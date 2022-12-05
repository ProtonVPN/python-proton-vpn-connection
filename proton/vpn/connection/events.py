"""
VPN connection events to react to.
"""
from .enum import StateMachineEventEnum


# pylint: disable=too-few-public-methods


class BaseEvent:
    """Skeleton event that all the other events should inherit from."""
    event = None

    def __init__(self, context=None):
        if self.event is None:
            raise AttributeError("event attribute not defined")

        self.__context = context

    @property
    def context(self) -> "StateContext":  # noqa
        """Returns the event's context."""
        return self.__context


class Up(BaseEvent):
    """Signals that the VPN connection should be started."""
    event = StateMachineEventEnum.UP


class Down(BaseEvent):
    """Signals that the VPN connection should be stopped."""
    event = StateMachineEventEnum.DOWN


class Connected(BaseEvent):
    """Signals that the VPN connection was successfully established."""
    event = StateMachineEventEnum.CONNECTED


class Disconnected(BaseEvent):
    """Signals that the VPN connection was successfully disconnected."""
    event = StateMachineEventEnum.DISCONNECTED


class Timeout(BaseEvent):
    """Signals that a timeout occurred while trying to establish the VPN
    connection."""
    event = StateMachineEventEnum.TIMEOUT


class AuthDenied(BaseEvent):
    """Signals that an authentication denied occurred while trying to establish
    the VPN connection."""
    event = StateMachineEventEnum.AUTH_DENIED


class TunnelSetupFail(BaseEvent):
    """Signals that there was an error setting up the VPN tunnel."""
    event = StateMachineEventEnum.TUNNEL_SETUP_FAIL


class Retry(BaseEvent):
    """Signals that a connection retry is required."""
    event = StateMachineEventEnum.RETRY


class UnknownError(BaseEvent):
    """Signals that an unexpected error occurred."""
    event = StateMachineEventEnum.UNKNOWN_ERROR
