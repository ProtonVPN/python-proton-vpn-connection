from .enum import StateMachineEventEnum


class Event:
    _event = None

    def __init__(self, context=None):
        if not self._event:
            raise AttributeError("event attribute not defined")

        self.__context = context

    @classmethod
    def event(cls):
        return cls._event

    @property
    def context(self):
        return self.__context


class Up(Event):
    _event = StateMachineEventEnum.UP


class Down(Event):
    _event = StateMachineEventEnum.DOWN


class Connected(Event):
    _event = StateMachineEventEnum.CONNECTED


class Disconnected(Event):
    _event = StateMachineEventEnum.DISCONNECTED


class Timeout(Event):
    _event = StateMachineEventEnum.TIMEOUT


class AuthDenied(Event):
    _event = StateMachineEventEnum.AUTH_DENIED


class TunnelSetupFail(Event):
    _event = StateMachineEventEnum.TUNNEL_SETUP_FAIL


class Retry(Event):
    _event = StateMachineEventEnum.RETRY


class UnknownError(Event):
    _event = StateMachineEventEnum.UNKOWN_ERROR
