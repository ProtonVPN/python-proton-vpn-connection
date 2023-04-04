"""
The different VPN connection states and their transitions is defined here.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
from concurrent.futures import Future

from proton.vpn import logging
from proton.vpn.connection import events
from proton.vpn.connection.enum import ConnectionStateEnum
from proton.vpn.connection.events import EventContext
from proton.vpn.connection.exceptions import ConcurrentConnectionsError

if TYPE_CHECKING:
    from proton.vpn.connection.vpnconnection import VPNConnection


# pylint: disable=too-few-public-methods


logger = logging.getLogger(__name__)


@dataclass
class StateContext:
    """
    Relevant state context data.

    Attributes:
        event: Event that led to the current state. It could be `None` on the
            context for the initial state, after initializing the state machine.
        connection: current VPN connection. They only case where this
            attribute could be None is on the initial state, if there is not
            already an existing VPN connection.
    """
    event: Optional[events.Event] = None
    connection: Optional["VPNConnection"] = None
    reconnection: Optional["VPNConnection"] = None


class State(ABC):
    """
    This is the base state from which all other states derive from. Each new
    state has to implement the `on_event` method.

    Since these states are backend agnostic. When implement a new backend the
    person implementing it has to have special care in correctly translating
    the backend specific events to known events
    (see `proton.vpn.connection.events`).

    Each state acts on the `on_event` method. Generally, if a state receives
    an unexpected event, it will then not update the state but rather keep the
    same state and should log the occurrence.

    The general idea of state transitions:

        1) Connect happy path:      Disconnected -> Connecting -> Connected
        2) Connect with error path: Disconnected -> Connecting -> Error
        3) Disconnect happy path:   Connected -> Disconnecting -> Disconnected
        4) Active connection error path: Connected -> Error

    Certain states will have to call methods from the state machine
    (see `Disconnected`, `Connected`). Both of these states call
    `vpn_connection.start()` and `vpn_connection.stop()`.
    It should be noted that these methods should be run in an async way so that
    it does not block the execution of the next line.

    States also have `context` (which are fetched from events). These can help
    in discovering potential issues on why certain states might an unexpected
    behaviour. It is worth mentioning though that the contexts will always
    be backend specific.
    """
    type = None

    def __init__(self, context: StateContext = None):
        self.context = context or StateContext()

        if self.type is None:
            raise TypeError("Undefined attribute \"state\" ")

    def _assert_no_concurrent_connections(self, event: events.Event):
        not_up_event = not isinstance(event, events.Up)
        different_connection = event.context.connection is not self.context.connection
        if not_up_event and different_connection:
            # Any state should always receive events for the same connection, the only
            # exception being when the Up event is received. In this case, the Up event
            # always carries a new connection: the new connection to be initiated.
            raise ConcurrentConnectionsError(
                f"State {self} expected events from {self.context.connection} "
                f"but received an event from {event.context.connection} instead."
            )

    def on_event(self, event: events.Event) -> State:
        """Returns the new state based on the received event."""
        self._assert_no_concurrent_connections(event)

        new_state = self._on_event(event)

        if new_state is self:
            logger.warning(
                f"{self.type.name} state received unexpected "
                f"event: {type(event).__name__}",
                category="CONN", event="WARNING"
            )

        return new_state

    @abstractmethod
    def _on_event(
            self, event: events.Event
    ) -> State:
        """Given an event, it returns the new state."""

    def run_tasks(self) -> Optional[events.Event]:
        """Tasks to be run when this state instance becomes the current VPN state."""


class Disconnected(State):
    """
    Disconnected is the initial state of a connection. It's also its final
    state, except if the connection could not be established due to an error.
    """
    type = ConnectionStateEnum.DISCONNECTED

    def _on_event(self, event: events.Event):
        if isinstance(event, events.Up):
            return Connecting(StateContext(event=event, connection=event.context.connection))

        return self

    def run_tasks(self):
        if not self.context.connection:
            return None

        if self.context.reconnection:
            # When a reconnection is expected, an Up event is returned to start a new connection.
            # straight away.
            # IMPORTANT: in this case, the kill switch is **not** disabled.
            return events.Up(EventContext(connection=self.context.reconnection))

        def _on_ipv6_leak_protection_disabled(_future: Future):
            _future.result()

        # When the state machine is in disconnected state, a VPN connection
        # may have not been created yet.
        future = self.context.connection.disable_ipv6_leak_protection()
        future.add_done_callback(_on_ipv6_leak_protection_disabled)
        self.context.connection.remove_persistence()
        return None


class Connecting(State):
    """
    Connecting is the state reached when a VPN connection is requested.
    """
    type = ConnectionStateEnum.CONNECTING

    def _on_event(self, event: events.Event):
        if isinstance(event, events.Connected):
            return Connected(StateContext(event=event, connection=event.context.connection))

        if isinstance(event, events.Down):
            return Disconnecting(StateContext(event=event, connection=event.context.connection))

        if isinstance(event, events.Error):
            return Error(StateContext(event=event, connection=event.context.connection))

        if isinstance(event, events.Up):
            # If a new connection is requested while in `Connecting` state then
            # cancel the current one and pass the requested connection so that it's
            # started as soon as the current connection is down.
            return Disconnecting(
                StateContext(
                    event=event,
                    connection=self.context.connection,
                    reconnection=event.context.connection
                )
            )

        if isinstance(event, events.Disconnected):
            # Another process disconnected the VPN, otherwise the Disconnected
            # event would've been received by the Disconnecting state.
            return Disconnected(StateContext(event=event, connection=event.context.connection))

        return self

    def run_tasks(self):
        def _on_ipv6_leak_protection_enabled(_future: Future):
            _future.result()
            self.context.connection.start()

        future = self.context.connection.enable_ipv6_leak_protection()
        future.add_done_callback(_on_ipv6_leak_protection_enabled)


class Connected(State):
    """
    Connected is the state reached once the VPN connection has been successfully
    established.
    """
    type = ConnectionStateEnum.CONNECTED

    def _on_event(self, event: events.Event):
        if isinstance(event, events.Down):
            return Disconnecting(StateContext(event=event, connection=event.context.connection))

        if isinstance(event, events.Up):
            # If a new connection is requested while in `Connected` state then
            # cancel the current one and pass the requested connection so that it's
            # started as soon as the current connection is down.
            return Disconnecting(
                StateContext(
                    event=event,
                    connection=self.context.connection,
                    reconnection=event.context.connection
                )
            )

        if isinstance(event, events.Error):
            return Error(StateContext(event=event, connection=event.context.connection))

        if isinstance(event, events.Disconnected):
            # Another process disconnected the VPN, otherwise the Disconnected
            # event would've been received by the Disconnecting state.
            return Disconnected(StateContext(event=event, connection=event.context.connection))

        return self

    def run_tasks(self):
        self.context.connection.add_persistence()


class Disconnecting(State):
    """
    Disconnecting is state reached when VPN disconnection is requested.
    """
    type = ConnectionStateEnum.DISCONNECTING

    def _on_event(self, event: events.Event):
        if isinstance(event, events.Disconnected):
            return Disconnected(
                StateContext(
                    event=event,
                    connection=event.context.connection,
                    reconnection=self.context.reconnection
                )
            )

        if isinstance(event, events.Up):
            # If a new connection is requested while in the `Disconnecting` state then
            # store the requested connection in the state context so that it's started
            # as soon as the current connection is down.
            self.context.reconnection = event.context.connection

        return self

    def run_tasks(self):
        self.context.connection.stop()


class Error(State):
    """
    Error is the state reached after a connection error.
    """
    type = ConnectionStateEnum.ERROR

    def _on_event(self, event: events.Event):
        if isinstance(event, events.Down):
            return Disconnected(StateContext(event=event, connection=event.context.connection))

        if isinstance(event, events.Up):
            return Connecting(StateContext(event=event, connection=event.context.connection))

        return self

    def run_tasks(self):
        # Make sure connection resources are properly released.
        self.context.connection.stop()
