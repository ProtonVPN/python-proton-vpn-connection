from abc import ABC, abstractmethod
from ..vpnconfig.abstract_vpnconfig import AbstractVPNConfiguration


class AbstractVPNConnection(ABC):

    @abstractmethod
    def up(self, vpnconfig: AbstractVPNConfiguration):
        pass

    @abstractmethod
    def down(self):
        pass


class NetworkMangerOpenVPNCertificate(AbstractVPNConnection):

    def up(self, vpnconfig: AbstractVPNConfiguration):
        filepath = vpnconfig.get_vpn_config_filepath()
        cert = vpnconfig.get_certificate()
        # attempt to connect

    def down(self):
        pass


class NetworkMangerOpenVPNUserPass(AbstractVPNConnection):

    def up(self, vpnconfig: AbstractVPNConfiguration):
        filepath = vpnconfig.get_vpn_config_filepath()
        cert = vpnconfig.get_user_pass()
        # attempt to connect

    def down(self):
        pass


class OpenVPNCertificate(AbstractVPNConnection):

    def up(self, vpnconfig: AbstractVPNConfiguration):
        filepath = vpnconfig.get_vpn_config_filepath()
        cert = vpnconfig.get_certificate()
        # attempt to connect

    def down(self):
        pass


class OpenVPNUserPass(AbstractVPNConnection):

    def up(self, vpnconfig: AbstractVPNConfiguration):
        filepath = vpnconfig.get_vpn_config_filepath()
        cert = vpnconfig.get_user_pass()
        # attempt to connect

    def down(self):
        pass


class Wireguard(AbstractVPNConnection):

    def up(self, vpnconfig: AbstractVPNConfiguration):
        filepath = vpnconfig.get_vpn_config_filepath()
        cert = vpnconfig.get_certificate()
        # attempt to connect

    def down(self):
        pass