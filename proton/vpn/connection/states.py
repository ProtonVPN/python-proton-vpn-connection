"""
The different VPN connection states and their transitions is defined here.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

from proton.vpn import logging
from proton.vpn.connection import events
from proton.vpn.connection.enum import ConnectionStateEnum

if TYPE_CHECKING:
    from proton.vpn.connection.state_machine import VPNStateMachine
    from proton.vpn.connection.vpnconnection import VPNConnection


# pylint: disable=too-few-public-methods


logger = logging.getLogger(__name__)


@dataclass
class StateContext:
    """
    Relevant state context data.

    Attributes:
        event: Event that led to the current state.
        connection: current VPN connection.
    """
    event: events.BaseEvent = None
    connection: "VPNConnection" = None


class BaseState:
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
    `state_machine.start_connection()` and `state_machine.stop_connection()`.
    It should be noted that these methods should be run in an async way so that
    it does not block the execution of the next line.

    States also have `context` (which are fetched from events). These can help
    in discovering potential issues on why certain states might an unexpected
    behaviour. It is worth mentioning though that the contexts will always
    be backend specific.
    """
    state = None

    def __init__(self, context=None):
        self.context = context or StateContext()
        if self.state is None:
            raise AttributeError("Undefined attribute \"state\" ")

    def on_event(self, event: events.BaseEvent, state_machine: "VPNStateMachine") -> BaseState:
        """Returns the new state based on the received event."""
        self.context.event = event
        self.context.connection = state_machine

        new_state = self._on_event(event, state_machine)

        if new_state is self:
            logger.warning(
                f"{self.state.name} state received unexpected "
                f"event: {type(event).__name__}",
                category="CONN", event="WARNING"
            )

        return new_state

    def _on_event(
            self, event: events.BaseEvent, state_machine: "VPNStateMachine"
    ):
        """To be implemented in the subclasses."""
        raise NotImplementedError(
            f"{type(self).__name__} does not implement the _on_event method.")

    def init(self, state_machine: "VPNStateMachine"):
        """Initialization tasks to be run just after a state change."""


class Disconnected(BaseState):
    """
    Disconnected is the initial state of a connection. It's also its final
    state, except if the connection could not be established due to an error.
    """
    state = ConnectionStateEnum.DISCONNECTED

    def _on_event(self, event: events.BaseEvent, state_machine: "VPNStateMachine"):
        if isinstance(event, events.Up):
            return Connecting(self.context)

        return self

    def init(self, state_machine: "VPNStateMachine"):
        state_machine.remove_persistence()


class Connecting(BaseState):
    """
    Connecting is the transitional state between Disconnected and Connected.
    """
    state = ConnectionStateEnum.CONNECTING

    def _on_event(self, event: events.BaseEvent, state_machine: "VPNStateMachine"):
        if isinstance(event, events.Connected):
            return Connected(self.context)

        if isinstance(event, events.Down):
            return Disconnecting(self.context)

        if isinstance(event, events.Disconnected):
            # Another process disconnected the VPN, otherwise the Disconnected
            # event would've been received by the Disconnecting state.
            return Disconnected(self.context)

        if isinstance(event, events.Error):
            return Error(self.context)

        return self

    def init(self, state_machine: "VPNStateMachine"):
        state_machine.start_connection()


class Connected(BaseState):
    """
    Connected is the state reached once the VPN connection has been successfully
    established.
    """
    state = ConnectionStateEnum.CONNECTED

    def _on_event(self, event: events.BaseEvent, state_machine: "VPNStateMachine"):
        if isinstance(event, events.Down):
            return Disconnecting(self.context)

        if isinstance(event, events.Disconnected):
            # Another process disconnected the VPN, otherwise the Disconnected
            # event would've been received by the Disconnecting state.
            return Disconnected(self.context)

        if isinstance(event, events.Error):
            return Error(self.context)

        return self

    def init(self, state_machine: "VPNStateMachine"):
        state_machine.add_persistence()


class Disconnecting(BaseState):
    """
    Disconnecting is the transitional state between Connected and Disconnected.
    """
    state = ConnectionStateEnum.DISCONNECTING

    def _on_event(self, event: events.BaseEvent, state_machine: "VPNStateMachine"):
        if isinstance(event, events.Disconnected):
            return Disconnected(self.context)

        return self

    def init(self, state_machine: "VPNStateMachine"):
        state_machine.stop_connection()


class Error(BaseState):
    """
    Error is the final state after a connection error.
    """
    state = ConnectionStateEnum.ERROR

    def _on_event(self, event: events.BaseEvent, state_machine: "VPNStateMachine"):
        return self

    def init(self, state_machine: "VPNStateMachine"):
        # Make sure connection resources are properly released.
        state_machine.stop_connection()
