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
from unittest.mock import Mock, patch, AsyncMock

import pytest
from proton.vpn.killswitch.interface import KillSwitch

from proton.vpn.connection import events, states, Settings
from proton.vpn.connection.enum import KillSwitchSetting
from proton.vpn.connection.states import StateContext
from proton.vpn.connection.vpnconnector import VPNConnector


@pytest.fixture
def settings():
    settings = Mock(Settings)
    settings.killswitch = 0
    return settings


@pytest.fixture
def kill_switch():
    return Mock(KillSwitch)


@pytest.mark.asyncio
async def test_initialize_state_runs_tasks_for_initial_state(settings, kill_switch):
    initial_state = Mock()
    initial_state.run_tasks = AsyncMock(return_value=None)

    await VPNConnector(settings, kill_switch=kill_switch).initialize_state(initial_state)

    initial_state.run_tasks.assert_called_once()


@pytest.mark.asyncio
async def test_initialize_state_subscribes_to_connection_if_exists(settings, kill_switch):
    initial_state = Mock()
    initial_state.run_tasks = AsyncMock(return_value=None)

    await VPNConnector(
        settings, kill_switch=kill_switch
    ).initialize_state(initial_state)

    initial_state.context.connection.register.assert_called_once()


@pytest.mark.asyncio
@patch("proton.vpn.connection.vpnconnector.VPNConnection")
async def test_connect_creates_connection_and_sends_up_event_to_current_state(
        vpn_connection_mock, settings, kill_switch
):
    initial_state = Mock()
    next_state = Mock()
    initial_state.run_tasks = AsyncMock(return_value=None)
    initial_state.on_event.return_value = next_state
    # Mock that next_state does not auto generate new events
    next_state.run_tasks = AsyncMock(return_value=None)

    connector = VPNConnector(settings, state=initial_state, kill_switch=kill_switch)

    server = Mock()
    credentials = Mock()
    settings.kill_switch = KillSwitchSetting.OFF
    await connector.connect(server, credentials, settings, "protocol", "backend")

    vpn_connection_mock.create.assert_called_once_with(server, credentials, settings, "protocol", "backend")

    # Assert the generated Up event was processed and that it contained the newly created connection
    initial_state.on_event.assert_called_once()
    generated_event = initial_state.on_event.call_args.args[0]
    assert isinstance(generated_event, events.Up)
    assert generated_event.context.connection is vpn_connection_mock.create.return_value

    next_state.run_tasks.assert_called_once()


@pytest.mark.asyncio
async def test_disconnect_sends_down_event_to_current_state(settings, kill_switch):
    initial_state = Mock()
    next_state = Mock()
    initial_state.run_tasks = AsyncMock(return_value=None)
    initial_state.on_event.return_value = next_state
    # Mock that next_state does not auto generate new events
    next_state.run_tasks = AsyncMock(return_value=None)

    connector = VPNConnector(settings, state=initial_state, kill_switch=kill_switch)

    await connector.disconnect()

    initial_state.on_event.assert_called_once()
    generated_event = initial_state.on_event.call_args.args[0]
    assert isinstance(generated_event, events.Down)


@pytest.mark.asyncio
async def test_connector_unsubscribes_from_current_connection_when_connection_ends(
        settings, kill_switch
):
    initial_state = Mock()
    initial_state.run_tasks = AsyncMock(return_value=None)
    next_state = states.Disconnected(StateContext(connection=AsyncMock()))
    next_state.context.connection.unregister = Mock(return_value=None)
    initial_state.on_event = Mock(return_value=next_state)

    connector = VPNConnector(settings, kill_switch=kill_switch)
    await connector.initialize_state(initial_state)

    # Simulate connection event.
    initial_state.context.connection.register.assert_called_once()
    on_event_callback = initial_state.context.connection.register.call_args.args[0]
    print(on_event_callback)
    await on_event_callback(event=Mock())

    next_state.context.connection.unregister.assert_called_once_with(on_event_callback)


@pytest.mark.asyncio
async def test_connector_does_not_run_state_tasks_when_event_did_not_lead_to_a_state_transition(
        settings, kill_switch
):
    current_state = Mock()
    # Mock that events received by the current state do not lead to a state transition.
    current_state.on_event.return_value = current_state
    current_state.run_tasks = AsyncMock(return_value=None)

    connector = VPNConnector(settings, kill_switch=kill_switch)
    await connector.initialize_state(current_state)
    current_state.run_tasks.reset_mock()

    # Simulate connection event.
    current_state.context.connection.register.assert_called_once()
    on_event_callback = current_state.context.connection.register.call_args.args[0]
    await on_event_callback(Mock())

    # Assert that after the new event, since there was no state transition, the current
    # state tasks were not run again.
    current_state.run_tasks.assert_not_called()


@pytest.mark.asyncio
async def test_connector_sends_events_generated_when_running_state_tasks(
        settings, kill_switch
):
    initial_state = Mock()
    initial_state.run_tasks = AsyncMock(return_value=None)
    next_state = Mock()
    initial_state.on_event.return_value = next_state

    # Mock that next_state generates a new event when its tasks are run.
    generated_event = Mock()
    next_state.run_tasks = AsyncMock(return_value=generated_event)

    # Stop cascading events.
    next_next_state = Mock()
    next_state.on_event.return_value = next_next_state
    next_next_state.run_tasks = AsyncMock(return_value=None)

    await VPNConnector(
        settings, kill_switch=kill_switch
    ).initialize_state(initial_state)

    on_event_callback = initial_state.context.connection.register.call_args.args[0]

    # Simulate connection event.
    initial_event = Mock()
    await on_event_callback(initial_event)

    initial_state.on_event.assert_called_with(initial_event)
    next_state.on_event.assert_called_with(generated_event)


@pytest.mark.asyncio
@patch("proton.vpn.connection.vpnconnector.VPNConnection")
async def test_get_instance_returns_a_singleton_instance(VPNConnection, settings):
    VPNConnection.get_current_connection = AsyncMock(return_value=None)

    VPNConnector._instance = None  # Reset singleton instance.
    connector1 = await VPNConnector.get_instance(settings, kill_switch=AsyncMock())
    connector2 = await VPNConnector.get_instance(settings)
    assert connector1 is connector2


@pytest.mark.asyncio
@patch("proton.vpn.connection.vpnconnector.VPNConnection")
async def test_get_instance_initializes_state_to_initial_connection_state_if_a_connection_exists(
        VPNConnection, settings
):
    current_connection = Mock()
    current_connection.initial_state = states.Connected(states.StateContext(connection=current_connection))
    current_connection.add_persistence = AsyncMock(return_value=None)
    VPNConnection.get_current_connection = AsyncMock(return_value=current_connection)

    VPNConnector._instance = None  # Reset singleton instance.
    connector = await VPNConnector.get_instance(settings, kill_switch=AsyncMock())

    assert connector.current_state is current_connection.initial_state


@pytest.mark.asyncio
@patch("proton.vpn.connection.vpnconnector.VPNConnection")
async def test_get_instance_initializes_state_to_disconnected_if_a_connection_does_not_exist(
        VPNConnection, settings
):
    VPNConnection.get_current_connection = AsyncMock(return_value=None)

    VPNConnector._instance = None  # Reset singleton instance.
    connector = await VPNConnector.get_instance(settings, kill_switch=AsyncMock())

    assert isinstance(connector.current_state, states.Disconnected)
