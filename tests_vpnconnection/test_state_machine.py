from proton.vpn.connection.state_machine import VPNStateMachine
from proton.vpn.connection import events
from proton.vpn.connection import states
import pytest
import enum
import time
from threading import Thread


class FlowTestCases(enum.IntEnum):
    DISCONNECTED_TO_CONNECTED = 0
    CONNECTED_TO_DISCONNECTED = 1
    DISCONNECTED_TO_ERROR = 2
    CONNECTED_TO_ERROR = 3


class DummyStateMachine(VPNStateMachine):
    def _determine_initial_state(self):
        self._update_connection_state(states.Disconnected())

    def _start_connection(self):
        self.on_event(events.Connected())

    def _stop_connection(self):
        self.on_event(events.Disconnected())

    def _add_persistence(self):
        pass

    def _remove_persistence(self):
        pass

    def _async_start(self):
        pass

    def _async_stop(self):
        pass


class DummyListenerClass:
    disconnected_to_connected_flow_states = [
        states.Connecting,
        states.Connected
    ]
    connected_to_disconnected_flow_states = [
        states.Disconnecting,
        states.Disconnected
    ]
    disconnected_to_error_flow_states = [
        states.Connecting,
        states.Error,
        states.Disconnecting,
        states.Disconnected
    ]
    connected_to_error_flow_states = [
        states.Error,
        states.Disconnecting,
        states.Disconnected
    ]
    test_flow = FlowTestCases.DISCONNECTED_TO_CONNECTED

    def status_update(self, status):
        try:
            if self._counter >= 0:
                self._counter += 1
        except AttributeError:
            self._counter = 0

        # print(
        #     """
        #     Counter: {}
        #     TestFlow: {}
        #     Expected State: {}
        #     Received State: {}\n
        #     """.format(
        #         self._counter,
        #         self.test_flow,
        #         self.connected_to_disconnected_flow_states[self._counter],
        #         status
        #     )
        # )

        if self.test_flow == FlowTestCases.DISCONNECTED_TO_CONNECTED:
            assert self.disconnected_to_connected_flow_states[
                self._counter
            ].state == status.state
        elif self.test_flow == FlowTestCases.CONNECTED_TO_DISCONNECTED:
            assert self.connected_to_disconnected_flow_states[
                self._counter
            ].state == status.state
        elif self.test_flow == FlowTestCases.DISCONNECTED_TO_ERROR:
            assert self.disconnected_to_error_flow_states[
                self._counter
            ].state == status.state
        elif self.test_flow == FlowTestCases.CONNECTED_TO_ERROR:
            assert self.connected_to_error_flow_states[
                self._counter
            ].state == status.state


@pytest.fixture
def dummy_state_machine():
    yield DummyStateMachine


@pytest.fixture
def dummy_listener_object():
    yield DummyListenerClass


def test_create_state_machine_without_overriding_initial_state_method():
    class MissingDetermineInitialState(VPNStateMachine):
        pass

    with pytest.raises(NotImplementedError):
        MissingDetermineInitialState()


def test_create_state_machine_without_overriding_other_methods():
    class MissingMethodsStateMachine(VPNStateMachine):
        def _determine_initial_state(self):
            self._update_connection_state(states.Disconnected())

    sm = MissingMethodsStateMachine()
    with pytest.raises(NotImplementedError):
        sm._start_connection()

    with pytest.raises(NotImplementedError):
        sm._stop_connection()

    with pytest.raises(NotImplementedError):
        sm._add_persistence()

    with pytest.raises(NotImplementedError):
        sm._remove_persistence()


def test_expected_initial_state(dummy_state_machine):
    sm = dummy_state_machine()
    assert sm.status.state == states.Disconnected().state


def test_unexpected_initial_state(dummy_state_machine):
    sm = dummy_state_machine()
    assert sm.status.state != states.Connected().state


def test_from_disconnected_to_connected(dummy_state_machine, dummy_listener_object):

    def _start_connection(self):
        thread = Thread(target=self._async_start)
        thread.start()

    def _async_start(self):
        time.sleep(0.2)
        self.on_event(events.Connected())

    dummy_state_machine._start_connection = _start_connection
    dummy_state_machine._async_start = _async_start
    sm = dummy_state_machine()
    lc = dummy_listener_object()
    sm.register(lc)
    sm.on_event(events.Up())

    while True:
        if sm.status.state == states.Connected.state:
            break


def test_from_disconnected_to_error(dummy_state_machine, dummy_listener_object):

    def _stop_connection(self):
        thread = Thread(target=self._async_stop)
        thread.start()

    def _async_stop(self):
        time.sleep(0.2)
        self.on_event(events.Disconnected())

    def _start_connection(self):
        thread = Thread(target=self._async_start)
        thread.start()

    def _async_start(self):
        time.sleep(0.2)
        self.on_event(events.AuthDenied())

    dummy_state_machine._stop_connection = _stop_connection
    dummy_state_machine._async_stop = _async_stop
    dummy_state_machine._start_connection = _start_connection
    dummy_state_machine._async_start = _async_start
    sm = dummy_state_machine()
    lc = dummy_listener_object()
    lc.test_flow = FlowTestCases.DISCONNECTED_TO_ERROR
    sm.register(lc)
    sm.on_event(events.Up())

    while True:
        if sm.status.state == states.Disconnected.state:
            break
        elif sm.status.state == states.Error.state:
            sm.on_event(events.Down())


def test_from_connected_to_disconnected(dummy_state_machine, dummy_listener_object):
    def _determine_initial_state(self):
        self._update_connection_state(states.Connected())

    def _stop_connection(self):
        thread = Thread(target=self._async_stop)
        thread.start()

    def _async_stop(self):
        time.sleep(0.2)
        self.on_event(events.Disconnected())

    dummy_state_machine._determine_initial_state = _determine_initial_state
    dummy_state_machine._stop_connection = _stop_connection
    dummy_state_machine._async_stop = _async_stop
    sm = dummy_state_machine()
    lc = dummy_listener_object()
    lc.test_flow = FlowTestCases.CONNECTED_TO_DISCONNECTED
    sm.register(lc)
    sm.on_event(events.Down())

    while True:
        if sm.status.state == states.Disconnected.state:
            break


def test_from_connected_to_error(dummy_state_machine, dummy_listener_object):
    def _determine_initial_state(self):
        self._update_connection_state(states.Connected())

    def _stop_connection(self):
        thread = Thread(target=self._async_stop)
        thread.start()

    def _async_stop(self):
        time.sleep(0.2)
        self.on_event(events.Disconnected())

    dummy_state_machine._determine_initial_state = _determine_initial_state
    dummy_state_machine._stop_connection = _stop_connection
    dummy_state_machine._async_stop = _async_stop
    sm = dummy_state_machine()
    lc = dummy_listener_object()
    lc.test_flow = FlowTestCases.CONNECTED_TO_ERROR
    sm.register(lc)
    sm.on_event(events.AuthDenied())

    while True:
        if sm.status.state == states.Disconnected.state:
            break
        elif sm.status.state == states.Error.state:
            sm.on_event(events.Down())
