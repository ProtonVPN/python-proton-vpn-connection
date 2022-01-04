from ..vpnconnection.abstract_connection_factory import AbstractConnectionFactory
from ..vpnconnection.abstract_vpnconnection import AbstractVPNConnection, ProtocolEnum


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
