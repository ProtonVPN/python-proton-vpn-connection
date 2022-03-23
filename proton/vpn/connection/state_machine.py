from abc import abstractmethod

from .publisher import Publisher


class VPNStateMachine(Publisher):
    def __init__(self):
        super().__init__()
        self.__previous_state = None
        self.__current_state = None
        self._determine_initial_state()

    @property
    def status(self) -> "State":
        return self.__current_state

    def on_event(self, event) -> "None":
        self._update_connection_state(
            self.__current_state.on_event(event, self)
        )
        self._notify_subscribers(self.__current_state)

    def _update_connection_state(self, newstate) -> "None":
        self.__previous_state = self.__current_state
        self.__current_state = newstate

    @abstractmethod
    def _determine_initial_state(self) -> "None":
        # FIX-ME: Each backend should have it's
        # own implementation of determining initial state
        raise NotImplementedError

    @abstractmethod
    def _start_connection() -> "None":
        raise NotImplementedError

    @abstractmethod
    def _stop_connection() -> "None":
        raise NotImplementedError

    @abstractmethod
    def _add_persistence(self) -> "None":
        raise NotImplementedError

    @abstractmethod
    def _remove_persistence(self) -> "None":
        raise NotImplementedError
