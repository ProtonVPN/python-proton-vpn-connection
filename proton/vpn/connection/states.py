from proton.vpn.connection.enum import ConnectionStateEnum
from proton.vpn.connection import events
from proton.vpn.connection.events import BaseEvent


class BaseState:
    """
    This is the base state from which all other states derive from. Each new
    state has to implement the `on_event` method.

    Since these states are backend agnostic. When implement a new backend the person
    implenting it has to have special care in correctly translating
    the backend specific events to known events (see `proton.vpn.connection.events`)

    Each state acts on the `on_event` method. Generally, if a state receives an unexpected
    event, it will then not update the state but rather keep the same state and should log the
    occurence.

    The general idea of state transitions:

        1) Connect succesfully path:       Disconnected -> Connecting -> Connected
        2) Connect with error path:        Disconnected -> Connecting -> Error -> Disconnecting -> Disconnected
        3) Disconnect succesfully path:    Connected -> Disconnecting -> Disconnected
        4) Connection error path:          Connected -> Error -> Disconnecting -> Disconnected

    There's also a 5th state transition, which is for transient errors (only when already connected):

        5*) Connected -> TransientError  ->  Connected
                                    \---->  Error -> Disconnecting -> Disconnected

    Certain states will have to call methods from the state machine (see `Disconnected`, `Connected`).
    Both of these states call `state_machine.start_connection()` and `state_machine.stop_connection()`. It should be
    noted that these methods should be run in a async way so that it does not block the execution of the next line.

    States also have `context` (which are fetched from events). These can help in discovering potential issues
    on why certain states might an unexpected behaviour. It is worth mentioning though that the contexts will always
    be backend specific.

    *This last state transition is as of yet not fully described.
    """
    state = None

    def __init__(self, context=None):
        self.__context = context
        if self.state is None:
            raise AttributeError("state attribute not defined")

    @property
    def context(self):
        return self.__context

    def on_event(e: "BaseEvent", state_machine: "VPNStateMachine"):
        raise NotImplementedError


class Disconnected(BaseState):
    """
    Disconnected is a final/initial state. It only acts on `Up` events,
    all other events are ignored.

    Path:
        |--------------|
        | Disconnected |-> Connecting -> Connected (initial state)
        |--------------|              |--------------|
        Connected -> Disconnecting -> | Disconnected | (final state)
            \--> Error -->/           |--------------|
    """
    state = ConnectionStateEnum.DISCONNECTED

    def on_event(self, e: "events.BaseEvent", state_machine: "VPNStateMachine"):
        if e.event == events.Up.event:
            state_machine.start_connection()
            return Connecting()
        else:
            # FIX-ME: log
            pass

        return self


class Connecting(BaseState):
    """
    Connecting is a transitioning state. Any other event then `Connected` either
    ends in `Error` state or is ignored.

    Path:
        |------------|
        | Connecting | -> Connected (transitioning state)
        |------------|
                \ --> Error
    """
    state = ConnectionStateEnum.CONNECTING

    def on_event(self, e: "BaseEvent", state_machine: "VPNStateMachine"):
        if e.event == events.Connected.event:
            state_machine.add_persistence()
            return Connected()
        elif e.event in [
            events.Timeout.event,
            events.AuthDenied.event,
            events.UnknownError.event,
            events.TunnelSetupFail.event,
            events.Disconnected.event
        ]:
            return Error(e.context)
        else:
            # FIX-ME: log
            pass

        return self


class Connected(BaseState):
    """
    Connected is a final/initial state (simillar to `Disconnected`).
    Any other event then `Down` or `Timeout` either
    ends in `Error` state or is ignored.

    Path:
                                      |-----------|
        Disconnected -> Connecting -> | Connected | (final state)
        |-----------|                 |-----------|
        | Connected | -> Disconnecting -> Disconnected (initial state)
        |-----------|      /
            \--> Error -->/
    """
    state = ConnectionStateEnum.CONNECTED

    def on_event(self, e: "BaseEvent", state_machine: "VPNStateMachine"):
        if e.event == events.Down.event:
            state_machine.stop_connection()
            return Disconnecting(e.context)
        if e.event == events.Timeout.event:
            return Transient(e.context)
        elif e.event in [
            events.AuthDenied.event,
            events.UnknownError.event
        ]:
            return Error(e.context)
        else:
            # FIX-ME: log
            pass

        return self


class Disconnecting(BaseState):
    """
    Disconnecting is a transitioning state. Any other event then `Disconnected`
    or `UnknownError` either end in `Error` state or are ignored.

    Path:
                    |---------------|
        Connected ->| Disconnecting |-> Disconnected (transitioning state)
           \        |---------------|
            \--> Error -->/
    """
    state = ConnectionStateEnum.DISCONNECTING

    def on_event(self, e: "BaseEvent", state_machine: "VPNStateMachine"):
        if e.event in [
            events.Disconnected.event,
            events.UnknownError.event,
        ]:
            state_machine.remove_persistence()
            return Disconnected()
        else:
            # FIX-ME: log
            pass

        return self


class Transient(BaseState):
    """
    Transient is a temporary (transitioning) error state.
    Usually this should only happen when the connection
    is already established and for some reason it temporarily drops.
    Ideally this state should attempt to restore the connection.

    FIX-ME: Not fully describred/implemented on how this should work.

    Path:
                    |-----------|
        Connected ->| Transient |-> Connected (transitioning state)
                    |-----------|
    """
    state = ConnectionStateEnum.TRANSIENT_ERROR

    def on_event(self, e: "BaseEvent", state_machine: "VPNStateMachine"):
        if e.event == events.Timeout.event:
            # FIX ME: Attempt to reconnect
            return self
        elif e.event in [
            events.Down.event,
            events.AuthDenied.event,
            events.UnknownError.event,
        ]:
            return Error(e.context)
        else:
            # FIX-ME: log
            pass

        return self


class Error(BaseState):
    """
    Error is a transitioning state. Any error that occurs during either
    establishing a connection or when already connected will always
    go through `Error` state, then to disconnecting (to ensure a smooth
    process) then disconnected. Thus all events that will land here will
    lead to `Disconnecting` state.

    Path:
      |--------|
      |  Error | -> Disconnecting -> Disconnected (transitioning state)
      |--------|
    """
    state = ConnectionStateEnum.ERROR

    def on_event(self, e: "BaseEvent", state_machine: "VPNStateMachine"):
        state_machine.stop_connection()
        return Disconnecting()
