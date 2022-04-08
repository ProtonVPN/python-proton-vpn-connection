from .publisher import Publisher


class VPNStateMachine(Publisher):
    """
    State Machine that updates it's internal states
    based on received events.
    """
    def __init__(self):
        super().__init__()
        self.__previous_state = None
        self.__current_state = None
        self.determine_initial_state()

    @property
    def status(self) -> "State":
        """
        :return: the connection state
        :rtype: State
        """
        return self.__current_state

    def on_event(self, event) -> "None":
        """
        This method internally updates the state machine
        based on the based events.

        A copy of the previous state is always stored internally
        in `self.__previous_state`
        """
        self.update_connection_state(
            self.__current_state.on_event(event, self)
        )
        self._notify_subscribers(self.__current_state)

    def update_connection_state(self, newstate) -> "None":
        self.__previous_state = self.__current_state
        self.__current_state = newstate

    def determine_initial_state(self) -> "None":
        raise NotImplementedError

    def start_connection(self) -> "None":
        raise NotImplementedError

    def stop_connection(self) -> "None":
        raise NotImplementedError

    def add_persistence(self) -> "None":
        raise NotImplementedError

    def remove_persistence(self) -> "None":
        raise NotImplementedError
