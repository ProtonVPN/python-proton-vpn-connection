from abc import abstractmethod
import tempfile
import os
from .abstract_interfaces import AbstractSettings
import jinja2
from jinja2 import Environment, FileSystemLoader


TEMPLATE_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "template")


class DummySettings(AbstractSettings):
    pass


class VPNConfiguration:
    def __init__(self, vpnserver, vpnaccount, settings=None):
        self._configfile = None
        self._vpnserver = vpnserver
        self._vpnaccount = vpnaccount
        self.settings = settings

    @property
    def protocol(self):
        return self._protocol

    @protocol.setter
    def protocol(self, new_value):
        self._protocol = new_value

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
                dir=ExecutionEnvironment.path_runtime, delete=False,
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
        for file in os.getcwd():
            if file.endswith(".{}".format(self.extension)):
                os.remove(
                    os.path.join(os.getcwd(), file)
                )

    @abstractmethod
    def generate(self):
        pass


class OVPNFileConfig(VPNConfiguration):
    extension = ".ovpn"
    _protocol = None
    _is_certificate = False

    @property
    def is_certificate(self):
        return self._is_certificate

    @is_certificate.setter
    def is_certificate(self, new_value):
        self._is_certificate = new_value

    def generate(self):
        """Method that generates a vpn config file.

        Returns:
            string: configuration file
        """

        ports = self._vpnserver.tcp_ports if "tcp" == self.protocol else self._vpnserver.udp_ports

        j2_values = {
            "openvpn_protocol": self._protocol,
            "serverlist": [self._vpnserver.server_ip],
            "openvpn_ports": ports,
            "ipv6_disabled": self._settings.disable_ipv6,
            "certificate_based": self._is_certificate,
            "split": True if len(self._settings.split_tunneling_ips) > 0 else False,
        }
        if self._is_certificate:
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

        j2 = Environment(loader=FileSystemLoader(TEMPLATE_FOLDER))

        template = j2.get_template("openvpn_v2_template.j2")

        try:
            return template.render(j2_values)
        except jinja2.exceptions.TemplateNotFound as e:
            raise jinja2.exceptions.TemplateNotFound(e)

    def _cidr_to_netmask(self, cidr):
        import ipaddress
        subnet = ipaddress.IPv4Network("0.0.0.0/{0}".format(cidr))
        return str(subnet.netmask)


class WireguardFileConfig(VPNConfiguration):
    _config_file = None

    def __enter__(self):
        pass

    def __exit__(self):
        pass
