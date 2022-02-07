from abc import abstractmethod
from typing import Callable, Optional
from .interfaces import VPNServer, Settings, VPNCredentials
from .enum import ConnectionStateEnum


class VPNConnection:
    """

    VPNConnection is the base class for which all types of connection need to derive from.
    It contains most of the logic that is needed for either creating a new backend
    or protocol.

    Apart from VPNConnection being a base class for vpn connections, it too provides
    vpnconnections via its factory.

    Usage:
    ::
        from protonvpn.vpnconnection import VPNConnection

        vpnconnection_type = VPNConnection.get_from_factory()
        vpnconnection=vpnconnection_type(vpnserver, vpncredentials)

        # Before establishing you should also decide if you would like to
        # subscribe to the connection status updates with:
        # see more inte register()
        # vpnconnection.register("killswitch")

        vpnconnection.up()

        # to shutdown vpn connection
        vpnconnection.down()

    Or you could directly use a protocol from a specific backend:
    ::
        vpnconnection_type = VPNConnection.get_from_factory("wireguard")
        vpnconnection=vpnconnection_type(vpnserver, vpncredentials)
        vpnconnection.up()

    If a specific backend supports it, a VPNConnection object is persistent
    accross client-code exits. For instance, if you started a VPNConnection with
    :meth:`up`, you can get it back like this in another instance of your client code :
    ::
        vpnconnection = VPNConnection.get_current_connection()
        vpnconnection.down()

    *Limitations*:Currently you can only handle 1 persistent connection at a time.

    """

    def __init__(
        self,
        vpnserver: VPNServer,
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

        This will set the interal properties which will be used by each backend/protocol
        to create its configuration file, so that it's ready to establish a VPN connection.
        """
        self._vpnserver = vpnserver
        self._vpncredentials = vpncredentials
        self._settings = settings
        self._unique_id = None
        self._subscribers = {}

    @abstractmethod
    def up(self) -> None:
        """Up method to establish a vpn connection.

        Before start a connection it must be setup, thus it's
        up to the one implement the class to build it.

        :raises AuthenticationError: The credentials used to authenticate on the VPN are not correct
        :raises ConnectionTimeoutError: No answer from the VPN server for too long
        :raises MissingBackendDetails: The backend cannot be used.
        :raises UnexpectedError: When an expected/unhandled error occurs.
        """
        pass

    @abstractmethod
    def down(self) -> None:
        """Down method to stop a vpn connection.

        :raises MissingVPNConnectionError: When there is no connection to disconnect.
        :raises UnexpectedError: When an expected/unhandled error occurs.
        """
        pass

    @classmethod
    def get_from_factory(cls, protocol: str = None, backend: str = None):
        """Get a vpn connection from factory.

            :param protocol: Optional.
                protocol to connect with, all in smallcaps
            :type protocol: str
            :param backend: Optional.
                By default, get_vpnconnection() will always return based on NM backend, although
                there are two execetpions to this, which are listed below:

                - If the priority value of another backend is lower then the priority value of
                  NM backend, then former will be returned instead of the latter.
                - If backend is set to a matching property of an backend of
                  VPNConnection, then that backend is to be returned instead.
            :type backend: str
        """
        from proton.loader import Loader
        all_backends = Loader.get_all("backend")
        sorted_backends = sorted(all_backends, key=lambda _b: _b.priority, reverse=True)

        if backend:
            try:
                return [_b.cls for _b in sorted_backends if _b.class_name == backend][0].cls.factory(protocol)
            except (IndexError, AttributeError):
                return None

        for backend in sorted_backends:
            if not backend.cls._validate():
                continue

            return backend.cls.factory(protocol)

    @classmethod
    def get_current_connection(self) -> Optional['VPNConnection']:
        """ Get the current VPNConnection or None if there no current connection. current VPNConnection
            is persistent and can be called after client code exit.

            :return: :class:`VPNConnection`
        """
        from proton.loader import Loader
        all_backends = Loader.get_all("backend")
        sorted_backends = sorted(all_backends, key=lambda _b: _b.priority, reverse=True)

        for backend in sorted_backends:
            conn = backend.cls._get_connection()
            if conn:
                return conn

    @abstractmethod
    def cancel(self) -> bool:
        """
        If for some reasons you would like to stop the current connection before it's established,
        then you can use the cancel method, which cancels the current connection activity.

        Has to be overriden by all classes that derive from VPNConnection

            :return: if connection was cancelled or not
            :rtype: bool
        """
        raise NotImplementedError

    @property
    def settings(self) -> Settings:
        """ Current settings of the connection :
            Some settings can be changed on the fly and are RW :
            netshield level, kill switch enabled/disabled, split tunneling, VPN accelerator, custom DNS.
            Other settings are RO and cannot be changed once the connection is instanciated :
            VPN protocol.
        """
        return self._settings

    @settings.setter
    def settings(self, new_value: Settings):
        """ Change the current settings of the connection, only valid for the RW settings of the connection.
        """
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

    def register(self, who: object, callback: Callable = None) -> None:
        """
        Register a subscriber to receive connection status updates.

            :param who: object/class instance that wants to receive connection status updates
            :type who: object
            :param callback: Optional.
                Pass an alternative callback method.
            :type callback: Callable

        Usage:
        ::
            class StatusUpdateReceiver:

                def _connection_status_update(self, status):
                    print(status)
                    # or do something else with the received status

            status_update_receives = StatusUpdateReceiver()

            from protonvpn.vpnconnection import VPNConnection

            vpnconnection = VPNConnection.get_from_factory()
            vpnconnection(vpnserver, vpncredentials)
            vpnconnection.register(status_update_receives)

        Each subscriber should expose `_connection_status_update()` method,
        to guarantee that the callback is always called. If the subscriber does not provide
        `_connection_status_update()` method, then subscribers needs toe ensure that the
        alternative callback method is passed, ie:
        ::
            class StatusUpdateReceiver:

                def _my_custom_method(self, status):
                    print(status)
                    # or do something else with the received status

            status_update_receives = StatusUpdateReceiver()

            from protonvpn.vpnconnection import VPNConnection

            vpnconnection = VPNConnection.get_from_factory()
            vpnconnection(vpnserver, vpncredentials)
            vpnconnection.register(
                status_update_receives,
                callback = status_update_receives._my_custom_method
            )

        """
        if not callback:
            callback = getattr(who, "_connection_status_update")

        self._subscribers[who] = callback

    def unregister(self, who) -> None:
        """
        Unregister subscriber to stop receiving connection status updates.

            :param who: who is the subscriber, smallcaps letters
            :type who: str

        Usage:
        ::
            class StatusUpdateReceiver:

                def _connection_status_update(self, status):
                    print(status)
                    # or do something else with the received status

            status_update_receives = StatusUpdateReceiver()

            from protonvpn.vpnconnection import VPNConnection

            vpnconnection = VPNConnection.get_from_factory()
            vpnconnection(vpnserver, vpncredentials)
            vpnconnection.register(status_update_receives)

            # lower in the code I then decide that I no longer wish to
            # receive connection status updates, so I decide to
            # unregister myself as a subscriber:
            vpnconnection.unregister(status_update_receives)

        """
        try:
            del self._subscribers[who]
        except KeyError:
            pass

    def _notify_subscribers(self, connection_status: ConnectionStateEnum) -> None:
        """*For developers*

        Notifies the subscribers about connection state changes.

        Each backend and/or protocol have to call this method whenever the connection
        state changes, so that each subscriber can receive states changes whenever they occur.

            :param connection_status: the current status of the connection
            :type connection_status: ConnectionStateEnum

        Usage:
        ::
            from protonvpn.vpnconnection import VPNConnection

            class CustomBackend(VPNConnection):
                backend = "custom_backend"

                ...

                def up(self):
                    self._notify_subscribers(ConnectionStateEnum.DISCONNECTED)
                    self._setup()
                    self._persist_connection()
                    self._start_connection()
                    # Connection has been established
                    self._notify_subscribers(ConnectionStateEnum.CONNECTED)

                def down(self):
                    self._stop_connection()
                    self._remove_connection_persistence()

                def _stop_connection(self):
                    self._notify_subscribers(ConnectionStateEnum.DISCONNECTING)
                    # stopped connection
                    self._notify_subscribers(ConnectionStateEnum.DISCONNECTED)

                def _setup(self):
                    # setup connection
                    self._notify_subscribers(ConnectionStateEnum.CONNECTING)

        Note: Some code has been ommitted for readability.
        """
        for subscriber, callback in self._subscribers.items():
            callback(connection_status)

    @abstractmethod
    def _get_connection(self) -> 'VPNConnection':
        """*For developers*
        Each backend has to provide a classmethod of getting a connection.

            :return: either vpn connection if exists or none
            :rtype: VPNConnection | None

        Usage:
        ::
            from protonvpn.vpnconnection import VPNConnection

            class CustomBackend(VPNConnection):
                backend = "custom_backend"

                @classmethod
                def _get_connection(cls):
                    classes = [OpenVPNTCP, OpenVPNUDP, Wireguard, Strongswan]

                    for _class in classes:
                        vpnconnection = _class(None, None)
                        if vpnconnection._get_protonvpn_connection():
                            return vpnconnection

        Note: Some code has been ommitted for readability.
        """
        pass

    @classmethod
    def _get_priority(cls) -> int:
        """*For developers*

        Priority value determines which backend takes precedence.

        If no specific backend has been defined then each connection
        backend class to calculate it's priority value. This priority value is
        then used by the factory to select the optimal backend for
        establishing a connection.

        The lower the value, the more priority it has.

        Network manager will always have priority, thus it will always have the value of 100.
        If NetworkManage packages are installed but are not running, then any other backend
        will take precedence.

        Usage:
        ::
            from protonvpn.vpnconnection import VPNConnection

            class CustomBackend(VPNConnection):
                backend = "custom_backend"

                ...

                @classmethod
                def _get_priority(cls):
                    # Either return a hard-coded value (which is discoureaged),
                    # or calculate it based on some system settings
                    return 150

        Note: Some code has been ommitted for readability.
        """
        return None

    @classmethod
    def _validate(cls):
        return False

    def _ensure_unique_id_is_set(self) -> None:
        """*For developers*

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
        from .persistence import ConnectionPeristence
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
        """*For developers*

        If for some reason the component crashes, we need to know which connection we
        should be handling. Thus the connection unique ID is prefixed with the protocol
        and backend and stored to a file.

        Usage:
        ::

            from protonvpn.vpnconnection import VPNConnection

            class CustomBackend(VPNConnection):
                backend = "custom_backend"

                ...

                def up(self):
                    self._setup()

                    # `_persist_connection` creates a file with filename in the format of
                    # <BACKEND>_<PROTOCOl>_<UNIQUE_ID>
                    # where:
                    #   - `<BACKEND>` is `backend`
                    #   - `<PROTOCOl>` is the provided protocol to factory
                    #   - `<UNIQUE_ID>` is `self._unique_id`
                    # so the file would look like this (given that we've selected udp as protocol):
                    # `custom_backend_openvpn_udp_132123-123sdf-12312-fsd`

                    self._persist_connection()

                    self._start_connection()

                def down(self):
                    self._stop_connection()
                    self._remove_connection_persistence()

                def _stop_connection(self):
                    # stopped connection

                def _setup(self):
                    # setup connection
                    # after setup, the connecction uuid is 132123-123sdf-12312-fsd
                    self._unique_id = 132123-123sdf-12312-fsd

        Note: Some code has been ommitted for readability.
        """
        from .persistence import ConnectionPeristence
        persistence = ConnectionPeristence()
        conn_id = self._persistence_prefix + self._unique_id
        persistence.persist(conn_id)

    def _remove_connection_persistence(self):
        """*For developers*

        Works in the opposite way of _persist_connection. It removes the persitence
        file. This is used in conjunction with down, since if the connection is turned down,
        we don't want to keep any persistence files.
        """
        from .persistence import ConnectionPeristence
        persistence = ConnectionPeristence()
        conn_id = self._persistence_prefix + self._unique_id
        persistence.remove_persist(conn_id)

    def _get_user_pass(self, apply_feature_flags=False):
        """*For developers*

            :param apply_feature_flags: if feature flags are to be suffixed to username
            :type apply_feature_flags: bool

        In case of non-certificate based authentication, username and password need
        to be provided for authentication. In such cases, the username can be optionally
        suffixed with different options, of which are fetched from `self._settings`

        Usage:
        ::

            from protonvpn.vpnconnection import VPNConnection

            class CustomBackend(VPNConnection):
                backend = "custom_backend"

                ...

                def _setup(self):
                    if not use_ceritificate:
                        # In this case, the username will have suffixes added given
                        # that any of the them are set in `self._settings`
                        user, pass = self._get_user_pass()

                        # Then add the username and password to the configurations

        """
        user_data = self._vpncredentials.vpn_get_username_and_password()
        username = user_data.username
        if apply_feature_flags:
            flags = self._get_feature_flags()
            username = "+".join([username] + flags)  # each flag must be preceded by "+"

        return username, user_data.password

    def _get_feature_flags(self) -> Optional[list]:
        """*For developers*

        Creates a list of feature flags that are fetched from `self._settings`.
        These feature flags are used to suffix them to a username, to trigger special
        behaviour on server-side.
        """
        list_flags = []
        self._transform_features_to_flags(list_flags)
        return list_flags

    def _transform_features_to_flags(self, list_flags: Optional[list]) -> Optional[list]:
        """*For developers*

        Transform the flags into features to be suffixed to username.
        """
        features = self._settings
        if features is None:
            list_flags.append("nsm")
            return

        v = features.netshield
        list_flags.append(f"f{v}")

        if not features.vpn_accelerator:
            list_flags.append("nst")
        if features.port_forwarding:
            list_flags.append("pmp")
        if not features.random_nat:
            list_flags.append("nr")
        if features.safe_mode:
            list_flags.append("sm")
        else:
            list_flags.append("nsm")
