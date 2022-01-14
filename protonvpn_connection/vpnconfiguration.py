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

    @abstractmethod
    def __enter__(self):
        pass

    @abstractmethod
    def __exit__(self):
        pass

    @abstractmethod
    def generate(self):
        pass


class OVPNFileConfig(VPNConfiguration):
    _configfile = None
    _protocol = None

    def __enter__(self):
        # We create the configuration file when we enter,
        # and delete it when we exit.
        # This is a race free way of having temporary files.
        if self._configfile is None:
            self.__delete_existing_ovpn_configuration()
            self._configfile = tempfile.NamedTemporaryFile(
                dir=os.getcwd(), delete=False,
                prefix='ProtonVPN-', suffix="ovpn", mode='w'
            )
            self._configfile.write("test")
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

    def __delete_existing_ovpn_configuration(self):
        for file in os.getcwd():
            if file.endswith(".ovpn"):
                os.remove(
                    os.path.join(os.getcwd(), file)
                )

    def generate(self):
        """Method that generates a vpn certificate.

        Returns:
            string: configuration file
        """

        j2_values = {
            "openvpn_protocol": self._protocol,
            "serverlist": [self._physical_server.entry_ip],
            "openvpn_ports": self.ports,
        }

        j2 = Environment(loader=FileSystemLoader(TEMPLATE_FOLDER))

        template = j2.get_template("openvpn_v2_template.j2")

        try:
            return template.render(j2_values)
        except jinja2.exceptions.TemplateNotFound as e:
            raise jinja2.exceptions.TemplateNotFound(e)


class WireguardFileConfig(VPNConfiguration):
    _config_file = None

    def __enter__(self):
        pass

    def __exit__(self):
        pass
