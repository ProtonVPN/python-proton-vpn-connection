"""
VPN connection interface.


Copyright (c) 2023 Proton AG

This file is part of Proton VPN.

Proton VPN is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Proton VPN is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with ProtonVPN.  If not, see <https://www.gnu.org/licenses/>.
"""

from __future__ import annotations

import os
import sys
from abc import ABC, abstractmethod
from typing import Optional, Callable, List
from concurrent.futures import Future

from proton.loader import Loader

from proton.vpn.connection.events import Event
from proton.vpn.connection.interfaces import VPNServer, Settings, VPNCredentials
from proton.vpn.connection.persistence import ConnectionPersistence, ConnectionParameters
from proton.vpn.connection.publisher import Publisher
from proton.vpn.connection import states
from proton.vpn.killswitch.interface import KillSwitch


# pylint: disable=too-many-instance-attributes
class VPNConnection(ABC):
    """
    Defines the interface to create a new VPN connection.

    It's the base class for any VPN connection implementation.
    """

    # Class attrs to be set by subclasses.
    backend = None
    protocol = None

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        server: VPNServer,
        credentials: VPNCredentials,
        settings: Settings = None,
        persisted_parameters: ConnectionParameters = None,
        connection_persistence: ConnectionPersistence = None,
        publisher: Publisher = None,
        killswitch: KillSwitch = None

    ):
        """Initialize a VPNConnection object.

        :param server: VPN server to connect to.
        :param credentials: credentials used to authenticate to the VPN server.
        :param settings: Settings to be used when establishing the VPN connection.
            This parameter is optional. When it's not specified the default settings
            will be used instead.
        :param connection_persistence: Connection persistence implementation.
            This parameter is optional. When not specified, the default connection
            persistence implementation will be used instead.
        :param publisher: Publisher implementation. This parameter is optional. Pass it
            only if you know what you are doing.
        """
        self._vpnserver = server
        self._vpncredentials = credentials
        self._settings = settings
        self._persisted_parameters = persisted_parameters

        self._killswitch = killswitch or KillSwitch.get()()

        self._connection_persistence = connection_persistence or ConnectionPersistence()
        self._publisher = publisher or Publisher()

        if self._persisted_parameters:
            self._unique_id = self._persisted_parameters.connection_id
            self.initial_state = self._initialize_persisted_connection(
                self._persisted_parameters
            )
        else:
            self._unique_id = None
            self.initial_state = states.Disconnected(states.StateContext(connection=self))

    @abstractmethod
    def _initialize_persisted_connection(
            self, persisted_parameters: ConnectionParameters
    ) -> states.State:
        """
        Initializes the state of this instance of VPN connection according
        to previously persisted connection parameters and returns its current state.
        Needs to be provided by the VPN connection implementation.
        """

    @abstractmethod
    def start(self):
        """
        Starts the VPN connection.

        Important: this method is expected to be implemented in an asynchronous manner.
        It should never block while the connection is being established.
        """

    @abstractmethod
    def stop(self):
        """Stops the VPN connection.

        Important: this method is expected to be implemented in an asynchronous manner.
        It should never block while the connection is being shut down.
        """

    def register(self, subscriber: Callable[[Event], None]):
        """
        Registers a subscriber to be notified whenever a new connection event happens.

        The subscriber will be called passing the connection event as argument.
        """
        self._publisher.register(subscriber)

    def unregister(self, subscriber: Callable[[Event], None]):
        """Unregister a previously registered connection events subscriber."""
        self._publisher.unregister(subscriber)

    def _notify_subscribers(self, event: Event):
        """Notifies all subscribers of a connection event.

        Subscribers are called passing the connection event as argument.

        This is a utility method that VPN connection implementations can use to notify
        subscribers when a new connection event happens.

        :param event: the event to be notified to subscribers.
        """
        self._publisher.notify(event=event)

    @staticmethod
    def create(server: VPNServer, credentials: VPNCredentials, settings: Settings = None,
               protocol: str = None, backend: str = None):
        """
        Creates a new VPN connection object. Note the VPN connection won't be initiated. For that
        to happen, see the `start` method.

        :param server: VPN server to connect to.
        :param credentials: Credentials used to authenticate to the VPN server.
        :param settings: VPN settings used to create the connection.
        :param protocol: protocol to connect with. If None, the default protocol will be used.
        :param backend: Name of the class implementing the VPNConnection interface.
            If None, the default implementation will be used.
        """
        backend = Loader.get("backend", class_name=backend)
        protocol = protocol.lower() if protocol else None
        protocol_class = backend.factory(protocol)
        return protocol_class(server, credentials, settings)

    @classmethod
    def get_current_connection(
            cls, connection_persistence: ConnectionPersistence = None
    ) -> Optional[VPNConnection]:
        """
        :return: the current VPN connection or None if there isn't one.
        """
        connection_persistence = connection_persistence or ConnectionPersistence()
        persisted_parameters = connection_persistence.load()
        if not persisted_parameters:
            return None

        backend = Loader.get("backend", persisted_parameters.backend)
        current_connection = backend.get_persisted_connection(persisted_parameters)

        return current_connection

    @property
    def server_id(self) -> str:
        """Returns the VPN server ID of this VPN connection."""
        # VPNConnection is only partially restored when deserialized from disk:
        # it's constructed without neither VPNServer, VPNCredentials
        # nor Settings objects. It only loads the parameters that were
        # persisted to disk.
        if self._vpnserver:
            server_id = self._vpnserver.server_id
        elif self._persisted_parameters:
            server_id = self._persisted_parameters.server_id
        else:
            server_id = None

        return server_id

    @property
    def server_name(self) -> str:
        """Returns the VPN server name of this VPN connection."""
        # VPNConnection is only partially restored when deserialized from disk:
        # it's constructed without neither VPNServer, VPNCredentials
        # nor Settings objects. It only loads the parameters that were
        # persisted to disk.
        if self._vpnserver:
            server_name = self._vpnserver.server_name
        elif self._persisted_parameters:
            server_name = self._persisted_parameters.server_name
        else:
            server_name = None

        return server_name

    @property
    def server_ip(self) -> str:
        """Returns the VPN server IP of this VPN connection."""
        server_ip = None
        if self._vpnserver:
            server_ip = self._vpnserver.server_ip

        return server_ip

    @property
    def killswitch(self) -> int:
        """Returns stored kill switch setting.

        If internal settings object is not set, then we try to fetch it from
        persisted parameters. If there they're not found then we default to
        disabled.
        """
        if self._settings:
            return self._settings.killswitch

        return self._persisted_parameters.killswitch

    @property
    def settings(self) -> Settings:
        """ Current settings of the connection :
            Some settings can be changed on the fly and are RW :
            netshield level, kill switch enabled/disabled, split tunneling,
            VPN accelerator, custom DNS.
            Other settings are RO and cannot be changed once the connection
            is instantiated: VPN protocol.
        """
        return self._settings

    @settings.setter
    def settings(self, new_value: Settings):
        """ Change the current settings of the connection, only valid for the
        RW settings of the connection.
        """
        # FIX-ME: Should be defined when settings can be set
        self._settings = new_value

    @property
    def _use_certificate(self):
        use_certificate = False
        env_var = os.environ.get("PROTON_VPN_USE_CERTIFICATE", False)
        if isinstance(env_var, str):
            env_filtered = env_var.strip("").replace(" ", "").lower()
            if env_filtered == "true" or "true" in env_filtered:
                use_certificate = True

        return use_certificate

    @classmethod
    @abstractmethod
    def _get_priority(cls) -> int:
        """
        Priority of the VPN connection implementation.

        To be implemented by subclasses.

        When no backend is specified when creating a VPN connection instance
        with `VPNConnection.create`, the VPN connection implementation is
        chosen based on the priority value returned by this method.

        The lower the value, the more priority it has.

        Ideally, the returned priority value should not be hardcoded but
        calculated based on the environment. For example, a VPN connection
        implementation using NetworkManager could return a high priority
        when the NetworkManager service is running or a low priority when it's
        not.
        """

    @classmethod
    @abstractmethod
    def _validate(cls) -> bool:
        """
        Determines whether the VPN connection implementation is valid or not.
        To be implemented by subclasses.

        If this method returns `False` then the VPN connection implementation
        will be skipped when creating a VPN connection instance with
        `VPNConnection.create`.

        :return: `True` if the implementation is valid or `False` otherwise.
        """

    def add_persistence(self):
        """
        Stores the connection parameters to disk.

        The connection parameters (e.g. backend, protocol, connection ID,
        server name) are stored to disk so that they can be loaded again
        after an unexpected crash.
        """
        params = ConnectionParameters(
            connection_id=self._unique_id,
            backend=type(self).backend,
            protocol=type(self).protocol,
            server_id=self.server_id,
            server_name=self.server_name,
            killswitch=self.killswitch
        )
        self._connection_persistence.save(params)
        self._persisted_parameters = params

    def remove_persistence(self):
        """
        Works in the opposite way of add_persistence. It removes the
        persistence file. This is used in conjunction with down, since if the
        connection is turned down, we don't want to keep any persistence files.
        """
        self._connection_persistence.remove()

    def enable_killswitch(self, vpn_server: VPNServer = None) -> Future:
        """
        Prevents accidental leaks.

        This method should be called before establishing IPv4 VPN connections,
        so that no traffic leaks through the IPv6 interface while connected
        to the VPN.
        """
        return self._killswitch.enable(vpn_server)

    def disable_killswitch(self) -> Future:
        """
        Stops kill switch.

        This method should be called after the user willingly ends a VPN connection.
        """
        return self._killswitch.disable()

    def enable_ipv6_leak_protection(self) -> Future:
        """
        Prevents IPv6 leaks.

        This method should be called before establishing IPv4 VPN connections,
        so that no traffic leaks through the IPv6 interface while connected
        to the VPN.
        """
        return self._killswitch.enable_ipv6_leak_protection()

    def disable_ipv6_leak_protection(self) -> Future:
        """
        Stops preventing IPv6 leaks.

        This method should be called after the user willingly ends a VPN connection.
        """
        return self._killswitch.disable_ipv6_leak_protection()

    def _get_user_pass(self, apply_feature_flags=False):
        """*For developers*

        :param apply_feature_flags: if feature flags are to be suffixed to username

        In case of non-certificate based authentication, username and password need
        to be provided for authentication. In such cases, the username can be optionally
        suffixed with different options, of which are fetched from `self._settings`

        Usage:

        .. code-block::

            from proton.vpn.connection import VPNConnection

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
        user_data = self._vpncredentials.userpass_credentials
        username = user_data.username
        if apply_feature_flags:
            flags = self._get_feature_flags()
            username = "+".join([username] + flags)  # each flag must be preceded by "+"

        return username, user_data.password

    def _get_feature_flags(self) -> List[str]:
        """
        Creates a list of feature flags that are fetched from `self._settings`.
        These feature flags are used to suffix them to a username, to trigger server-side
        specific behavior.
        """
        list_flags = []

        if sys.platform.startswith("linux"):
            list_flags.append("pl")
        elif sys.platform.startswith("win32") or sys.platform.startswith("cygwin"):
            list_flags.append("pw")
        elif sys.platform.startswith("darwin"):
            list_flags.append("pm")

        # This is used to ensure that the provided IP matches the one
        # from the exit IP.
        label = self._vpnserver.label
        if label:
            list_flags.append(f"b:{label}")

        if self._settings is None:
            return list_flags

        features = self._settings.features

        list_flags.append(f"f{features.netshield}")

        if not features.vpn_accelerator:
            list_flags.append("nst")
        if features.port_forwarding:
            list_flags.append("pmp")
        if features.moderate_nat:
            list_flags.append("nr")

        return list_flags
