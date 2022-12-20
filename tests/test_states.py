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
        (states.Connecting(), events.Down(), states.Disconnecting),
        (states.Connecting(), events.Disconnected(), states.Disconnected),
        (states.Connecting(), events.Timeout(), states.Error),
        (states.Connecting(), events.AuthDenied(), states.Error),
        (states.Connecting(), events.TunnelSetupFailed(), states.Error),
        (states.Connecting(), events.UnexpectedError(), states.Error),
        (states.Connected(), events.Down(), states.Disconnecting),
        (states.Connected(), events.Disconnected(), states.Disconnected),
        (states.Connected(), events.Timeout(), states.Error),
        (states.Connected(), events.AuthDenied(), states.Error),
        (states.Connected(), events.UnexpectedError(), states.Error),
        (states.Connected(), events.DeviceDisconnected(), states.Error),
        (states.Disconnecting(), events.Disconnected(), states.Disconnected),
    ]
)
def test_assert_state_flow(state, event, expected_state):
    new_state = state.on_event(event, Mock())
    assert new_state.state == expected_state.state


@pytest.mark.parametrize(
    "state_class, expected_event_types",
    [
        (states.Disconnected, {
            events.Up, events.TunnelSetupFailed
        }),
        (states.Connecting, {
            events.Connected, events.Down, events.Disconnected, events.Error
        }),
        (states.Connected, {
            events.Down, events.Disconnected, events.Error
        }),
        (states.Disconnecting, {
            events.Disconnected
        })
    ]
)
def test_on_event_returns_same_state_on_unexpected_event_types(
        state_class, expected_event_types, caplog
):
    unexpected_events = [
        event_type for event_type in events.EVENT_TYPES
        if not issubclass(event_type, tuple(expected_event_types))
    ]
    state = state_class()

    for event_type in unexpected_events:
        next_state = state.on_event(event_type(), Mock())

        assert next_state is state, \
            f"{state_class.__name__} state was not expected to transition " \
            f"to {type(next_state).__name__} on event {event_type.__name__}."
        warnings = [record for record in caplog.records if record.levelname == 'WARNING']
        assert len(warnings) == 1, "One warning was expected but the " \
                                   "following where found: " \
                                   f"{[record.message for record in warnings]}"

        caplog.clear()
