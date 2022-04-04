from proton.vpn.connection.enum import ConnectionStateEnum
from proton.vpn.connection import events
from abc import abstractmethod


def ensure_event_has_necessary_properties(func):
    def inner(self, e, state_machine):
        _e = e
        if not hasattr(e, "event"):
            _e = events.BaseEvent

        return func(self, _e, state_machine)

    return inner


class BaseState:
    state = None

    def __init__(self, context=None):
        self.__context = context
        if self.state is None:
            raise AttributeError("state attribute not defined")

    @property
    def context(self):
        return self.__context

    @abstractmethod
    def on_event(e, state_machine):
        raise NotImplementedError


class Disconnected(BaseState):
    state = ConnectionStateEnum.DISCONNECTED

    @ensure_event_has_necessary_properties
    def on_event(self, e, state_machine):
        if e.event == events.Up.event:
            state_machine._start_connection()
            return Connecting()
        else:
            # FIX-ME: log
            pass

        return self


class Connecting(BaseState):
    state = ConnectionStateEnum.CONNECTING

    @ensure_event_has_necessary_properties
    def on_event(self, e, state_machine):
        if e.event == events.Connected.event:
            state_machine._add_persistence()
            return Connected()
        elif e.event in [
            events.Timeout.event,
            events.AuthDenied.event,
            events.UnknownError.event
        ]:
            return Error(e.context)
        else:
            # FIX-ME: log
            pass

        return self


class Connected(BaseState):
    state = ConnectionStateEnum.CONNECTED

    @ensure_event_has_necessary_properties
    def on_event(self, e, state_machine):
        if e.event == events.Down.event:
            state_machine._stop_connection()
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
    state = ConnectionStateEnum.DISCONNECTING

    @ensure_event_has_necessary_properties
    def on_event(self, e, state_machine):
        if e.event == events.Disconnected.event:
            state_machine._remove_persistence()
            return Disconnected()
        else:
            # FIX-ME: log
            pass

        return self


class Transient(BaseState):
    state = ConnectionStateEnum.TRANSCIENT_ERROR

    @ensure_event_has_necessary_properties
    def on_event(self, e, state_machine):
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
    state = ConnectionStateEnum.ERROR

    def on_event(self, e, state_machine):
        state_machine._stop_connection()
        return Disconnecting()
