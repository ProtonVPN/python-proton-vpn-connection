from .publisher import Publisher


class VPNStateMachine(Publisher):
    """
    Each connection that derives from this class benefits from
    a clear way of handling events and updating connection
    states, with the added benefit of notifying its subscribers
    of state changes.

    Whenever a connection state changes, an event should always be
    dispatched via `on_event()` where an apropriate event from
    `proton.vpn.connection.events` is to be passed to the method. This
    in turn will update the internal state of the state machine while
    also emitting a notification for any subscribers about the state change.
    Internally the state machine will always store the previous state.

    The methods `determine_initial_state()`, `start_connection()`, `stop_connection()`,
    `add_persistence()`,`remove_persistence()` all raise `NotImplementedError` because
    these methods have to be implemented/overriden by the class that will derive
    from `VPNStateMachine`. Thus if you want to build your own connection/backend,
    you'll have to override these methods for the following reasons:

        `determine_initial_state()`: Whenever you launch the software,
            the state machine should have a way to determine its
            initial state. Once you've established which initial state
            the connection should be in, use the `update_connection_state()`
            to update the connection state.
        `start_connection()`/`stop_connection()`: Works mostly as a contract/interface
            for communication, as states are expecting these methods.
            Limitations: These methods have to always run in a async way, either via
            threads or any other method. Just be sure that they're not blocking the
            main thread, for a smooth experience.
        `add_persistence()`/`remove_persistence()`: Simillar to above, these also
            work mostly as contract/interface for ensuring connection persistance.
            Connection persistance is essential in cases when software can crash/restart
            and it needs to know which connection the state machine should act on. Though
            its up to the one implementing the backend/connection to ensure that this is
            working properly.
    """
    def __init__(self):
        super().__init__()
        self.__previous_state = None
        self.__current_state = None
        self.determine_initial_state()

    @property
    def status(self) -> "BaseState":
        """
        :return: the connection state
        :rtype: BaseState
        """
        return self.__current_state

    def on_event(self, event: "BaseEvent"):
        """
        Internally updates the state machine
        based on the event.

        A copy of the previous state is always stored internally
        in `self.__previous_state`
        """
        self.update_connection_state(
            self.__current_state.on_event(event, self)
        )
        self._notify_subscribers(self.__current_state)

    def update_connection_state(self, newstate: "BaseState"):
        """
        Replaces the `self.__previous_state` with the
        current value of `self.__current_state` and then replaces
        the value of the latter with `newstate`.
        """
        self.__previous_state = self.__current_state
        self.__current_state = newstate

    def determine_initial_state(self):
        raise NotImplementedError

    def start_connection(self):
        raise NotImplementedError

    def stop_connection(self):
        raise NotImplementedError

    def add_persistence(self):
        raise NotImplementedError

    def remove_persistence(self):
        raise NotImplementedError
