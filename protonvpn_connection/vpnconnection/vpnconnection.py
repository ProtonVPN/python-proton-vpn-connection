from abc import abstractmethod
from typing import Callable
from ..abstract_interfaces import AbstractVPNServer, AbstractVPNAccount, AbstractUserSettings


class classproperty(property):
    def __get__(self, cls, owner):
        return classmethod(self.fget).__get__(None, owner)()


class VPNConnection:
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
            get_username_and_password -> namedtuple(username, password)

    Basic Usage:
    ::
        vpnconnection = VPNConnection.get_from_factory()
        vpnconnection(vpnserver, vpnaccount)

        # Before establishing you should also decide if you would like to
        # subscribe to the connection status updates with:
        # vpnconnection.register("killswitch")

        vpnconnection.up()

        # to shutdown vpn connection
        vpnconnection.down()

    """
    def __init__(self, vpnserver: AbstractVPNServer, vpnaccount: AbstractVPNAccount):
        """Initialize a VPNConnection object.

            :param vpnserver: AbstractVPNServer type or same signature as AbstractVPNServer.
            :type vpnserver: object
            :param vpnaccount: AbstractVPNAccount type or same signature as AbstractVPNAccount.
            :type vpnaccount: object

        This will set the interal properties which will be used by each implementation/protocol
        to create its configuration file, so that it's ready to establish a VPN connection.
        """
        self.vpnserver = vpnserver
        self.vpnaccount = vpnaccount
        self._subscribers = {}

    @classmethod
    def get_from_factory(
        cls,
        protocol: str = None,
        usersettings: AbstractUserSettings = None,
        connection_implementation: str = None,
    ):
        """Get a vpn connection from factory.

            :param protocol: Optional.
                protocol to connect with, all in smallcaps
            :type protocol: str
            :param usersettings: Optional.
                Provide an instance that implements AbstractUserSettings or
                provide an instance that simply exposes methods to match the
                signature of AbstractUserSettings.
            :type usersettings: object
            :param connection_implementation: Optional.
                By default, get_vpnconnection() will always return based on NM implementation, although
                there are two execetpions to this, which are listed below:

                - If the priority value of another implementation is lower then the priority value of
                  NM implementation, then former will be returned instead of the latter.
                - If connection_implementation is set to a matching property of an implementation of
                  VPNConnection, then that implementation is to be returned instead.
            :type connection_implementation: str
        """
        pass

    def register(self, who: str, callback: Callable = None):
        """Register subscribers.

            :param who: who is the subscriber, smallcaps letters
            :type who: str
            :param callback: Optional.
                The optional callback method that can be passed.
            :type callback: Callable

        Ideally each subscriber should at the least expose an receive_connection_status_update() method,
        so that it can always be called. Though not necessary, each subscriber can pass
        a specific callback method, which the publisher does not care of the name of the method,
        as long as it's callable and that at the least it receives one argument.
        """
        if not callback:
            callback = getattr(who, "receive_connection_status_update")

        self._subscribers[who] = callback

    def unregister(self, who):
        """Unrgister subscribers.

            :param who: who is the subscriber, smallcaps letters
            :type who: str
        """
        try:
            del self._subscribers[who]
        except KeyError:
            pass

    def notify_subscribers(self, connection_status, *args, **kwargs):
        """Notify all subscribers.

        This method is used once there are any status updates on the VPNConnection.
        Any desired args and kwargs can passed although one that should always be passed is
        connections_status.
        """
        for subscriber, callback in self._subscribers.items():
            callback(connection_status, *args, **kwargs)

    @classproperty
    def _priority(self):
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


class NMVPNConnection(VPNConnection):
    """Returns VPN connections based on Network Manager implementation.

    This is the default backend that will be returned. See docstring for
    VPNConnection.get_vpnconnection() for further explanation on how priorities work.

    A NMVPNConnection can return a VPNConnection based on protocols such as OpenVPN, IKEv2 or Wireguard.
    """
    implementation = "networkmanager"

    @classmethod
    def get_connection(cls, protocol: str = None, usersettings: object = None):
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

    def _priority(cls):
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
