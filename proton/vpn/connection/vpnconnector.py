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

import asyncio
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
    async def get_instance(cls):
        """
        Gets a singleton instance.

        Each VPNConnector instance ensures a single connection is active at a time.
        However, a singleton instance is required to avoid creating multiple active
        VPN connections by using multiple VPNConnector instances.
        """
        if cls._instance:
            return cls._instance

        cls._instance = VPNConnector()
        initial_state = await cls._determine_initial_state()
        await cls._instance.initialize_state(initial_state)
        return cls._instance

    @classmethod
    async def _determine_initial_state(cls):
        """Determines the initial state of the state machine."""
        current_connection = await VPNConnection.get_current_connection()

        if current_connection:
            return current_connection.initial_state

        return states.Disconnected(StateContext())

    def __init__(self, state: states.State = None):
        self._current_state = state
        self._publisher = Publisher()
        self._lock = asyncio.Lock()

    async def initialize_state(self, state: states.State):
        """Initializes the state machine with the specified state."""
        connection = state.context.connection
        if connection:
            connection.register(self._on_connection_event)

        await self._update_state(state)

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
    async def connect(
            self, server: VPNServer, credentials: VPNCredentials, settings: Settings,
            protocol: str = None, backend: str = None
    ):
        """Connects to a VPN server."""
        connection = VPNConnection.create(
            server, credentials, settings, protocol, backend
        )

        connection.register(self._on_connection_event)

        await self._on_connection_event(
            events.Up(events.EventContext(connection=connection))
        )

    async def disconnect(self):
        """Disconnects the current VPN connection, if any."""
        await self._on_connection_event(
            events.Down(events.EventContext(connection=self.current_connection))
        )

    def register(self, subscriber: Callable[[states.State], None]):
        """Registers a new subscriber to connection state updates."""
        self._publisher.register(subscriber)

    def unregister(self, subscriber: Callable[[states.State], None]):
        """Unregister an existing subscriber from connection state updates."""
        self._publisher.unregister(subscriber)

    async def _on_connection_event(self, event: events.Event):
        """
        Callback called when a connection event happens.
        """
        # The following lock guaranties that each new event is processed only
        # when the previous event was fully processed.
        async with self._lock:
            triggered_events = 0
            while event:
                triggered_events += 1
                if triggered_events > 99:
                    raise RuntimeError("Maximum number of chained connection events was reached.")

                new_state = self.current_state.on_event(event)
                event = await self._update_state(new_state)

    async def _update_state(self, new_state) -> Optional[events.Event]:
        if new_state is self.current_state:
            return None

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

        state_tasks = asyncio.create_task(self._current_state.run_tasks())
        await self._publisher.notify(new_state)
        new_event = await state_tasks

        return new_event
