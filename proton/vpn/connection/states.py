from proton.vpn.connection.enum import ConnectionStateEnum
from proton.vpn.connection import events


class BaseState:
    state = None

    def __init__(self, context=None):
        self.__context = context
        if self.state is None:
            raise AttributeError("state attribute not defined")

    @property
    def context(self):
        return self.__context

    def on_event(e: "events.BaseEvent", state_machine: "VPNStateMachine"):
        raise NotImplementedError


class Disconnected(BaseState):
    state = ConnectionStateEnum.DISCONNECTED

    def on_event(self, e: "events.BaseEvent", state_machine: "VPNStateMachine"):
        if e.event == events.Up.event:
            state_machine.start_connection()
            return Connecting()
        else:
            # FIX-ME: log
            pass

        return self


class Connecting(BaseState):
    state = ConnectionStateEnum.CONNECTING

    def on_event(self, e: "events.BaseEvent", state_machine: "VPNStateMachine"):
        if e.event == events.Connected.event:
            state_machine.add_persistence()
            return Connected()
        elif e.event in [
            events.Timeout.event,
            events.AuthDenied.event,
            events.UnknownError.event,
            events.TunnelSetupFail.event,
            events.Disconnected.event
        ]:
            return Error(e.context)
        else:
            # FIX-ME: log
            pass

        return self


class Connected(BaseState):
    state = ConnectionStateEnum.CONNECTED

    def on_event(self, e: "events.BaseEvent", state_machine: "VPNStateMachine"):
        if e.event == events.Down.event:
            state_machine.stop_connection()
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

    def on_event(self, e: "events.BaseEvent", state_machine: "VPNStateMachine"):
        if e.event in [
            events.Disconnected.event,
            events.UnknownError.event,
        ]:
            state_machine.remove_persistence()
            return Disconnected()
        else:
            # FIX-ME: log
            pass

        return self


class Transient(BaseState):
    state = ConnectionStateEnum.TRANSIENT_ERROR

    def on_event(self, e: "events.BaseEvent", state_machine: "VPNStateMachine"):
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

    def on_event(self, e: "events.BaseEvent", state_machine: "VPNStateMachine"):
        state_machine.stop_connection()
        return Disconnecting()
