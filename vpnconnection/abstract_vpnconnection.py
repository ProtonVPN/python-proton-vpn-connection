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
        print("Connecting")
        print("\n\nConnected")

    def down(self):
        print("disconnecting")


class NetworkMangerOpenVPNUserPass(AbstractVPNConnection):

    def up(self, vpnconfig: AbstractVPNConfiguration):
        filepath = vpnconfig.get_vpn_config_filepath()
        cert = vpnconfig.get_user_pass()
        # attempt to connect
        print("Connecting")
        print("\n\nConnected")

    def down(self):
        print("disconnecting")


class NetworkManagerWireguard(AbstractVPNConnection):

    def up(self, vpnconfig: AbstractVPNConfiguration):
        filepath = vpnconfig.get_vpn_config_filepath()
        cert = vpnconfig.get_certificate()
        # attempt to connect
        print("Connecting")
        print("\n\nConnected")

    def down(self):
        print("disconnecting")


class NativeOpenVPNCertificate(AbstractVPNConnection):

    def up(self, vpnconfig: AbstractVPNConfiguration):
        filepath = vpnconfig.get_vpn_config_filepath()
        cert = vpnconfig.get_certificate()
        # attempt to connect
        print("Connecting")
        print("\n\nConnected")

    def down(self):
        print("disconnecting")


class NativeOpenVPNUserPass(AbstractVPNConnection):

    def up(self, vpnconfig: AbstractVPNConfiguration):
        filepath = vpnconfig.get_vpn_config_filepath()
        cert = vpnconfig.get_user_pass()
        # attempt to connect
        print("Connecting")
        print("\n\nConnected")

    def down(self):
        print("disconnecting")


class NativeWireguard(AbstractVPNConnection):

    def up(self, vpnconfig: AbstractVPNConfiguration):
        filepath = vpnconfig.get_vpn_config_filepath()
        cert = vpnconfig.get_certificate()
        # attempt to connect
        print("Connecting")
        print("\n\nConnected")

    def down(self):
        print("disconnecting")
