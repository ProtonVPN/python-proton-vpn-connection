from .vpnconnection import VPNConnection

import gi
gi.require_version("NM", "1.0")
from gi.repository import NM
from .nmclient import NMClientMixin


class NMConnection(VPNConnection, NMClientMixin):
    """Returns VPN connections based on Network Manager implementation.

    This is the default backend that will be returned. See docstring for
    VPNConnection.get_vpnconnection() for further explanation on how priorities work.

    A NMConnection can return a VPNConnection based on protocols such as OpenVPN, IKEv2 or Wireguard.
    """
    implementation = "networkmanager"

    @classmethod
    def factory(cls, protocol: str = None):
        """Get VPN connection.

        The type of procotol returned.
        """
        if "openvpn" in protocol:
            return OpenVPN.get_by_protocol(protocol)
        elif "wireguard" in protocol:
            return Wireguard

    @staticmethod
    def _priority():
        return 100

    def _setup(self):
        raise NotImplementedError

    def up(self):
        raise NotImplementedError

    def down(self):
        raise NotImplementedError

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
            print("Connection normalized")

        return connection

    def _get_protonvpn_connection(self, from_active=False):
        """Get ProtonVPN connection.

        Returns:
            if:
            - NetworkManagerConnectionTypeEnum.ALL: NM.RemoteConnection
            - NetworkManagerConnectionTypeEnum.ACTIVE: NM.ActiveConnection
        """
        protonvpn_connection = False
        if from_active:
            conn_list = self.nm_client.get_active_connections()
        else:
            conn_list = self.nm_client.get_connections()

        for conn in conn_list:
            if conn.get_connection_type() == "vpn":
                conn_for_vpn = conn

                try:
                    vpn_settings = conn_for_vpn.get_setting_vpn()
                except AttributeError:
                    continue

                if (
                    vpn_settings.get_data_item("dev")
                    == self.virtual_device_name
                ):
                    protonvpn_connection = conn
                    break

        return protonvpn_connection


class OpenVPN(NMConnection):
    virtual_device_name = "proton0"
    connection = None

    @staticmethod
    def get_by_protocol(protocol: str):
        """Get VPN connection based on protocol."""
        if "tcp" in protocol:
            return OpenVPNTCP
        else:
            return OpenVPNUDP

    def _configure_connection(self, vpnconfig, cert_based=False):
        self.connection = self._import_vpn_config(vpnconfig)

        self.vpn_settings = self.connection.get_setting_vpn()
        self.connection_settings = self.connection.get_setting_connection()

        self.make_vpn_user_owned()
        self.add_server_certificate_check()
        self.dns_configurator()
        self.set_custom_connection_id()
        self.apply_virtual_device_type()

        if not cert_based:
            self.add_vpn_credentials()

    def make_vpn_user_owned(self):
        # returns NM.SettingConnection
        # https://lazka.github.io/pgi-docs/NM-1.0/classes/SettingConnection.html#NM.SettingConnection
        from getpass import getuser

        self.connection_settings.add_permission(
            "user",
            getuser(),
            None
        )

    def add_server_certificate_check(self):
        appened_domain = "name:" + self._vpnserver.domain
        self.vpn_settings.add_data_item(
            "verify-x509-name", appened_domain
        )

    def dns_configurator(self):
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

    def set_custom_connection_id(self):
        try:
            self.connection_settings.props.id = "ProtonVPN {}".foramt(
                self._vpnserver.servername if self._vpnserver.servername else "Connection")
        except AttributeError:
            self.connection_settings.props.id = "ProtonVPN Connection"

    def apply_virtual_device_type(self):
        """Apply virtual device type and name."""
        # Changes virtual tunnel name
        self.vpn_settings.add_data_item("dev", self.virtual_device_name)
        self.vpn_settings.add_data_item("dev-type", "tun")

    def add_vpn_credentials(self):
        """Add OpenVPN credentials to ProtonVPN connection.

        Args:
            openvpn_username (string): openvpn/ikev2 username
            openvpn_password (string): openvpn/ikev2 password
        """
        # returns NM.SettingVpn if the connection contains one, otherwise None
        # https://lazka.github.io/pgi-docs/NM-1.0/classes/SettingVpn.html
        user_data = self._vpnaccount.get_username_and_password()

        self.vpn_settings.add_data_item(
            "username", user_data.username
        )
        self.vpn_settings.add_secret(
            "password", user_data.password
        )

    def down(self):
        self._remove_connection_async(self._get_protonvpn_connection(True))


class OpenVPNTCP(OpenVPN):
    """Creates a OpenVPNTCP connection."""
    protocol = "tcp"

    def _setup(self):
        from ..vpnconfiguration import OVPNFileConfig
        vpnconfig = OVPNFileConfig(self._vpnserver, self._vpnaccount, self._settings)
        vpnconfig.protocol = self.protocol
        self._configure_connection(vpnconfig)
        self._add_connection_async(self.connection)

    def up(self):
        self._setup()
        self._start_connection_async(self._get_protonvpn_connection())


class OpenVPNUDP(OpenVPN):
    """Creates a OpenVPNUDP connection."""
    protocol = "udp"

    def _setup(self):
        from ..vpnconfiguration import OVPNFileConfig
        vpnconfig = OVPNFileConfig(self._vpnserver, self._vpnaccount, self._settings)
        vpnconfig.protocol = self.protocol
        self._configure_connection(vpnconfig)
        self._add_connection_async(self.connection)

    def up(self):
        self._setup()
        self._start_connection_async(self._get_protonvpn_connection())


class Wireguard(NMConnection):
    """Creates a Wireguard connection."""
    protocol = "wg"

    def _setup(self):
        pass

    def up(self):
        pass

    def down(self):
        pass
