from ..vpnconnection.abstract_connection_factory import AbstractConnectionFactory
from ..vpnconnection.abstract_vpnconnection import AbstractVPNConnection
from ..vpnconfig import AbstractVPNConfiguration


class NativeOpenVPNCertificate(AbstractVPNConnection):

    def up(self, vpnconfig: AbstractVPNConfiguration):
        print("Connecting")
        print("\n\nConnected")

    def down(self):
        print("disconnecting")


class NativeOpenVPNUserPass(AbstractVPNConnection):

    def up(self, vpnconfig: AbstractVPNConfiguration):
        print("Connecting")
        print("\n\nConnected")

    def down(self):
        print("disconnecting")


class NativeWireguard(AbstractVPNConnection):

    def up(self, vpnconfig: AbstractVPNConfiguration):
        print("Connecting")
        print("\n\nConnected")

    def down(self):
        print("disconnecting")


class NativeConnectionFactory(AbstractConnectionFactory):

    @classmethod
    def openvpn_certificate_based(self) -> NativeOpenVPNCertificate:
        return NativeOpenVPNCertificate

    @classmethod
    def openvpn_user_pass_based(self) -> NativeOpenVPNUserPass:
        return NativeOpenVPNUserPass

    @classmethod
    def wireguard_certificate_based(self) -> NativeWireguard:
        return NativeWireguard
