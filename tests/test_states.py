from proton.vpn.connection import states
from proton.vpn.connection import events
import pytest
from unittest.mock import Mock


def test_raises_exception_when_missing_state():
    class DummyState(states.BaseState):
        pass

    with pytest.raises(AttributeError):
        DummyState()


def test_assert_does_not_raise_exception_when_state_is_set():
    custom_state = "test_state"

    class DummyState(states.BaseState):
        state = custom_state

    assert DummyState().state == custom_state


def test_assert_context_can_be_accessed():
    class DummyState(states.BaseState):
        state = "test_event"

    context = "test-context"
    s = DummyState(context)
    assert s.context == context


@pytest.mark.parametrize(
    "state, event, expected_state",
    [
        (states.Disconnected(), events.Up(), states.Connecting),
        (states.Connecting(), events.Connected(), states.Connected),
        (states.Connecting(), events.Timeout(), states.Error),
        (states.Connecting(), events.AuthDenied(), states.Error),
        (states.Connecting(), events.UnknownError(), states.Error),
        (states.Connected(), events.Down(), states.Disconnecting),
        (states.Connected(), events.AuthDenied(), states.Error),
        (states.Connected(), events.UnknownError(), states.Error),
        (states.Disconnecting(), events.Disconnected(), states.Disconnected),
        (states.Error(), events.UnknownError(), states.Error)
    ]
)
def test_assert_state_flow(state, event, expected_state):
    new_state = state.on_event(event, Mock())
    assert new_state.state == expected_state.state


@pytest.mark.parametrize(
    "state, event",
    [
        (states.Disconnected(), events.Connected()),
        (states.Disconnected(), events.Timeout()),
        (states.Disconnected(), events.AuthDenied()),

        (states.Disconnected(), events.UnknownError()),
        (states.Disconnected(), events.Down()),
        (states.Disconnected(), events.Disconnected()),

        (states.Disconnected(), events.TunnelSetupFail()),
        (states.Connecting(), events.Up()),
        (states.Connected(), events.Disconnected()),

        (states.Connected(), events.TunnelSetupFail(),),
        (states.Connected(), events.Up()),
        (states.Disconnecting(), events.Connected()),

        (states.Disconnecting(), events.Timeout()),
        (states.Disconnecting(), events.AuthDenied()),
        (states.Disconnecting(), events.Down()),
        (states.Disconnecting(), events.TunnelSetupFail()),
    ]
)
def test_expected_self_event_type(state, event, caplog):
    state.on_event(event, Mock())

    warnings = 0
    for record in caplog.records:
        if record.levelname == "WARNING":
            warnings += 1

    assert warnings == 1
