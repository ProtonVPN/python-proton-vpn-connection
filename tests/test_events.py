from unittest.mock import Mock

from proton.vpn.connection import events
from proton.vpn.connection.enum import StateMachineEventEnum
import pytest

from proton.vpn.connection.events import EventContext

context = EventContext(connection=Mock())


def test_base_class_missing_event():
    class DummyEvent(events.Event):
        pass

    with pytest.raises(AttributeError):
        DummyEvent(context)


def test_base_class_expected_event():
    custom_event = "test_event"

    class DummyEvent(events.Event):
        type = custom_event

    assert DummyEvent(context).type == custom_event


@pytest.mark.parametrize(
    "event_class, expected_event",
    [
        (events.Up.type, StateMachineEventEnum.UP),
        (events.Down.type, StateMachineEventEnum.DOWN),
        (events.Connected.type, StateMachineEventEnum.CONNECTED),
        (events.Disconnected.type, StateMachineEventEnum.DISCONNECTED),
        (events.Timeout.type, StateMachineEventEnum.TIMEOUT),
        (events.AuthDenied.type, StateMachineEventEnum.AUTH_DENIED),
        (events.UnexpectedError.type, StateMachineEventEnum.UNEXPECTED_ERROR),
    ]
)
def test_individual_events(event_class, expected_event):
    assert event_class == expected_event
