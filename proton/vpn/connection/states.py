"""
The different VPN connection states and their transitions is defined here.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from proton.vpn import logging
from proton.vpn.connection import events
from proton.vpn.connection.enum import ConnectionStateEnum
from proton.vpn.connection.events import BaseEvent

if TYPE_CHECKING:
    from proton.vpn.connection.state_machine import VPNStateMachine
    from proton.vpn.connection.vpnconnection import VPNConnection


logger = logging.getLogger(__name__)


@dataclass
class StateContext:
    """Relevant state context data."""
    event: BaseEvent = None  # event that led to the current state
    connection: "VPNConnection" = None  # current VPN connection


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
    It should be noted that these methods should be run in a async way so that
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

    # pylint: disable=unused-argument
    def on_event(self, event: "BaseEvent", state_machine: "VPNStateMachine"):
        """Returns the new state based on the received event."""
        return self

    def init(self, state_machine: "VPNStateMachine"):
        """Initializes the current state."""


class Disconnected(BaseState):
    r"""
    Disconnected is a final/initial state. It only acts on `Up` events,
    all other events are ignored.

    Path:
        |--------------|
        | Disconnected |-> Connecting -> Connected
        |--------------|             |--------------|
        Connected -> Disconnected -> | Disconnected |
            \                        |--------------|
             \-----------> Error
    """
    state = ConnectionStateEnum.DISCONNECTED

    def on_event(self, event: BaseEvent, state_machine: "VPNStateMachine"):

        if event.event == events.Up.event:
            state_machine.start_connection()
            self.context.connection = state_machine
            self.context.event = event
            return Connecting(self.context)

        logger.warning(
            f"{self.state.name} state received unexpected "
            f"event: {event.event.name}",
            category="CONN", event="WARNING"
        )

        return self


class Connecting(BaseState):
    r"""
    Connecting is a transitioning state. Any other event then `Connected` either
    ends in `Error` state or is ignored.

    Path:
        |------------|
        | Connecting | -> Connected -> Disconnected
        |------------|
                \--------> Error
    """
    state = ConnectionStateEnum.CONNECTING

    def on_event(self, event: BaseEvent, state_machine: "VPNStateMachine"):
        self.context.event = event
        if event.event == events.Connected.event:
            state_machine.add_persistence()
            return Connected(self.context)

        if event.event == events.Down.event:
            state_machine.stop_connection()
            return Disconnecting(self.context)

        if event.event in [
            events.Timeout.event,
            events.AuthDenied.event,
            events.UnknownError.event,
            events.TunnelSetupFail.event,
            events.Disconnected.event
        ]:
            return Error(self.context)

        logger.warning(
            f"{self.state.name} state received unexpected "
            f"event: {event.event.name}",
            category="CONN", event="WARNING"
        )

        return self


class Connected(BaseState):
    r"""
    Connected is a final/initial state (simillar to `Disconnected`).
    Any other event then `Down` or `Timeout` either
    ends in `Error` state or is ignored.

    Path:
                                      |-----------|
        Disconnected -> Connecting -> | Connected |
        |-----------|                 |-----------|
        | Connected | -> Disconnecting -> Disconnected
        |-----------|
            \-----------> Error
    """
    state = ConnectionStateEnum.CONNECTED

    def on_event(self, event: BaseEvent, state_machine: "VPNStateMachine"):
        self.context.event = event
        if event.event == events.Down.event:
            state_machine.stop_connection()
            return Disconnecting(self.context)

        if event.event in [
            events.Timeout.event,
            events.AuthDenied.event,
            events.UnknownError.event
        ]:
            return Error(self.context)

        logger.warning(
            f"{self.state.name} state received unexpected "
            f"event: {event.event.name}",
            category="CONN", event="WARNING"
        )

        return self


class Disconnecting(BaseState):
    r"""
    Disconnecting is a transitioning state. Any other event then `Disconnected`
    or `UnknownError` either end in `Error` state or are ignored.

    Path:
                    |---------------|
        Connected ->| Disconnecting |-> Disconnected
           \        |---------------|
            \----------> Error
    """
    state = ConnectionStateEnum.DISCONNECTING

    def on_event(self, event: BaseEvent, state_machine: "VPNStateMachine"):
        self.context.event = event
        if event.event in [
            events.Disconnected.event,
            events.UnknownError.event,
        ]:
            state_machine.remove_persistence()
            return Disconnected(self.context)

        logger.warning(
            f"{self.state.name} state received unexpected "
            f"event: {event.event.name}",
            category="CONN", event="WARNING"
        )

        return self


class Error(BaseState):
    r"""
    Error is a transitioning state. Any error that occurs during either
    establishing a connection or when already connected will always
    go through `Error` state, then to disconnecting (to ensure a smooth
    process) then disconnected. Thus all events that will land here will
    lead to `Disconnecting` state.

    Path:
    Connecting ---> |-------|
                    | Error |
    Connected ----> |-------|
    """
    state = ConnectionStateEnum.ERROR

    def init(self, state_machine):
        state_machine.stop_connection()
        state_machine.remove_persistence()

    def on_event(self, event: BaseEvent, state_machine: "VPNStateMachine"):
        logger.warning(
            f"{self.state.name} state received unexpected "
            f"event: {event.event.name}",
            category="CONN", event="WARNING"
        )
        return self
