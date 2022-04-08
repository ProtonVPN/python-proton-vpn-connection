from proton.vpn.connection.state_machine import VPNStateMachine
from proton.vpn.connection import events
from proton.vpn.connection import states
import pytest
import enum
import time
from threading import Thread

TIMEOUT_LIMIT = 10


class FlowTestCases(enum.IntEnum):
    DISCONNECTED_TO_CONNECTED = 0
    CONNECTED_TO_DISCONNECTED = 1
    DISCONNECTED_TO_ERROR = 2
    CONNECTED_TO_ERROR = 3


class DummyStateMachine(VPNStateMachine):
    def determine_initial_state(self):
        self.update_connection_state(states.Disconnected())

    def start_connection(self):
        self.on_event(events.Connected())

    def stop_connection(self):
        self.on_event(events.Disconnected())

    def add_persistence(self):
        pass

    def remove_persistence(self):
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
        def determine_initial_state(self):
            self.update_connection_state(states.Disconnected())

    sm = MissingMethodsStateMachine()
    with pytest.raises(NotImplementedError):
        sm.start_connection()

    with pytest.raises(NotImplementedError):
        sm.stop_connection()

    with pytest.raises(NotImplementedError):
        sm.add_persistence()

    with pytest.raises(NotImplementedError):
        sm.remove_persistence()


def test_expected_initial_state(dummy_state_machine):
    sm = dummy_state_machine()
    assert sm.status.state == states.Disconnected().state


def test_unexpected_initial_state(dummy_state_machine):
    sm = dummy_state_machine()
    assert sm.status.state != states.Connected().state


def test_from_disconnected_to_connected(dummy_state_machine, dummy_listener_object):

    def start_connection(self):
        thread = Thread(target=self._async_start)
        thread.start()

    def _async_start(self):
        time.sleep(0.2)
        self.on_event(events.Connected())

    dummy_state_machine.start_connection = start_connection
    dummy_state_machine._async_start = _async_start
    sm = dummy_state_machine()
    lc = dummy_listener_object()
    sm.register(lc)

    assert sm.status.state == states.Disconnected().state

    sm.on_event(events.Up())

    start = time.time()
    while True:
        if sm.status.state == states.Connected.state:
            break
        elif time.time() - start >= TIMEOUT_LIMIT:
            sm.on_event(events.Timeout())


def test_from_disconnected_to_error(dummy_state_machine, dummy_listener_object):

    def stop_connection(self):
        thread = Thread(target=self._async_stop)
        thread.start()

    def _async_stop(self):
        time.sleep(0.2)
        self.on_event(events.Disconnected())

    def start_connection(self):
        thread = Thread(target=self._async_start)
        thread.start()

    def _async_start(self):
        time.sleep(0.2)
        self.on_event(events.AuthDenied())

    dummy_state_machine.stop_connection = stop_connection
    dummy_state_machine._async_stop = _async_stop
    dummy_state_machine.start_connection = start_connection
    dummy_state_machine._async_start = _async_start
    sm = dummy_state_machine()
    lc = dummy_listener_object()
    lc.test_flow = FlowTestCases.DISCONNECTED_TO_ERROR
    sm.register(lc)

    assert sm.status.state == states.Disconnected().state

    sm.on_event(events.Up())

    start = time.time()
    while True:
        if sm.status.state == states.Disconnected.state:
            break
        elif sm.status.state == states.Error.state:
            sm.on_event(events.Down())
        elif time.time() - start >= TIMEOUT_LIMIT:
            sm.on_event(events.Timeout())


def test_from_connected_to_disconnected(dummy_state_machine, dummy_listener_object):
    def determine_initial_state(self):
        self.update_connection_state(states.Connected())

    def stop_connection(self):
        thread = Thread(target=self._async_stop)
        thread.start()

    def _async_stop(self):
        time.sleep(0.2)
        self.on_event(events.Disconnected())

    dummy_state_machine.determine_initial_state = determine_initial_state
    dummy_state_machine.stop_connection = stop_connection
    dummy_state_machine._async_stop = _async_stop
    sm = dummy_state_machine()
    lc = dummy_listener_object()
    lc.test_flow = FlowTestCases.CONNECTED_TO_DISCONNECTED
    sm.register(lc)

    assert sm.status.state == states.Connected().state

    sm.on_event(events.Down())

    start = time.time()
    while True:
        if sm.status.state == states.Disconnected.state:
            break
        elif time.time() - start >= TIMEOUT_LIMIT:
            sm.on_event(events.Timeout())


def test_from_connected_to_error(dummy_state_machine, dummy_listener_object):
    def determine_initial_state(self):
        self.update_connection_state(states.Connected())

    def stop_connection(self):
        thread = Thread(target=self._async_stop)
        thread.start()

    def _async_stop(self):
        time.sleep(0.2)
        self.on_event(events.Disconnected())

    dummy_state_machine.determine_initial_state = determine_initial_state
    dummy_state_machine.stop_connection = stop_connection
    dummy_state_machine._async_stop = _async_stop
    sm = dummy_state_machine()
    lc = dummy_listener_object()
    lc.test_flow = FlowTestCases.CONNECTED_TO_ERROR
    sm.register(lc)

    assert sm.status.state == states.Connected().state

    sm.on_event(events.AuthDenied())

    start = time.time()
    while True:
        if sm.status.state == states.Disconnected.state:
            break
        elif sm.status.state == states.Error.state:
            sm.on_event(events.Down())
        elif time.time() - start >= TIMEOUT_LIMIT:
            sm.on_event(events.Timeout())
