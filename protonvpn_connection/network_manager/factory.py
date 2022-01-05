from ..vpnconnection.abstract_connection_factory import AbstractConnectionFactory
from ..vpnconnection.abstract_vpnconnection import AbstractVPNConnection
from ..vpnconfig import AbstractVPNConfiguration


class NMOpenVPNCertificateConnection(AbstractVPNConnection):

    def up(self, vpnconfig: AbstractVPNConfiguration):
        print("Connecting NM openvpn {} with certificate to {}".format(vpnconfig.protocol, vpnconfig.servername))
        print("\nConnected")

    def down(self):
        print("disconnecting")


class NMOpenVPNUserPassConnection(AbstractVPNConnection):

    def up(self, vpnconfig: AbstractVPNConfiguration):
        print("Connecting NM openvpn {} with user pass to {}".format(vpnconfig.protocol, vpnconfig.servername))
        print("\nConnected")

    def down(self):
        print("disconnecting")


class NMWireguardConnection(AbstractVPNConnection):

    def up(self, vpnconfig: AbstractVPNConfiguration):
        print("Connecting NM Wireguard {} with certificate to {}".format(vpnconfig.protocol, vpnconfig.servername))
        print("\nConnected")

    def down(self):
        print("disconnecting")


class NetworkManagerConnectionFactory(AbstractConnectionFactory):

    @classmethod
    def openvpn_certificate_based(self) -> NMOpenVPNCertificateConnection:
        return NMOpenVPNCertificateConnection()

    @classmethod
    def openvpn_user_pass_based(self) -> NMOpenVPNUserPassConnection:
        return NMOpenVPNUserPassConnection()

    @classmethod
    def wireguard_certificate_based(self) -> NMWireguardConnection:
        return NMWireguardConnection()
