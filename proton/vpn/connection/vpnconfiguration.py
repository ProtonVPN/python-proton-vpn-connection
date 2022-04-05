import tempfile
import os
from .interfaces import Settings
import jinja2
from jinja2 import Environment, BaseLoader
import re


class DummySettings(Settings):
    pass


class VPNConfiguration:
    def __init__(self, vpnserver, vpncredentials, settings=None):
        self._configfile = None
        self.__use_certificate = False
        if vpnserver is None or vpncredentials is None:
            raise TypeError("Unexpected type `None`")

        self._vpnserver = vpnserver
        self._vpncredentials = vpncredentials
        self._settings = settings

    @property
    def use_certificate(self):
        return self.__use_certificate

    @use_certificate.setter
    def use_certificate(self, new_value):
        self.__use_certificate = new_value

    @classmethod
    def from_factory(cls, protocol):
        protocols = {
            "openvpn_tcp": OpenVPNTCPConfig,
            "openvpn_udp": OpenVPNUDPConfig,
            "wireguard": WireguardConfig,
        }

        return protocols[protocol]

    @property
    def settings(self):
        if self._settings is None:
            self._settings = DummySettings()

        return self._settings

    @settings.setter
    def settings(self, new_value):
        if new_value is None:
            self._settings = DummySettings()
        else:
            self._settings = new_value

    def __enter__(self):
        # We create the configuration file when we enter,
        # and delete it when we exit.
        # This is a race free way of having temporary files.

        if self._configfile is None:
            self.__delete_existing_configuration()
            self._configfile = tempfile.NamedTemporaryFile(
                dir=self.__base_path, delete=False,
                prefix='ProtonVPN-', suffix=self.extension, mode='w'
            )
            self._configfile.write(self.generate())
            self._configfile.close()
            self._configfile_enter_level = 0

        self._configfile_enter_level += 1

        return self._configfile.name

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._configfile is None:
            return

        self._configfile_enter_level -= 1
        if self._configfile_enter_level == 0:
            os.unlink(self._configfile.name)
            self._configfile = None

    def __delete_existing_configuration(self):
        for file in self.__base_path:
            if file.endswith(".{}".format(self.extension)):
                os.remove(
                    os.path.join(self.__base_path, file)
                )

    def generate(self):
        raise NotImplementedError

    @property
    def __base_path(self):
        from .utils import ExecutionEnvironment
        return ExecutionEnvironment().path_runtime

    def cidr_to_netmask(self, cidr):
        import ipaddress
        subnet = ipaddress.IPv4Network("0.0.0.0/{0}".format(cidr))
        return str(subnet.netmask)

    def is_valid_ipv4(self, ip):
        valid_ip_re = re.compile(
            r'^(25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.'
            r'(25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.'
            r'(25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.'
            r'(25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)'
            r'(/(3[0-2]|[12][0-9]|[1-9]))?$'  # Matches CIDR
        )

        return True if valid_ip_re.match(ip) else False


class OVPNConfig(VPNConfiguration):
    extension = ".ovpn"

    def generate(self):
        """Method that generates a vpn config file.

        Returns:
            string: configuration file
        """
        from .constants import openvpn_v2_template
        from .constants import ca_cert

        ports = self._vpnserver.tcp_ports if "tcp" == self._protocol else self._vpnserver.udp_ports

        if not isinstance(self._settings, Settings):
            self._settings = DummySettings()

        j2_values = {
            "openvpn_protocol": self._protocol,
            "serverlist": [self._vpnserver.server_ip],
            "openvpn_ports": ports,
            "ipv6_disabled": self._settings.ipv6,
            "ca_certificate": ca_cert,
            "certificate_based": self.use_certificate,
            "split_tunneling": True if len(self._settings.split_tunneling_ips) > 0 else False,
            "custom_dns": True if len(self._settings.dns_custom_ips) > 0 else False,
        }
        if self.use_certificate:

            j2_values["cert"] = self._vpncredentials.pubkey_credentials.certificate_pem
            j2_values["priv_key"] = self._vpncredentials.pubkey_credentials.openvpn_private_key

        if len(self._settings.split_tunneling_ips) > 0:
            ip_nm_pairs = []
            for ip in self._settings.split_tunneling_ips:
                netmask = "255.255.255.255"

                if not self.is_valid_ipv4(ip):
                    continue

                if "/" in ip:
                    ip, cidr = ip.split("/")
                    netmask = self.cidr_to_netmask(int(cidr))
                else:
                    ip = ip

                ip_nm_pairs.append({"ip": ip, "nm": netmask})

            j2_values["ip_nm_pairs"] = ip_nm_pairs

        if len(self._settings.dns_custom_ips) > 0:
            dns_ips = []
            for ip in self._settings.dns_custom_ips:

                # FIX-ME: Should custom DNS IPs be tested
                # if they are in a valid form ?
                #
                # if not self.is_valid_ipv4(ip):
                #     continue
                dns_ips.append(ip)

            j2_values["dns_ips"] = dns_ips

        template = Environment(loader=BaseLoader).from_string(openvpn_v2_template)

        try:
            return template.render(j2_values)
        except jinja2.exceptions.TemplateNotFound:
            raise


class OpenVPNTCPConfig(OVPNConfig):
    _protocol = "tcp"


class OpenVPNUDPConfig(OVPNConfig):
    _protocol = "udp"


class WireguardConfig(VPNConfiguration):
    _protocol = "wireguard"
    extension = ".conf"

    def generate(self) -> str:
        """Method that generates a wireguard vpn configuration.
        """

        if not self.use_certificate:
            raise RuntimeError("Wireguards expects certificate configuration")

        from .constants import wireguard_template

        j2_values = {
            "wg_client_secret_key": self._vpncredentials.pubkey_credentials.wg_private_key,
            "wg_ip": self._vpnserver.server_ip,
            "wg_port": self._vpnserver.udp_ports[0],
            "wg_server_pk": self._vpnserver.wg_public_key_x25519
        }

        template = Environment(loader=BaseLoader).from_string(wireguard_template)

        try:
            return template.render(j2_values)
        except jinja2.exceptions.TemplateNotFound:
            raise
        except Exception:
            pass
