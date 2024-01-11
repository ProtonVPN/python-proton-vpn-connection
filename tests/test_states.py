"""
Copyright (c) 2023 Proton AG

This file is part of Proton VPN.

Proton VPN is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Proton VPN is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with ProtonVPN.  If not, see <https://www.gnu.org/licenses/>.
"""
from typing import Type
from unittest.mock import Mock, call, AsyncMock

import pytest

from proton.vpn.connection import states, events
from proton.vpn.connection.exceptions import ConcurrentConnectionsError
from proton.vpn.killswitch.interface import KillSwitchState


def test_state_subclass_raises_exception_when_missing_state():
    class DummyState(states.State):
        pass

    with pytest.raises(TypeError):
        DummyState(states.StateContext())


def test_state_on_event_logs_warning_when_event_did_not_cause_state_transition(caplog):
    class DummyState(states.State):
        type = Mock()

        def _on_event(self, event: events.Event) -> states.State:
            return self

    state = DummyState(states.StateContext())

    new_state = state.on_event(events.Up(events.EventContext(connection=Mock())))

    assert new_state is state
    warnings = [record for record in caplog.records if record.levelname == "WARNING"]
    assert len(warnings) == 1
    assert "state received unexpected event" in warnings[0].message


@pytest.mark.parametrize(
    "event_type, concurrent_connections_error_expected", [
        (event_type, event_type != events.Up) for event_type in events.EVENT_TYPES
    ]
)
def test_state_on_event_raises_concurrent_connections_error_when_multiple_connections_are_detected(
        event_type, concurrent_connections_error_expected
):
    """
    All state instance raise an exception if they receive an event carrying a connection that's not
    the same as the one the state instance already has on its context. The reason for this is that
    the current state should be receiving state updates from the same connection that led to this
    state.

    The exception to this rule is the Up event, since the goal of the Up event is to start a new
    connection.
    """
    # In this case, the concrete state instance doesn't matter, since this check is done in
    # the base State class.
    state = states.Connected(states.StateContext(connection=Mock()))
    event = event_type(events.EventContext(connection=Mock()))

    try:
        state.on_event(event)
        error_raised = False
    except ConcurrentConnectionsError:
        error_raised = True

    assert error_raised is concurrent_connections_error_expected


def assert_state_transition(
        state_type: Type[states.State],
        event_type: Type[events.Event],
        expected_next_state_type: Type[states.State]
):
    """Asserts that when calling the `on_event` method on an instance of `state_type` passing it
    an instance of `event_type` then the result is an instance of `expected_next_state_type`."""
    connection = Mock()
    state = state_type(states.StateContext(connection=connection))
    event = event_type(events.EventContext(connection=connection))

    next_state = state.on_event(event)

    assert isinstance(next_state, expected_next_state_type)

    if next_state is not state:
        # The new state should keep the event that led to it in its context.
        assert next_state.context.event is event


@pytest.mark.parametrize("state_type, event_type, expected_next_state_type", [
    (states.Disconnected, events.Up, states.Connecting),
    (states.Connecting, events.Connected, states.Connected),
    (states.Connected, events.Down, states.Disconnecting),
    (states.Disconnecting, events.Disconnected, states.Disconnected)
])
def test_happy_flow_state_transitions(state_type, event_type, expected_next_state_type):
    """
    {DISCONNECTED} --Up--> {CONNECTING} --Connected--> {CONNECTED}
    --Down--> {DISCONNECTING} --Disconnected--> {DISCONNECTED}
    """
    assert_state_transition(state_type, event_type, expected_next_state_type)


@pytest.mark.parametrize("event_type, expected_next_state_type", [
    (events.Up, states.Connecting),
    (events.Down, states.Disconnected),
    (events.Disconnected, states.Disconnected),
    (events.Connected, states. Disconnected),  # Invalid event.
    (events.UnexpectedError, states.Disconnected)  # Invalid event.
])
def test_disconnected_on_event_transitions(event_type, expected_next_state_type):
    assert_state_transition(states.Disconnected, event_type, expected_next_state_type)


@pytest.mark.parametrize("event_type, expected_next_state_type", [
    (events.Connected, states.Connected),
    (events.Down, states.Disconnecting),
    (events.UnexpectedError, states.Error),
    (events.Up, states.Disconnecting),  # Reconnection.
    (events.Disconnected, states.Disconnected)
])
def test_connecting_on_event_transitions(event_type, expected_next_state_type):
    assert_state_transition(states.Connecting, event_type, expected_next_state_type)


@pytest.mark.parametrize("event_type, expected_next_state_type", [
    (events.Down, states.Disconnecting),
    (events.Up, states.Disconnecting),  # Reconnection.
    (events.UnexpectedError, states.Error),
    (events.Disconnected, states.Disconnected),
    (events.Connected, states.Connected)
])
def test_connected_on_event_transitions(event_type, expected_next_state_type):
    assert_state_transition(states.Connected, event_type, expected_next_state_type)


@pytest.mark.parametrize("event_type, expected_next_state_type", [
    (events.Disconnected, states.Disconnected),
    (events.Up, states.Disconnecting),  # Reconnection.
    (events.Down, states.Disconnecting),
    (events.UnexpectedError, states.Disconnected),  # Errors events also signal VPN disconnection
    (events.Connected, states.Disconnecting)  # Invalid event.
])
def test_disconnecting_on_event_transitions(event_type, expected_next_state_type):
    assert_state_transition(states.Disconnecting, event_type, expected_next_state_type)


@pytest.mark.parametrize("event_type, expected_next_state_type", [
    (events.Down, states.Disconnected),
    (events.Up, states.Connecting),
    (events.UnexpectedError, states.Error),
    (events.Connected, states.Error),  # Invalid event.
    (events.Disconnected, states.Error)  # Invalid event.
])
def test_error_on_event_transitions(event_type, expected_next_state_type):
    assert_state_transition(states.Error, event_type, expected_next_state_type)


@pytest.mark.parametrize("active_state_type", [
    states.Connecting, states.Connected, states.Disconnecting
])
def test_reconnection_is_triggered_when_up_event_is_received_while_a_connection_is_active(
        active_state_type
):
    """
    A connection is active while in Connecting, Connected and Disconnecting
    states. When one of these states receives an Up event then a reconnection
    will be triggered. That means that, the current state will transition to
    Disconnecting state (to start disconnection) while keeping the new connection
    to be started (carried by the Up event) once the Disconnected state is reached.
    """
    active_state = active_state_type(states.StateContext(connection=Mock()))
    up = events.Up(events.EventContext(connection=Mock()))

    disconnecting = active_state.on_event(up)

    assert isinstance(disconnecting, states.Disconnecting)
    # The connection to disconnect from is the same we were connecting to.
    assert disconnecting.context.connection is active_state.context.connection
    # The connection that we want to reconnect to is the one carried by the up event.
    assert disconnecting.context.reconnection is up.context.connection


@pytest.mark.asyncio
async def test_disconnected_run_tasks_when_reconnection_is_not_requested():
    """
    The disconnected state should run the following tasks when reconnection is **not** requested:
     - Disable IPv6 leak protection.
     - Remove persisted connection parameters.
    """
    connection = Mock()
    connection.disable_ipv6_leak_protection = AsyncMock(return_value=None)
    connection.disable_killswitch = AsyncMock(return_value=None)
    connection.remove_persistence = AsyncMock(return_value=None)

    disconnected = states.Disconnected(states.StateContext(connection=connection))
    generated_event = await disconnected.run_tasks()

    connection_calls = connection.method_calls
    assert len(connection_calls) == 3
    assert connection_calls[0] == call.disable_ipv6_leak_protection()
    assert connection_calls[1] == call.disable_killswitch()
    assert connection_calls[2] == call.remove_persistence()
    assert generated_event is None


@pytest.mark.asyncio
async def test_disconnected_run_tasks_when_reconnection_is_requested_and_should_return_up_event():
    """
    When reconnection **is** requested while on the disconnected state then:
     - No connection tasks should be performed. It's very important that
       IPv6 leak protection or the kill switch are **not** disabled.
     - An Up event should be returned with the new connection to be started.
    """
    connection = Mock()
    reconnection = Mock()
    disconnected = states.Disconnected(states.StateContext(connection=connection, reconnection=reconnection))

    generated_event = await disconnected.run_tasks()

    assert len(connection.method_calls) == 0
    assert isinstance(generated_event, events.Up)
    assert generated_event.context.connection is reconnection


@pytest.mark.asyncio
async def test_disconnected_run_tasks_does_nothing_if_there_is_no_connection():
    """When there is no current connection, the disconnected state doesn't have any tasks to run."""
    disconnected = states.Disconnected(states.StateContext(connection=None))
    event = await disconnected.run_tasks()
    assert event is None


@pytest.mark.asyncio
@pytest.mark.parametrize("killswitch_state", [KillSwitchState.ON.value, KillSwitchState.OFF.value])
async def test_connecting_run_tasks(killswitch_state):
    """
    The connecting state tasks are the following ones, in the specified order:

     1. Enable IPv6 leak protection.
     2. Enable kill switch if it's set to be enabled.
     3. Start the connection.

    It's very important that IPv6 leak protection (and kill switch) is enabled
    before starting the connection.
    """
    connection = Mock()

    connection.enable_ipv6_leak_protection = AsyncMock(return_value=None)
    connection.enable_killswitch = AsyncMock(return_value=None)
    connection.start = AsyncMock(return_value=None)
    type(connection).killswitch = killswitch_state

    connecting = states.Connecting(states.StateContext(connection=connection))

    await connecting.run_tasks()

    connection_calls = connection.method_calls
    if killswitch_state == KillSwitchState.ON.value:
        assert len(connection_calls) == 3
        assert connection_calls[0] == call.enable_ipv6_leak_protection
        assert connection_calls[1] == call.enable_killswitch(connection)
        assert connection_calls[2] == call.start
    else:
        assert len(connection_calls) == 2
        assert connection_calls[0] == call.enable_ipv6_leak_protection
        assert connection_calls[1] == call.start


@pytest.mark.asyncio
@pytest.mark.parametrize("killswitch_state", [KillSwitchState.ON.value, KillSwitchState.OFF.value])
async def test_connected_run_tasks_add_persistence(killswitch_state):
    """The tasks to be run while on the connected state is to persist the connection parameters and 
    enable kill switch if it's set to be enabled."""
    connection = Mock()
    connected = states.Connected(states.StateContext(connection=connection))

    connection.enable_killswitch = AsyncMock(return_value=None)
    connection.add_persistence = AsyncMock(return_value=None)
    type(connection).killswitch = killswitch_state

    await connected.run_tasks()

    connection_calls = connection.method_calls

    if killswitch_state == KillSwitchState.ON.value:
        assert len(connection_calls) == 2
        assert connection_calls[0] == call.enable_killswitch
        assert connection_calls[1] == call.add_persistence
    else:
        assert len(connection_calls) == 1
        assert connection_calls[0] == call.add_persistence


@pytest.mark.asyncio
async def test_disconnecting_run_tasks_stops_connection():
    """The only task be run while on the disconnecting state is to stop the connection."""
    connection = Mock()
    connection.stop = AsyncMock(return_value=None)
    disconnecting = states.Disconnecting(states.StateContext(connection=connection))

    await disconnecting.run_tasks()

    connection_calls = connection.method_calls
    assert len(connection_calls) == 1
    connection_calls[0].method = connection.stop


@pytest.mark.asyncio
async def test_error_run_tasks_stops_connection():
    """
    The only task to be run while on the error state is to stop the connection.
    The reason for doing so is to release any resources the connection is holding onto.
    """
    connection = Mock()
    connection.stop = AsyncMock(return_value=None)
    connecting = states.Error(states.StateContext(connection=connection))

    await connecting.run_tasks()

    connection_calls = connection.method_calls
    assert len(connection_calls) == 1
    connection_calls[0].method = connection.stop
