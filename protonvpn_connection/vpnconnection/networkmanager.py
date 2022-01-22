import gi

from .vpnconnection import VPNConnection

gi.require_version("NM", "1.0")
import os

from gi.repository import NM

from ..utils import ExecutionEnvironment
from .nmclient import NMClient


class NMConnection(VPNConnection, NMClient):
    """Returns VPN connections based on Network Manager implementation.

    This is the default backend that will be returned. See docstring for
    VPNConnection.get_vpnconnection() for further explanation on how priorities work.

    A NMConnection can return a VPNConnection based on protocols such as OpenVPN, IKEv2 or Wireguard.
    """

    implementation = "networkmanager"

    @classmethod
    def factory(cls, protocol: str = None):
        """Get VPN connection.

        Returns vpn connection based on specified procotol from factory.
        """
        if "openvpn" in protocol.lower():
            return OpenVPN.get_by_protocol(protocol)
        elif "wireguard" in protocol.lower():
            return Wireguard
        elif "ikev2" in protocol.lower():
            return Strongswan

    def up(self):
        self._setup()
        self._persist_connection()
        self._start_connection_async(self._get_protonvpn_connection())

    def down(self):
        self._remove_connection_async(self._get_protonvpn_connection())
        self._remove_connection_persistence()

    @classmethod
    def _get_connection(cls):
        classes = [OpenVPNTCP, OpenVPNUDP, Wireguard, Strongswan]

        for _class in classes:
            vpnconnection = _class(None, None)
            if vpnconnection._get_protonvpn_connection():
                return vpnconnection

    def _get_servername(self) -> str:
        servername = "ProtonVPN Connection"
        try:
            servername = "ProtonVPN {}".format(
                self._vpnserver.servername
                if self._vpnserver.servername
                else "Connection"
            )
        except AttributeError:
            pass

        return servername

    def _setup(self):
        raise NotImplementedError

    @classmethod
    def _priority(cls):
        return 100

    def _import_vpn_config(self, vpnconfig):
        plugin_info = NM.VpnPluginInfo
        vpn_plugin_list = plugin_info.list_load()

        with vpnconfig as filename:
            for plugin in vpn_plugin_list:
                plugin_editor = plugin.load_editor_plugin()
                # return a NM.SimpleConnection (NM.Connection)
                # https://lazka.github.io/pgi-docs/NM-1.0/classes/SimpleConnection.html
                try:
                    connection = plugin_editor.import_(filename)
                    # plugin_name = plugin.props.name
                except gi.repository.GLib.Error:
                    pass

        if connection is None:
            raise NotImplementedError(
                "Support for given configuration is not implemented"
            )

        # https://lazka.github.io/pgi-docs/NM-1.0/classes/Connection.html#NM.Connection.normalize
        if connection.normalize():
            pass

        return connection

    def _get_protonvpn_connection(self):
        """Get ProtonVPN connection.

        Returns:
            if:
            - NetworkManagerConnectionTypeEnum.ALL: NM.RemoteConnection
            - NetworkManagerConnectionTypeEnum.ACTIVE: NM.ActiveConnection
        """

        active_conn_list = self.nm_client.get_active_connections()
        non_active_conn_list = self.nm_client.get_connections()

        all_conn_list = active_conn_list + non_active_conn_list

        self._ensure_unique_id_is_set()
        if not self._unique_id:
            return None

        for conn in all_conn_list:
            if conn.get_connection_type() != "vpn" and conn.get_connection_type() != "wireguard":
                continue

            try:
                conn = conn.get_connection()
            except AttributeError:
                pass

            if conn.get_uuid() == self._unique_id:
                return conn

        return None


class OpenVPN(NMConnection):
    virtual_device_name = "proton0"
    connection = None

    @staticmethod
    def get_by_protocol(protocol: str):
        """Get VPN connection based on protocol."""
        if "tcp" in protocol.lower():
            return OpenVPNTCP
        else:
            return OpenVPNUDP

    def _configure_connection(self, vpnconfig):
        """Configure imported vpn connection.

            :param vpnconfig: vpn configuration object.
            :type vpnconfig: VPNConfiguration

        It also uses vpnserver, vpncredentials and settings for the following reasons:
            - vpnserver is used to fetch domain, servername (optioanl)
            - vpncredentials is used to fetch username/password for non-certificate based connections
            - settings is used to fetch dns settings

        """
        self.connection = self._import_vpn_config(vpnconfig)

        self.__vpn_settings = self.connection.get_setting_vpn()
        self.__connection_settings = self.connection.get_setting_connection()

        self._unique_id = self.__connection_settings.get_uuid()

        self.__make_vpn_user_owned()
        self.__add_server_certificate_check()
        self.__configure_dns()
        self.__set_custom_connection_id()

        if not vpnconfig.use_certificate:
            self.__add_vpn_credentials()

    def __make_vpn_user_owned(self):
        # returns NM.SettingConnection
        # https://lazka.github.io/pgi-docs/NM-1.0/classes/SettingConnection.html#NM.SettingConnection
        from getpass import getuser

        self.__connection_settings.add_permission(
            "user",
            getuser(),
            None
        )

    def __add_server_certificate_check(self):
        appened_domain = "name:" + self._vpnserver.domain
        self.__vpn_settings.add_data_item(
            "verify-x509-name", appened_domain
        )

    def __configure_dns(self):
        """Apply dns configurations to ProtonVPN connection."""

        ipv4_config = self.connection.get_setting_ip4_config()
        ipv6_config = self.connection.get_setting_ip6_config()

        ipv4_config.props.dns_priority = -1500
        ipv6_config.props.dns_priority = -1500

        try:
            if len(self._settings.dns_custom_ips) == 0:
                return
        except AttributeError:
            return

        custom_dns = self.settings.dns_custom_ips
        ipv4_config.props.ignore_auto_dns = True
        ipv6_config.props.ignore_auto_dns = True

        ipv4_config.props.dns = custom_dns

    def __set_custom_connection_id(self):
        self.__connection_settings.props.id = self._get_servername()

    def __add_vpn_credentials(self):
        """Add OpenVPN credentials to ProtonVPN connection.

        Args:
            openvpn_username (string): openvpn/ikev2 username
            openvpn_password (string): openvpn/ikev2 password
        """
        # returns NM.SettingVpn if the connection contains one, otherwise None
        # https://lazka.github.io/pgi-docs/NM-1.0/classes/SettingVpn.html
        user_data = self._vpncredentials.vpn_get_username_and_password()

        self.__vpn_settings.add_data_item(
            "username", user_data.username
        )
        self.__vpn_settings.add_secret(
            "password", user_data.password
        )


class OpenVPNTCP(OpenVPN):
    """Creates a OpenVPNTCP connection."""
    protocol = "openvpn_tcp"
    _persistence_prefix = "nm_{}_".format(protocol)

    def _setup(self):
        from ..vpnconfiguration import VPNConfiguration
        vpnconfig = VPNConfiguration.from_factory(self.protocol)
        vpnconfig = vpnconfig(self._vpnserver, self._vpncredentials, self._settings)
        vpnconfig.use_certificate = self._use_certificate

        self._configure_connection(vpnconfig)
        self._add_connection_async(self.connection)


class OpenVPNUDP(OpenVPN):
    """Creates a OpenVPNUDP connection."""
    protocol = "openvpn_udp"
    _persistence_prefix = "nm_{}_".format(protocol)

    def _setup(self):
        from ..vpnconfiguration import VPNConfiguration
        vpnconfig = VPNConfiguration.from_factory(self.protocol)
        vpnconfig = vpnconfig(self._vpnserver, self._vpncredentials, self._settings)
        vpnconfig.use_certificate = self._use_certificate

        self._configure_connection(vpnconfig)
        self._add_connection_async(self.connection)


class Wireguard(NMConnection):
    """Creates a Wireguard connection."""
    protocol = "wireguard"
    _persistence_prefix = "nm_{}_".format(protocol)
    virtual_device_name = "proton0"

    def __generate_unique_id(self):
        import uuid
        self._unique_id = str(uuid.uuid4())

    def __add_connection_to_nm(self):
        import dbus

        s_con = dbus.Dictionary({
            "type": "wireguard",
            "uuid": self._unique_id,
            "id": self._get_servername(),
            "interface-name": Wireguard.virtual_device_name
        })
        con = dbus.Dictionary({"connection": s_con})
        bus = dbus.SystemBus()
        proxy = bus.get_object(
            "org.freedesktop.NetworkManager",
            "/org/freedesktop/NetworkManager/Settings"
        )
        settings = dbus.Interface(
            proxy,
            "org.freedesktop.NetworkManager.Settings"
        )
        settings.AddConnection(con)

    def __configure_connection(self):
        import socket

        # FIXME : Update connections cache, NMclient is a mess
        nm_client = NM.Client.new(None)
        connection = nm_client.get_connection_by_uuid(self._unique_id)
        s_wg = connection.get_setting(NM.SettingWireGuard)

        # https://lazka.github.io/pgi-docs/NM-1.0/classes/Connection.html#NM.Connection.get_setting
        ip4 = connection.get_setting_ip4_config()
        ip4.set_property('method', 'manual')
        s_wg.set_property(
            NM.SETTING_WIREGUARD_PRIVATE_KEY,
            self._vpncredentials.vpn_get_certificate_holder().vpn_client_private_wg_key
        )
        ip4.add_address(NM.IPAddress(socket.AF_INET, '10.2.0.2', 32))
        ip4.add_dns('10.2.0.1')
        ip4.add_dns_search('~')
        ipv6_config = connection.get_setting_ip6_config()
        ipv6_config.props.dns_priority = -1500
        ip4.props.dns_priority = -1500
        peer = NM.WireGuardPeer()
        peer.set_public_key(self._vpnserver.x25519pk, True)
        peer.set_endpoint(f'{self._vpnserver.server_ip}:{self._vpnserver.udp_ports[0]}', True)
        peer.append_allowed_ip('0.0.0.0/0', False)
        s_wg.append_peer(peer)
        print(connection)
        connection.commit_changes(True, None)

    def __setup_wg_connection(self):
        self.__generate_unique_id()
        self.__add_connection_to_nm()
        self.__configure_connection()
        # FIXME : Update connections cache, NMclient is a mess
        nm_client = NM.Client.new(None)
        print(self._unique_id)
        self.connection = nm_client.get_connection_by_uuid(self._unique_id)

        self.connection.commit_changes(True, None)
        self._commit_changes_async(self.connection)

    def _setup(self):
        self.__setup_wg_connection()


class StrongswanProperties:
    # FIXME : Plugin seems to handle private key from a file, not really safe ?
    # FIXME : see if the plugin can accept anything else than files.
    CA_FILENAME = "protonvpnca.pem"
    PRIVATE_KEY_FILENAME = "key.pem"
    CERT_FILENAME = "cert.pem"


class Strongswan(NMConnection):
    """Creates a Strongswan/IKEv2 connection."""
    protocol = "ikev2"
    _persistence_prefix = "nm_{}_".format(protocol)
    virtual_device_name = "proton0"

    PEM_CA_FILEPATH = os.path.join(ExecutionEnvironment().path_runtime,StrongswanProperties.CA_FILENAME)
    PRIVKEY_FILEPATH = os.path.join(ExecutionEnvironment().path_runtime,StrongswanProperties.PRIVATE_KEY_FILENAME)
    CERT_FILEPATH = os.path.join(ExecutionEnvironment().path_runtime,StrongswanProperties.CERT_FILENAME)

    def __generate_unique_id(self):
        import uuid
        self._unique_id = str(uuid.uuid4())

    def __configure_connection(self):
        from ..constants import ca_cert
        new_connection = NM.SimpleConnection.new()

        s_con = NM.SettingConnection.new()
        s_con.set_property(NM.SETTING_CONNECTION_ID, self._get_servername())
        s_con.set_property(NM.SETTING_CONNECTION_UUID, self._unique_id)
        s_con.set_property(NM.SETTING_CONNECTION_TYPE, "vpn")

        s_vpn = NM.SettingVpn.new()
        s_vpn.set_property(NM.SETTING_VPN_SERVICE_TYPE, "org.freedesktop.NetworkManager.strongswan")
        s_vpn.add_data_item("address", self._vpnserver.domain)
        s_vpn.add_data_item("encap", "no")
        s_vpn.add_data_item("ike", "aes256gcm16-ecp384")
        s_vpn.add_data_item("ipcomp", "no")
        s_vpn.add_data_item("password-flags", "1")
        s_vpn.add_data_item("proposal", "no")
        s_vpn.add_data_item("virtual", "yes")

        with open(Strongswan.PEM_CA_FILEPATH, "w") as f:
            f.write(ca_cert)
        s_vpn.add_data_item("certificate", Strongswan.PEM_CA_FILEPATH)

        if self._use_certificate:
            s_vpn.add_data_item("method", "key")
            api_cert = self._vpncredentials.vpn_get_certificate_holder().vpn_client_api_pem_certificate
            with open(Strongswan.CERT_FILEPATH, "w") as f:
                f.write(api_cert)
            # openvpn key should work.
            priv_key = self._vpncredentials.vpn_get_certificate_holder().vpn_client_private_openvpn_key
            with open(Strongswan.PRIVKEY_FILEPATH, "w") as f:
                f.write(priv_key)
            s_vpn.add_data_item("usercert", Strongswan.CERT_FILEPATH)
            s_vpn.add_data_item("userkey", Strongswan.PRIVKEY_FILEPATH)
        else:
            pass_creds = self._vpncredentials.vpn_get_username_and_password()
            s_vpn.add_data_item("method", "eap")
            s_vpn.add_data_item("user", pass_creds.username)
            s_vpn.add_secret("password", pass_creds.password)

        new_connection.add_setting(s_con)
        new_connection.add_setting(s_vpn)

        self.connection = new_connection

    def __add_dns(self):
        # FIXME : Update connections cache, NMclient is a mess
        nm_client = NM.Client.new(None)
        connection = nm_client.get_connection_by_uuid(self._unique_id)
        ip4_s = connection.get_setting_ip4_config()
        ip4_s.add_dns('10.2.0.1')
        ip4_s.add_dns_search('~.')
        ip4_s.props.dns_priority = -1500
        ipv6_config = connection.get_setting_ip6_config()
        ipv6_config.add_dns_search('~.')
        ipv6_config.props.dns_priority = -1500
        connection.commit_changes(True, None)

    def _setup(self):
        self.__generate_unique_id()
        self.__configure_connection()
        self._add_connection_async(self.connection)
        self.__add_dns()
