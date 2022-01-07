from abc import abstractmethod


class classproperty(property):
    def __get__(self, cls, owner):
        return classmethod(self.fget).__get__(None, owner)()


class VPNConnectionFactory:
    """VPN connection factory.

    Allows to instantiate a VPN connection.
    The VPNConnection constructor needs to be passed four different objects
    that provide different types of information.

    vpnserver:
        - vpnserver should always provide a server_ip, domain, tcp_ports
          and udp_ports properties.
          Servername is optional is not entirely necessary to provide, unless
          you would like to have a custom name for the connection.

        - Properties:
            - server_ip -> str
            - domain -> str
            - servername -> str | None
            - tcp_ports -> [int]
            - udp_ports -> [int]

    vpnaccount:
        - vpnaccount should provide the following properties:
        - Methods:
            - vpn_username -> str
            - vpn_password -> str

    Basic Usage:
    ::
    vpnconnection = VPNConnectionFactory(vpnserver, vpnaccount)
    vpnconnection.up()

    # to shutdown vpn connection
    vpnconnection.down()

    """
    def __init__(self, vpnserver: object, vpnaccount: object):
        self.vpnserver = vpnserver
        self.vpnaccount = vpnaccount

    @classmethod
    def get_vpnconnection(
        cls,
        protocol: str = None,
        usersettings: object = None,
        connection_implementation: str = None,
    ):
        """Get a vpn connection from factory.

            :param protocol: Optional.
                protocol to connect with, all in smallcaps
            :type protocol: str
            :param usersettings: Optional.
                If it's passed then it should provide the following properties:
                - custom_dns_list -> [str] - A list of custom IPs to use for DNS
                - split_tunnleing -> [str] - A list of IPs to exclude from VPN
                - smart_routing -> bool - If smart routing is to be used or not
            :type usersettings: object
            :param connection_implementation: Optional.
                By default, get_vpnconnection() will always return based on NM implementation, although
                there are two execetpions to this, which are listed below:

                - If the priority value of another implementation is lower then the priority value of
                  NM implementation, then former will be returned instead of the latter.
                - If connection_implementation is set to a matching property of an implementation of
                  VPNConnectionFactory, then that implementation is to be returned instead.
            :type connection_implementation: str
        """
        pass

    def priority(self):
        """This value determines which implementation takes precedence.

        If no specific implementation has been defined then each connection
        implementation class to calculate it's priority value. This priority value is
        then used by the factory to select the optimal implementation for
        establishing a connection.

        The lower the value, the more priority it has.

        Network manager will always have priority, thus it will always have the value of 100.
        If NetworkManage packages are installed but are not running, then any other implementation
        will take precedence.

        """
        raise NotImplementedError

    @abstractmethod
    def up(self):
        """Up method to establish a vpn connection.

        Before start a connection it must obviously be setup, thus it's
        up to the one implement the class to build it.

        """
        pass

    @abstractmethod
    def down(self):
        """Down method to stop a vpn connection.

        """
        pass


class NMVPNConnection(VPNConnectionFactory):
    """Returns VPN connections based on Network Manager implementation.

    This is the default backend that will be returned. See docstring for
    VPNConnectionFactory.get_vpnconnection() for further explanation on how priorities work.

    A NMVPNConnection can consist of various implementations, such as OpenVPN, IKEv2 or Wireguard.
    """

    @classmethod
    def get_vpnconnection(cls, protocol: str = None, usersettings: object = None):
        """Get VPN connection.

        The type of procotol returned here is based on some conditions, and these conditions are:
        - If only the protocol has been passed, then it should return the respective
          connection based on the desired protocol
        - If only usersettings has been passed, it has to be checked if smart_routing is enabled
          or not. If yes the follow the logic for smart routing, if not then user protocol
          is selected from usersettings.
        - If both are passed then protocol takes always precedence.
        - If none are passed, then a custom logic takes precedence [TBD].
        """
        pass

    @classproperty
    def priority(cls):
        return 100

    def _setup(self):
        raise NotImplementedError

    def up(self):
        raise NotImplementedError

    def down(self):
        raise NotImplementedError


class OpenVPN(NMVPNConnection):
    def get_openvpnconnection(self, protocol: str):
        """Get VPN connection based on protocol."""
        pass


class OpenVPNTCP(OpenVPN):
    """Creates a OpenVPNTCP connection."""
    protocol = "tcp"

    def _setup(self):
        pass

    def up(self):
        pass

    def down(self):
        pass


class OpenVPNUDP(OpenVPN):
    """Creates a OpenVPNUDP connection."""
    protocol = "udp"

    def _setup(self):
        pass

    def up(self):
        pass

    def down(self):
        pass


class Wireguard(NMVPNConnection):
    """Creates a Wireguard connection."""
    protocol = "wg"

    def _setup(self):
        pass

    def up(self):
        pass

    def down(self):
        pass
