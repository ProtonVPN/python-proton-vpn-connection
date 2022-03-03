from abc import abstractmethod
from .enum import ConnectionStateEnum, StateMachineEventEnum


class State:
    @abstractmethod
    def on_event(self, event):
        raise NotImplementedError


class DisconnectedState(State):
    state = ConnectionStateEnum.DISCONNECTED

    def on_event(self, event):
        if event == StateMachineEventEnum.UP:
            return ConnectingState()

        return self


class ConnectingState(State):
    state = ConnectionStateEnum.CONNECTING

    def on_event(self, event):
        if event == StateMachineEventEnum.CONNECTED:
            return ConnectedState()
        elif event in [
            StateMachineEventEnum.TIMEOUT,
            StateMachineEventEnum.AUTH_DENIED,
            event == StateMachineEventEnum.UNKOWN_ERROR
        ]:
            return ErrorState()

        return self


class ConnectedState(State):
    state = ConnectionStateEnum.CONNECTED

    def on_event(self, event):
        if event == StateMachineEventEnum.DOWN:
            return DisconnectingState()
        if event == StateMachineEventEnum.TIMEOUT:
            return TranscientState()
        elif event in [
            StateMachineEventEnum.AUTH_DENIED,
            StateMachineEventEnum.UNKOWN_ERROR
        ]:
            return ErrorState()

        return self


class DisconnectingState(State):
    state = ConnectionStateEnum.DISCONNECTING

    def on_event(self, event):
        if event == StateMachineEventEnum.DISCONNECTED:
            return DisconnectedState()

        return self


class TranscientState(State):
    state = ConnectionStateEnum.TRANSCIENT_ERROR

    def on_event(self, event):
        if event == StateMachineEventEnum.TIMEOUT:
            # FIX ME: Attempt to reconnect
            pass
        elif event in [
            StateMachineEventEnum.DOWN,
            StateMachineEventEnum.AUTH_DENIED,
            StateMachineEventEnum.UNKOWN_ERROR
        ]:
            return ErrorState()

        return self


class ErrorState(State):
    state = ConnectionStateEnum.ERROR

    def on_event(self, event):
        return DisconnectingState()


class VPNStateMachine:

    def __init__(self):
        self.__previous_state = None
        self.__current_state = None
        self.__determine_initial_state()

    @property
    def state(self):
        self.__current_state.state

    def on_event(self, event):
        self.__previous_state = self.__current_state
        self.__current_state = self.__current_state.on_event(event)

    def __determine_initial_state(self):
        self.__current_state = DisconnectedState()
