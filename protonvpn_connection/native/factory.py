from ..vpnconnection.abstract_connection_factory import AbstractConnectionFactory
from ..vpnconnection.abstract_vpnconnection import AbstractVPNConnection, ProtocolEnum


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
