from ..vpnconnection.abstract_connection_factory import AbstractConnectionFactory
from ..vpnconnection.abstract_vpnconnection import AbstractVPNConnection
from ..vpnconfig import AbstractVPNConfiguration


class NativeOpenVPNCertificateConnection(AbstractVPNConnection):

    def up(self, vpnconfig: AbstractVPNConfiguration):
        print("Connecting native openvpn {} with certificate to {}".format(vpnconfig.protocol, vpnconfig.servername))
        print("nConnected")

    def down(self):
        print("disconnecting")


class NativeOpenVPNUserPassConnection(AbstractVPNConnection):

    def up(self, vpnconfig: AbstractVPNConfiguration):
        print("Connecting native openvpn {} with user pass to {}".format(vpnconfig.protocol, vpnconfig.servername))
        print("\nConnected")

    def down(self):
        print("disconnecting")


class NativeWireguardConnection(AbstractVPNConnection):

    def up(self, vpnconfig: AbstractVPNConfiguration):
        print("Connecting native wireguard {} with cert to {}".format(vpnconfig.protocol, vpnconfig.servername))
        print("\n\nConnected")

    def down(self):
        print("disconnecting")


class NativeConnectionFactory(AbstractConnectionFactory):

    @classmethod
    def openvpn_certificate_based(self) -> NativeOpenVPNCertificateConnection:
        return NativeOpenVPNCertificateConnection()

    @classmethod
    def openvpn_user_pass_based(self) -> NativeOpenVPNUserPassConnection:
        return NativeOpenVPNUserPassConnection()

    @classmethod
    def wireguard_certificate_based(self) -> NativeWireguardConnection:
        return NativeWireguardConnection()
