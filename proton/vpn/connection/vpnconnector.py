"""
VPN connector.


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

import threading
from threading import Lock
from typing import Optional, Callable

from proton.vpn import logging
from proton.vpn.connection import events, states, VPNConnection, VPNServer, VPNCredentials, Settings
from proton.vpn.connection.publisher import Publisher
from proton.vpn.connection.states import StateContext

logger = logging.getLogger(__name__)


class VPNConnector:
    """
    Allows connecting/disconnecting to/from Proton VPN servers, as well as querying
    information about the current VPN connection, or subscribing to its state
    updates.

    Multiple simultaneous VPN connections are not allowed. If a connection
    already exists when a new one is requested then the current one is brought
    down before starting the new one.

    A singleton instance is used to ensure a single VPN connection at a time.
    """
    _instance: VPNConnector = None

    @classmethod
    def get_instance(cls):
        """
        Gets a singleton instance.

        Each VPNConnector instance ensures a single connection is active at a time.
        However, a singleton instance is required to avoid creating multiple active
        VPN connections by using multiple VPNConnector instances.
        """
        if cls._instance:
            return cls._instance

        initial_state = cls._determine_initial_state()
        cls._instance = VPNConnector(initial_state)
        return cls._instance

    @classmethod
    def _determine_initial_state(cls):
        """Determines the initial state of the state machine."""
        current_connection = VPNConnection.get_current_connection()

        if current_connection:
            return current_connection.initial_state

        return states.Disconnected(StateContext())

    def __init__(self, initial_state: states.State):
        self._current_state = None
        self._publisher = Publisher()
        self._lock = Lock()

        connection = initial_state.context.connection
        if connection:
            connection.register(self._on_connection_event)

        self._update_state(initial_state)

    @property
    def current_state(self) -> states.State:
        """Returns the state of the current VPN connection."""
        return self._current_state

    @property
    def current_connection(self) -> Optional[VPNConnection]:
        """Returns the current VPN connection or None if there isn't one."""
        return self.current_state.context.connection if self.current_state else None

    @property
    def current_server_id(self) -> Optional[str]:
        """
        Returns the server ID of the current VPN connection.

        Note that by if the current state is disconnected, `None` will be
        returned if a VPN connection was never established. Otherwise,
        the server ID of the last server the connection was established to
        will be returned instead.
        """
        return self.current_connection.server_id if self.current_connection else None

    @property
    def is_connection_ongoing(self) -> bool:
        """Returns whether there is currently a VPN connection ongoing or not."""
        return not isinstance(self._current_state, (states.Disconnected, states.Error))

    # pylint: disable=too-many-arguments
    def connect(
            self, server: VPNServer, credentials: VPNCredentials, settings: Settings,
            protocol: str = None, backend: str = None
    ):
        """Connects to a VPN server."""
        connection = VPNConnection.create(
            server, credentials, settings, protocol, backend
        )

        connection.register(self._on_connection_event)

        self._on_connection_event(
            events.Up(events.EventContext(connection=connection))
        )

    def disconnect(self):
        """Disconnects the current VPN connection, if any."""
        self._on_connection_event(
            events.Down(events.EventContext(connection=self.current_connection))
        )

    def register(self, subscriber: Callable[[states.State], None]):
        """Registers a new subscriber to connection state updates."""
        self._publisher.register(subscriber)

    def unregister(self, subscriber: Callable[[states.State], None]):
        """Unregister an existing subscriber from connection state updates."""
        self._publisher.unregister(subscriber)

    def _on_connection_event(self, event: events.Event):
        """
        Callback called when a connection event happens.
        """
        new_event = self._process_connection_event(event)

        if new_event:
            self._on_connection_event(new_event)

    def _process_connection_event(self, event: events.Event) -> Optional[events.Event]:
        """
        Processes new connection events, updating the current VPN state and running the
        tasks associated with the new VPN state. It may also return a new event, if
        it was generated when running the tasks associated with the new VPN state.

        A lock is used to make this method thread-safe. Therefore, even if multiple threads
        run it concurrently, the current event will be fully processed before starting
        processing the next one. Currently, this method may be called from multiple threads:
         - the app's (main) thread, when the user requests to start/stop a connection,
         - and the thread starting/stopping the VPN connection, since connection
           implementations often use separate threads for asynchronous operations.

        :param event: the event to be processed.
        :returns: an optional new event, if it was generated while processing the current event.
        """
        thread_id = threading.get_ident()
        logger.debug(f"Thread {thread_id} sent event {event}")
        with self._lock:
            logger.debug(f"Thread {thread_id} is requesting to process event {event}")
            new_state = self.current_state.on_event(event)
            if new_state is self.current_state:
                # If the event didn't trigger a state change then there's nothing to do.
                return None

            new_event = self._update_state(new_state)
            logger.debug(f"Thread {thread_id} finished processing event {event}")
            return new_event

    def _update_state(self, new_state) -> Optional[states.Event]:
        old_state = self._current_state
        self._current_state = new_state
        logger.info(
            f"{type(self._current_state).__name__}"
            f"{' (initial state)' if not old_state else ''}",
            category="CONN", event="STATE_CHANGED"
        )

        if not self.is_connection_ongoing and self._current_state.context.connection:
            # Unregister from connection event updates once the connection ended.
            self._current_state.context.connection.unregister(self._on_connection_event)

        new_event = self._current_state.run_tasks()
        self._publisher.notify(new_state)

        return new_event
