from abc import abstractmethod
from typing import Callable, Optional
from ..interfaces import VPNServer, VPNCertificate, Settings, VPNCredentials


class VPNConnection:
    """Allows to instantiate a VPN connection.
    The VPNConnection constructor needs to be passed two objects
    that provide different types of information for configuration,
    thus these objects either implement the interfaces VPNServer and
    VPNCredentials or just implement the necessary signatures.

    Basic Usage:
    ::
        vpnconnection = VPNConnection.get_from_factory()
        vpnconnection(vpnserver, vpncredentials)

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
    accross client-code exits. For instance, if you started a VPNConnection with
    :meth:`up`, you can get it back like this in another instance of your client code :
    ::
        vpnconnection = VPNConnection.get_current_connection()
        vpnconnection.down()

    *Limitations* : Currently you can only handle 1 persistent connection at a time.

    """
    def __init__(
        self, vpnserver: VPNServer,
        vpncredentials: VPNCredentials,
        settings: Settings = None
    ):
        """Initialize a VPNConnection object.

            :param vpnserver: VPNServer type or same signature as VPNServer.
            :type vpnserver: object
            :param vpncredentials: VPNCredentials type or same signature as VPNCredentials.
            :type vpncredentials: object
            :param settings: Optional.
                Provide an instance that implements Settings or
                provide an instance that simply exposes methods to match the
                signature of Settings.
            :type settings: object

        This will set the interal properties which will be used by each implementation/protocol
        to create its configuration file, so that it's ready to establish a VPN connection.
        """
        self._vpnserver = vpnserver
        self._vpncredentials = vpncredentials
        self._settings = settings
        self._unique_id = None
        self._subscribers = {}

    @abstractmethod
    def up(self):
        """Up method to establish a vpn connection.

        Before start a connection it must be setup, thus it's
        up to the one implement the class to build it.
        """
        pass

    @abstractmethod
    def down(self):
        """Down method to stop a vpn connection."""
        pass

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
    def settings(self):
        return self._settings

    @settings.setter
    def settings(self, new_value: Settings):
        self._settings = new_value

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

    def _notify_subscribers(self, connection_status, *args, **kwargs):
        """Notify all subscribers.

        This method is used once there are any status updates on the VPNConnection.
        Any desired args and kwargs can passed although one that should always be passed is
        connections_status.
        """
        for subscriber, callback in self._subscribers.items():
            callback(connection_status, *args, **kwargs)

    @abstractmethod
    def _get_connection(self):
        pass

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

    def _ensure_unique_id_is_set(self):
        """Ensure that the unique id is set

        It is crucial that unique_id is always set and current. The only times
        where it can be empty is when there is no VPN connection.

        Suppose the following:
        ::
            vpnconnection = VPNConnection.get_current_connection()
            if not vpnconnection:
                print("There is no connection")

        The way to determine if there is connection is through persistence, where
        the filename is composed of various elemets, where the unique id plays a key
        part in it (see persist_connection()).

        The unique ID is also used to find connections in NetworkManager.
        """
        from ..persistence import ConnectionPeristence
        persistence = ConnectionPeristence()

        try:
            if not self._unique_id:
                self._unique_id = persistence.get_persisted(self._persistence_prefix)
        except AttributeError:
            self._unique_id = persistence.get_persisted(self._persistence_prefix)

        if not self._unique_id:
            return

        self._unique_id = self._unique_id.replace(self._persistence_prefix, "")

    def _persist_connection(self):
        """Persist a connection.

        If for some reason component crashes, we need to know which connection we
        should be handling. Thus the connection unique ID is prefixed with the protocol
        and implementation and stored to a file. Ie:
            - A connection unique ID is 132123-123sdf-12312-fsd
            - A file is created
            - The filename and content is: <IMPLEMENTATION>_<PROTOCOl>_132123-123sdf-12312-fsd
              - where IMPLEMENTATION can be networkmanager or native
              - where PROTOCOl can be openvpn_tcp, openvpn_udp or wireguard

        Following the previous example, our file will end up being called nm_wireguard_132123-123sdf-12312-fsd,
        which tells us that we used NetworkManager as an implementation and we've used the Wireguard protocol.
        Knowing this, we can correctly instatiate for later use.
        """
        from ..persistence import ConnectionPeristence
        persistence = ConnectionPeristence()
        conn_id = self._persistence_prefix + self._unique_id
        persistence.persist(conn_id)

    def _remove_connection_persistence(self):
        """Remove connection persistence.

        Works in the opposite way of _persist_connection. As it removes the peristence
        file. This is used in conjunction with down, since if the connection is turned down,
        we don't want to keep any persistence files.
        """
        from ..persistence import ConnectionPeristence
        persistence = ConnectionPeristence()
        conn_id = self._persistence_prefix + self._unique_id
        persistence.remove_persist(conn_id)

    def _get_credentials(self, flags: list = None):
        user_data = self._vpnaccount.get_username_and_password()
        username = user_data.username
        if flags is not None:
            username = "+".join([username] + flags)  # each flag must be preceded by "+"
        return username, user_data.password

    def _transform_features_to_flags(self) -> Optional[list]:
        list_flags = []
        features = self.settings
        if features is not None:
            if not features.vpn_accelerator:
                list_flags.append("nst")
            v = features.netshield_level
            list_flags.append(f"f{v}")
            if features.port_forwarding:
                list_flags.append("pmp")
            if not features.random_nat:
                list_flags.append("nr")
            if features.safe_mode:
                list_flags.append("sm")
            else:
                list_flags.append("nsm")
            return list_flags
        else:
            list_flags.append("nsm")
        return list_flags
