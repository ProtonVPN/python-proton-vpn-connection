"""
This module defines the classes holding the necessary configuration to establish
a VPN connection.
"""
import ipaddress
import tempfile
import os

from jinja2 import Environment, BaseLoader
from proton.utils.environment import ExecutionEnvironment

from proton.vpn.connection.constants import \
    CA_CERT, OPENVPN_V2_TEMPLATE, WIREGUARD_TEMPLATE
from proton.vpn.connection.interfaces import Settings


class DefaultSettings(Settings):
    """Default Proton VPN settings."""


class VPNConfiguration:
    """Base VPN configuration."""
    EXTENSION = None

    def __init__(self, vpnserver, vpncredentials, settings=None):
        self._configfile = None
        self._configfile_enter_level = None
        self._vpnserver = vpnserver
        self._vpncredentials = vpncredentials
        self.settings = settings or DefaultSettings()
        self.use_certificate = False
        if vpnserver is None or vpncredentials is None:
            raise TypeError("Unexpected type `None`")

    @classmethod
    def from_factory(cls, protocol):
        """Returns the configuration class based on the specified protocol."""
        protocols = {
            "openvpn_tcp": OpenVPNTCPConfig,
            "openvpn_udp": OpenVPNUDPConfig,
            "wireguard": WireguardConfig,
        }

        return protocols[protocol]

    def __enter__(self):
        # We create the configuration file when we enter,
        # and delete it when we exit.
        # This is a race free way of having temporary files.

        if self._configfile is None:
            self.__delete_existing_configuration()
            self._configfile = tempfile.NamedTemporaryFile(
                dir=self.__base_path, delete=False,
                prefix='ProtonVPN-', suffix=self.EXTENSION, mode='w'
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
            if file.endswith(f".{self.EXTENSION}"):
                os.remove(os.path.join(self.__base_path, file))

    def generate(self) -> str:
        """Generates the configuration file content."""
        raise NotImplementedError

    @property
    def __base_path(self):
        return ExecutionEnvironment().path_runtime

    @staticmethod
    def cidr_to_netmask(cidr) -> str:
        """Returns the subnet netmask from the CIDR."""
        subnet = ipaddress.IPv4Network(f"0.0.0.0/{cidr}")
        return str(subnet.netmask)

    @staticmethod
    def is_valid_ipv4(ip_address) -> bool:
        """Returns True if the specified ip address is a valid IPv4 address,
        and False otherwise."""
        try:
            ipaddress.ip_address(ip_address)
        except ValueError:
            return False

        return True


class OVPNConfig(VPNConfiguration):
    """OpenVPN-specific configuration."""
    _protocol = None
    EXTENSION = ".ovpn"

    def generate(self) -> str:
        """Method that generates a vpn config file.

        Returns:
            string: configuration file
        """
        ports = self._vpnserver.tcp_ports if "tcp" == self._protocol else self._vpnserver.udp_ports

        j2_values = {
            "openvpn_protocol": self._protocol,
            "serverlist": [self._vpnserver.server_ip],
            "openvpn_ports": ports,
            "ipv6_enabled": self.settings.ipv6,
            "ca_certificate": CA_CERT,
            "certificate_based": self.use_certificate,
            "custom_dns": len(self.settings.dns_custom_ips) > 0,
        }
        if self.use_certificate:

            j2_values["cert"] = self._vpncredentials.pubkey_credentials.certificate_pem
            j2_values["priv_key"] = self._vpncredentials.pubkey_credentials.openvpn_private_key

        if len(self.settings.dns_custom_ips) > 0:
            dns_ips = []
            for ip_address in self.settings.dns_custom_ips:

                # FIX-ME: Should custom DNS IPs be tested
                # if they are in a valid form ?
                #
                # if not VPNConfiguration.is_valid_ipv4(ip):
                #     continue
                dns_ips.append(ip_address)

            j2_values["dns_ips"] = dns_ips

        template = Environment(loader=BaseLoader).from_string(OPENVPN_V2_TEMPLATE)

        return template.render(j2_values)


class OpenVPNTCPConfig(OVPNConfig):
    """Configuration for OpenVPN using TCP."""
    _protocol = "tcp"


class OpenVPNUDPConfig(OVPNConfig):
    """Configuration for OpenVPN using UDP."""
    _protocol = "udp"


class WireguardConfig(VPNConfiguration):
    """Wireguard-specific configuration."""
    _protocol = "wireguard"
    EXTENSION = ".conf"

    def generate(self) -> str:
        """Method that generates a wireguard vpn configuration.
        """

        if not self.use_certificate:
            raise RuntimeError("Wireguards expects certificate configuration")

        j2_values = {
            "wg_client_secret_key": self._vpncredentials.pubkey_credentials.wg_private_key,
            "wg_ip": self._vpnserver.server_ip,
            "wg_port": self._vpnserver.udp_ports[0],
            "wg_server_pk": self._vpnserver.wg_public_key_x25519,
            "ipv6_enabled": self.settings.ipv6
        }

        template = Environment(loader=BaseLoader).from_string(WIREGUARD_TEMPLATE)
        return template.render(j2_values)
