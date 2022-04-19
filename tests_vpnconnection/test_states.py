from proton.vpn.connection import states
from proton.vpn.connection import events
import pytest


class MockStateMachine:
    def start_connection(self):
        pass

    def stop_connection(self):
        pass

    def add_persistence(self):
        pass

    def remove_persistence(self):
        pass


def test_base_class_with_missing_state():
    class DummyState(states.BaseState):
        pass

    with pytest.raises(AttributeError):
        DummyState()


def test_base_class_with_expected_event():
    custom_state = "test_state"

    class DummyState(states.BaseState):
        state = custom_state

    assert DummyState().state == custom_state


def test_get_context():
    class DummyState(states.BaseState):
        state = "test_event"

    context = "test-context"
    s = DummyState(context)
    assert s.context == context


def test_on_not_implemented_event():
    class DummyState(states.BaseState):
        state = "test_event"

    with pytest.raises(NotImplementedError):
        DummyState().on_event(MockStateMachine())


@pytest.mark.parametrize(
    "state, event, expected_state",
    [
        (states.Disconnected(), events.Up(), states.Connecting),
        (states.Connecting(), events.Connected(), states.Connected),
        (states.Connecting(), events.Timeout(), states.Error),
        (states.Connecting(), events.AuthDenied(), states.Error),
        (states.Connecting(), events.UnknownError(), states.Error),
        (states.Connected(), events.Down(), states.Disconnecting),
        (states.Connected(), events.Timeout(), states.Transient),
        (states.Connected(), events.AuthDenied(), states.Error),
        (states.Connected(), events.UnknownError(), states.Error),
        (states.Disconnecting(), events.Disconnected(), states.Disconnected),
        (states.Transient(), events.Timeout(), states.Transient),
        (states.Transient(), events.Down(), states.Error),
        (states.Transient(), events.AuthDenied(), states.Error),
        (states.Transient(), events.UnknownError(), states.Error),
        (states.Error(), events.UnknownError(), states.Disconnecting)
    ]
)
def test_expected_state(state, event, expected_state):
    new_state = state.on_event(event, MockStateMachine())
    assert new_state.state == expected_state.state


@pytest.mark.parametrize(
    "state, event, expected_state",
    [
        (states.Disconnected(), events.Connected(), states.Disconnected),
        (states.Disconnected(), events.Timeout(), states.Disconnected),
        (states.Disconnected(), events.AuthDenied(), states.Disconnected),
        (states.Disconnected(), events.UnknownError(), states.Disconnected),
        (states.Disconnected(), events.Down(), states.Disconnected),
        (states.Disconnected(), events.Disconnected(), states.Disconnected),
        (states.Disconnected(), events.TunnelSetupFail(), states.Disconnected),
        (states.Disconnected(), events.Retry(), states.Disconnected),

        (states.Connecting(), events.Down(), states.Connecting),
        (states.Connecting(), events.Disconnected(), states.Error),
        (states.Connecting(), events.TunnelSetupFail(), states.Error),
        (states.Connecting(), events.Retry(), states.Connecting),
        (states.Connecting(), events.Up(), states.Connecting),

        (states.Connected(), events.Disconnected(), states.Connected),
        (states.Connected(), events.TunnelSetupFail(), states.Connected),
        (states.Connected(), events.Retry(), states.Connected),
        (states.Connected(), events.Up(), states.Connected),

        (states.Disconnecting(), events.Connected(), states.Disconnecting),
        (states.Disconnecting(), events.Timeout(), states.Disconnecting),
        (states.Disconnecting(), events.AuthDenied(), states.Disconnecting),
        (states.Disconnecting(), events.Disconnected(), states.Disconnected),
        (states.Disconnecting(), events.Down(), states.Disconnecting),
        (states.Disconnecting(), events.TunnelSetupFail(), states.Disconnecting),
        (states.Disconnecting(), events.Retry(), states.Disconnecting),

        (states.Transient(), events.Up(), states.Transient),
        (states.Transient(), events.Retry(), states.Transient),
        (states.Transient(), events.TunnelSetupFail(), states.Transient),
        (states.Transient(), events.Disconnected(), states.Transient),
        (states.Transient(), events.Connected(), states.Transient)
    ]
)
def test_expected_self_event_type(state, event, expected_state):
    new_state = state.on_event(event, MockStateMachine())
    assert new_state.state == expected_state.state


@pytest.mark.parametrize(
    "state, event",
    [
        (states.Disconnected(), None),
        (states.Disconnected(), True),
        (states.Disconnected(), "Test"),
        (states.Disconnected(), []),
        (states.Disconnected(), {}),
        (states.Connecting(), None),
        (states.Connecting(), True),
        (states.Connecting(), "Test"),
        (states.Connecting(), []),
        (states.Connecting(), {}),
        (states.Connected(), None),
        (states.Connected(), True),
        (states.Connected(), "Test"),
        (states.Connected(), []),
        (states.Connected(), {}),
        (states.Disconnecting(), None),
        (states.Disconnecting(), True),
        (states.Disconnecting(), "Test"),
        (states.Disconnecting(), []),
        (states.Disconnecting(), {}),
        (states.Transient(), None),
        (states.Transient(), True),
        (states.Transient(), "Test"),
        (states.Transient(), []),
        (states.Transient(), {})
    ]
)
def test_unexpected_event_type(state, event):
    with pytest.raises(AttributeError):
        state.on_event(event, MockStateMachine())