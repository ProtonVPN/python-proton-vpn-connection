from abc import abstractmethod
from .enum import ConnectionStateEnum, StateMachineEventEnum
from .publisher import Publisher


class State:
    @abstractmethod
    def on_event(event, state_machine):
        raise NotImplementedError


class DisconnectedState(State):
    state = ConnectionStateEnum.DISCONNECTED

    def on_event(self, event, state_machine):
        if event == StateMachineEventEnum.UP:
            state_machine._start_connection()
            return ConnectingState()

        return self


class ConnectingState(State):
    state = ConnectionStateEnum.CONNECTING

    def on_event(self, event, state_machine):
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

    def on_event(self, event, state_machine):
        if event == StateMachineEventEnum.DOWN:
            state_machine._stop_connection()
            return DisconnectingState()
        if event == StateMachineEventEnum.TIMEOUT:
            return TransientState()
        elif event in [
            StateMachineEventEnum.AUTH_DENIED,
            StateMachineEventEnum.UNKOWN_ERROR
        ]:
            return ErrorState()

        return self


class DisconnectingState(State):
    state = ConnectionStateEnum.DISCONNECTING

    def on_event(self, event, state_machine):
        if event == StateMachineEventEnum.DISCONNECTED:
            return DisconnectedState()

        return self


class TransientState(State):
    state = ConnectionStateEnum.TRANSCIENT_ERROR

    def on_event(self, event, state_machine):
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

    def on_event(self, event, state_machine):
        state_machine._stop_connection()
        return DisconnectingState()


class VPNStateMachine(Publisher):

    def __init__(self):
        super().__init__()
        self.__previous_state = None
        self.__current_state = None
        self._determine_initial_state()

    @property
    def state(self):
        return self.__current_state.state

    def on_event(self, event):
        self.__previous_state = self.__current_state
        self.__current_state = self.__current_state.on_event(event, self)
        self._notify_subscribers(self.__current_state.state)

    def _determine_initial_state(self):
        # FIX-ME: Each backend has it's own implementation of determining this
        self.__current_state = DisconnectedState()

    @abstractmethod
    def _start_connection() -> None:
        raise NotImplementedError

    @abstractmethod
    def _stop_connection() -> None:
        raise NotImplementedError
