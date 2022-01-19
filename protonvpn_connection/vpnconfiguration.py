from abc import abstractmethod
import tempfile
import os
from .abstract_interfaces import AbstractSettings
import jinja2
from jinja2 import Environment, BaseLoader


TEMPLATE_FOLDER = '/tmp'
#os.path.join(os.path.dirname(os.path.abspath(__file__)), "template")


class DummySettings(AbstractSettings):
    pass


class VPNConfiguration:
    def __init__(self, vpnserver, vpnaccount, settings=None):
        self._configfile = None
        self._vpnserver = vpnserver
        self._vpnaccount = vpnaccount
        self.settings = settings
        self._use_certificate = False

    @property
    def use_certificate(self):
        return self._use_certificate

    @use_certificate.setter
    def use_certificate(self, new_value):
        self._use_certificate = new_value

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
        return self._settings

    @settings.setter
    def settings(self, new_value):
        if not new_value:
            self._settings = DummySettings()
        else:
            self._settings = new_value

    def __enter__(self):
        # We create the configuration file when we enter,
        # and delete it when we exit.
        # This is a race free way of having temporary files.
        from .utils import ExecutionEnvironment
        if self._configfile is None:
            self.__delete_existing_configuration()
            self._configfile = tempfile.NamedTemporaryFile(
                dir=ExecutionEnvironment().path_runtime, delete=False,
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
        from .utils import ExecutionEnvironment
        for file in ExecutionEnvironment().path_runtime:
            if file.endswith(".{}".format(self.extension)):
                os.remove(
                    os.path.join(ExecutionEnvironment().path_runtime, file)
                )

    @abstractmethod
    def generate(self):
        pass


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

        j2_values = {
            "openvpn_protocol": self._protocol,
            "serverlist": [self._vpnserver.server_ip],
            "openvpn_ports": ports,
            "ipv6_disabled": self._settings.disable_ipv6,
            "ca_certificate": ca_cert,
            "certificate_based": self._use_certificate,
            "split": True if len(self._settings.split_tunneling_ips) > 0 else False,
        }
        if self._use_certificate:
            j2_values["cert"] = self._vpnaccount.get_client_api_pem_certificate()
            j2_values["priv_key"] = self._vpnaccount.get_client_private_openvpn_key()

        if len(self._settings.split_tunneling_ips) > 0:
            ip_nm_pairs = []
            for ip in self._settings.split_tunneling_ips:
                if "/" in ip:
                    ip, cidr = ip.split("/")
                    netmask = self._cidr_to_netmask(int(cidr))
                else:
                    ip = ip

                ip_nm_pairs.append({"ip": ip, "nm": netmask})

            j2_values["ip_nm_pair"] = ip_nm_pairs

        template = Environment(loader=BaseLoader).from_string(openvpn_v2_template)

        try:
            return template.render(j2_values)
        except jinja2.exceptions.TemplateNotFound as e:
            raise jinja2.exceptions.TemplateNotFound(e)

    def _cidr_to_netmask(self, cidr):
        import ipaddress
        subnet = ipaddress.IPv4Network("0.0.0.0/{0}".format(cidr))
        return str(subnet.netmask)


class OpenVPNTCPConfig(OVPNConfig):
    _protocol = "tcp"


class OpenVPNUDPConfig(OVPNConfig):
    _protocol = "udp"


class WireguardConfig(VPNConfiguration):
    _config_file = None

    def __enter__(self):
        pass

    def __exit__(self):
        pass
