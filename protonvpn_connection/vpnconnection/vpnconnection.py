from abc import abstractmethod
from typing import Callable, Optional
from ..abstract_interfaces import AbstractVPNServer, AbstractVPNAccount, AbstractSettings


class VPNConnection:
    """Allows to instantiate a VPN connection.
    The VPNConnection constructor needs to be passed two objects
    that provide different types of information for configuration,
    thus these objects either implement the interfaces AbstractVPNServer and 
    AbstractVPNAccount or just implement the necessary signatures.

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

    Or you could directly use a protocol from a specific implementation:
    ::
        vpnconnection = VPNConnection.get_from_factory("wireguard")
        vpnconnection.up()

    If a specific implementation supports it, a VPNConnection object is persistent
    accross client-code exit. For instance, if you started a VPNConnection with
    :meth:`up`, you can get it back like this :
    ::
        vpnconnection = VPNConnection.get_current_connection()
        vpnconnection.down()

    *Limitations* : Currently you can only handle 1 persistent connection at a time.

    """
    def __init__(
        self, vpnserver: AbstractVPNServer,
        vpnaccount: AbstractVPNAccount,
        settings: AbstractSettings = None
    ):
        """Initialize a VPNConnection object.

            :param vpnserver: AbstractVPNServer type or same signature as AbstractVPNServer.
            :type vpnserver: object
            :param vpnaccount: AbstractVPNAccount type or same signature as AbstractVPNAccount.
            :type vpnaccount: object
            :param settings: Optional.
                Provide an instance that implements AbstractSettings or
                provide an instance that simply exposes methods to match the
                signature of AbstractSettings.
            :type settings: object

        This will set the interal properties which will be used by each implementation/protocol
        to create its configuration file, so that it's ready to establish a VPN connection.
        """
        self._vpnserver = vpnserver
        self._vpnaccount = vpnaccount
        self._settings = settings
        self._subscribers = {}

    @property
    def settings(self):
        return self._settings

    @settings.setter
    def settings(self, new_value: AbstractSettings):
        self._settings = new_value

    @classmethod
    def get_from_factory(cls, protocol: str = None, connection_implementation: str = None):
        """Get a vpn connection from factory.

            :param protocol: Optional.
                protocol to connect with, all in smallcaps
            :type protocol: str
            :param connection_implementation: Optional.
                By default, get_vpnconnection() will always return based on NM implementation, although
                there are two execetpions to this, which are listed below:

                - If the priority value of another implementation is lower then the priority value of
                  NM implementation, then former will be returned instead of the latter.
                - If connection_implementation is set to a matching property of an implementation of
                  VPNConnection, then that implementation is to be returned instead.
            :type connection_implementation: str
        """
        from .networkmanager import NMConnection
        from .native import NativeConnection
        if not protocol:
            protocol = "openvpn_udp"

        if connection_implementation == "networkmanager":
            return NMConnection.factory(protocol)
        elif connection_implementation == "native":
            return NativeConnection.factory(protocol)

        implementations = [NMConnection, NativeConnection]
        implementations.sort(key=lambda x: x._priority())

        return implementations[0].factory(protocol)

    @classmethod
    def get_current_connection(self) -> Optional['VPNConnection']:
        """ Get the current VPNConnection or None if there no current connection. current VPNConnection
            is persistent and can be called after client code exit.

            :return: :class:`VPNConnection`
        """
        from .networkmanager import NMConnection
        from .native import NativeConnection
        implementations = [NMConnection, NativeConnection]
        for implementation in implementations:
            conn = implementation._get_connection()
            if conn:
                return conn

    @property
    def _use_certificate(self):
        import os
        use_certificate = False
        env_var = os.environ.get("PROTONVPN_USE_CERTIFICATE", False)
        if isinstance(env_var, str):
            if env_var.lower() == "true":
                use_certificate = True

        return use_certificate

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
        """Unregister subscribers.

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

    @staticmethod
    def _priority():
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
    def _get_connection(self):
        pass

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
