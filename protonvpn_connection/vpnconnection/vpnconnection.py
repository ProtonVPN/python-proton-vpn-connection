from .abstract_vpnconnection import AbstractVPNConnection


class VPNConnection(AbstractVPNConnection):
    """Allows to instantiate a VPN connection.

    The VPNConnection constructor needs to be passed four different objects
    that provide different types of information.

    vpnserver:
        vpnserver at the least provide a server_ip and domain properties.
        Servername is optional is not entirely necessary to provide, unless
        you would like to have a custom name for the connection.

        Properties:
            server_ip -> str
            domain -> str
            servername -> str | None [Optional]

    ports:
        ports should always provide two properties, tcp and udp. Both of
        these properties should return a list of strings, or empty if there are no
        ports.

        Properties:
            tcp -> [int]
            udp -> [int]

    vpncredentials:
        vpncredentials should provide a namedtuple with username and password
        as its properties.

        Properties:
            get_username_password() -> namedtuple(str)

    usersettings:

        usersettings should provide two different properties, one to get protocol and another one to get
        a list of custom DNS IPs. For protocol only the following values are accepted: [udp | tcp]

        Properties:
            protocol -> str
            custom_dns_list -> [str]

    """
    def __init__(self, vpnserver: object, ports: object, vpncredentials: object, usersettings: object):
        pass

    def up(self):
        pass

    def down(self, device_name):
        # find connection with specific virtual device type
        # figure out which protocol is used
        # figure out which implementation is being used
        print("\nDisconnected from", device_name)
