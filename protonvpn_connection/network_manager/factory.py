from ..vpnconnection.abstract_connection_factory import AbstractConnectionFactory
from ..vpnconnection.abstract_vpnconnection import AbstractVPNConnection
from ..vpnconfig import AbstractVPNConfiguration


class NetworkMangerOpenVPNCertificate(AbstractVPNConnection):

    def up(self, vpnconfig: AbstractVPNConfiguration):
        print("Connecting")
        print("\n\nConnected")

    def down(self):
        print("disconnecting")


class NetworkMangerOpenVPNUserPass(AbstractVPNConnection):

    def up(self, vpnconfig: AbstractVPNConfiguration):
        print("Connecting")
        print("\n\nConnected")

    def down(self):
        print("disconnecting")


class NetworkManagerWireguard(AbstractVPNConnection):

    def up(self, vpnconfig: AbstractVPNConfiguration):
        print("Connecting")
        print("\n\nConnected")

    def down(self):
        print("disconnecting")


class NetworkManagerConnectionFactory(AbstractConnectionFactory):

    @classmethod
    def openvpn_certificate_based(self) -> NetworkMangerOpenVPNCertificate:
        return NetworkMangerOpenVPNCertificate

    @classmethod
    def openvpn_user_pass_based(self) -> NetworkMangerOpenVPNUserPass:
        return NetworkMangerOpenVPNUserPass

    @classmethod
    def wireguard_certificate_based(self) -> NetworkManagerWireguard:
        return NetworkManagerWireguard
