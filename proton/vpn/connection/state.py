from proton.vpn.connection.enum import ConnectionStateEnum
from proton.vpn.connection import event
from abc import abstractmethod


class State:
    _state = None

    def __init__(self, context=None):
        self.__context = context
        try:
            if not self._state:
                raise AttributeError("state attribute not defined")
        except AttributeError:
            raise ArithmeticError("state attribute not defined")

    @property
    def state(self):
        return self._state

    @property
    def context(self):
        return self.__context

    @abstractmethod
    def on_event(e, state_machine):
        raise NotImplementedError


class DisconnectedState(State):
    _state = ConnectionStateEnum.DISCONNECTED

    def on_event(self, e, state_machine):
        if e.event == event.Up.event:
            state_machine._start_connection()
            return ConnectingState()
        else:
            # FIX-ME: unsure if only logs should be enough
            # or should do anything else
            pass
        return self


class ConnectingState(State):
    _state = ConnectionStateEnum.CONNECTING

    def on_event(self, e, state_machine):
        if e.event == event.Connected.event:
            return ConnectedState()
        elif e.event in [
            event.Timeout.event,
            event.AuthDenied.event,
            event.UnknownError.event
        ]:
            return ErrorState(e.context)
        else:
            # FIX-ME: unsure if only logs should be enough
            # or should do anything else
            pass

        return self


class ConnectedState(State):
    _state = ConnectionStateEnum.CONNECTED

    def on_event(self, e, state_machine):
        if e.event == event.Down.event:
            state_machine._stop_connection()
            return DisconnectingState(e.context)
        if e.event == event.Timeout.event:
            return TransientState(e.context)
        elif e.event in [
            event.AuthDenied.event.event,
            event.UnknownError.event.event
        ]:
            return ErrorState(e.context)
        else:
            # FIX-ME: unsure if only logs should be enough
            # or should do anything else
            pass

        return self


class DisconnectingState(State):
    _state = ConnectionStateEnum.DISCONNECTING

    def on_event(self, e, state_machine):
        if e.event == event.Disconnected.event:
            return DisconnectedState()
        else:
            # FIX-ME: unsure if only logs should be enough
            # or should do anything else
            pass

        return self


class TransientState(State):
    _state = ConnectionStateEnum.TRANSCIENT_ERROR

    def on_event(self, e, state_machine):
        if e.event == event.Timeout.event:
            # FIX ME: Attempt to reconnect
            pass
        elif e.event in [
            event.Down.event,
            event.AuthDenied.event,
            event.UnknownError.event,
        ]:
            return ErrorState(e.context)
        else:
            # FIX-ME: unsure if only logs should be enough
            # or should do anything else
            pass

        return self


class ErrorState(State):
    _state = ConnectionStateEnum.ERROR

    def on_event(self, e, state_machine):
        state_machine._stop_connection()
        return DisconnectingState()
