from proton.vpn.connection import events
from proton.vpn.connection.enum import StateMachineEventEnum
import pytest


def test_base_class_missing_event():
    class DummyEvent(events.BaseEvent):
        pass

    with pytest.raises(AttributeError):
        DummyEvent()


def test_base_class_expected_event():
    custom_event = "test_event"

    class DummyEvent(events.BaseEvent):
        event = custom_event

    assert DummyEvent().event == custom_event


def test_get_context():
    class DummyEvent(events.BaseEvent):
        event = "test_event"

    context = "test-context"
    event = DummyEvent(context)
    assert event.context == context


@pytest.mark.parametrize(
    "event_class, expected_event",
    [
        (events.Up().event, StateMachineEventEnum.UP),
        (events.Down().event, StateMachineEventEnum.DOWN),
        (events.Connected().event, StateMachineEventEnum.CONNECTED),
        (events.Disconnected().event, StateMachineEventEnum.DISCONNECTED),
        (events.Timeout().event, StateMachineEventEnum.TIMEOUT),
        (events.AuthDenied().event, StateMachineEventEnum.AUTH_DENIED),
        (events.Retry().event, StateMachineEventEnum.RETRY),
        (events.UnexpectedError().event, StateMachineEventEnum.UNEXPECTED_ERROR),
    ]
)
def test_individual_events(event_class, expected_event):
    assert event_class == expected_event
