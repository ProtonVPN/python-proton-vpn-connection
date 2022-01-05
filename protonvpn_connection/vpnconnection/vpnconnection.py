from .abstract_vpnconnection import AbstractVPNConnection
from ..vpnconfig.abstract_vpnconfig import AbstractVPNConfiguration


class VPNConnection(AbstractVPNConnection):

    def up(self, vpnconfig: AbstractVPNConfiguration):
        if "prefferd_method_set_in_variable_set_to_native":
            from ..native import NativeConnectionFactory
            preffered_backend = NativeConnectionFactory
        else:
            from ..network_manager import NetworkManagerConnectionFactory
            preffered_backend = NetworkManagerConnectionFactory

        if vpnconfig.protocol.lower() in ["udp", "tcp"]:
            connection = preffered_backend.openvpn_user_pass_based()
        elif vpnconfig.protocol.lower() in ["wireguard", "wg"]:
            connection = preffered_backend.wireguard_certificate_based()

        connection.up(vpnconfig)

    def down(self, device_name):
        # find connection with specific virtual device type
        # figure out which protocol is used
        # figure out which implementation is being used
        print("\nDisconnected from", device_name)
