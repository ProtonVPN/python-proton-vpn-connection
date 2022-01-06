from .abstract_vpnconnection import AbstractVPNConnection


class VPNConnection(AbstractVPNConnection):
    """Allows to instantiate a VPN connection.

    The VPNConnection constructor needs to be passed four different objects
    that provide different types of information.

    vpnserver:
        vpnserver should always provide a server_ip, domain, tcp_ports
        and udp_ports properties.
        Servername is optional is not entirely necessary to provide, unless
        you would like to have a custom name for the connection.

        Properties:
            server_ip -> str
            domain -> str
            servername -> str | None
            tcp_ports -> [int]
            udp_ports -> [int]

    vpncredentials:
        vpncredentials should provide a namedtuple with username and password
        as its properties.

        Methods:
            get_username_password() -> namedtuple(str)

    Usage:
    .. code-block::
        vpnconnection = VPNConnection(vpnserver, vpncredentials)
        vpnconnection.up()

        # to shutdown vpn connection
        vpnconnection.down()
    """
    def __init__(self, vpnserver: object, vpncredentials: object):
        pass

    def up(self):
        pass

    def down(self, device_name):
        # find connection with specific virtual device type
        # figure out which protocol is used
        # figure out which implementation is being used
        print("\nDisconnected from", device_name)
