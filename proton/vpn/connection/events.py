from .enum import StateMachineEventEnum


class BaseEvent:
    event = None

    def __init__(self, context=None):
        if self.event is None:
            raise AttributeError("event attribute not defined")

        self.__context = context

    @property
    def context(self):
        return self.__context


class Up(BaseEvent):
    event = StateMachineEventEnum.UP


class Down(BaseEvent):
    event = StateMachineEventEnum.DOWN


class Connected(BaseEvent):
    event = StateMachineEventEnum.CONNECTED


class Disconnected(BaseEvent):
    event = StateMachineEventEnum.DISCONNECTED


class Timeout(BaseEvent):
    event = StateMachineEventEnum.TIMEOUT


class AuthDenied(BaseEvent):
    event = StateMachineEventEnum.AUTH_DENIED


class TunnelSetupFail(BaseEvent):
    event = StateMachineEventEnum.TUNNEL_SETUP_FAIL


class Retry(BaseEvent):
    event = StateMachineEventEnum.RETRY


class UnknownError(BaseEvent):
    event = StateMachineEventEnum.UNKNOWN_ERROR
