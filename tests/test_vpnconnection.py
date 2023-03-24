import os
from unittest.mock import Mock, patch

import pytest

from proton.vpn.connection import VPNConnection, states
from proton.vpn.connection.persistence import ConnectionPersistence, ConnectionParameters
from proton.vpn.connection.states import StateContext

from .common import (
    MalformedVPNCredentials, MalformedVPNServer, MockSettings,
    MockVpnCredentials, MockVpnServer
)


@pytest.fixture
def settings():
    return Mock()


@pytest.fixture
def vpn_credentials():
    return MockVpnCredentials()


@pytest.fixture
def vpn_server():
    return MockVpnServer()


@pytest.fixture
def connection_persistence_mock():
    return Mock(ConnectionPersistence)


class DummyVPNConnection(VPNConnection):
    """Dummy VPN connection implementing all the required abstract methods."""
    backend = "dummy"
    protocol = "protocol"

    def __init__(self, *args, connection_persistence = None, killswitch = None, **kwargs):
        self.initialize_persisted_connection_mock = Mock(return_value=states.Connected(StateContext(connection=self)))

        # Make sure we don't trigger connection persistence nor the kill switch.
        connection_persistence = connection_persistence or Mock()
        killswitch = killswitch or Mock()

        super().__init__(*args, connection_persistence=connection_persistence, killswitch=killswitch, **kwargs)

    def _initialize_persisted_connection(
            self, persisted_parameters: ConnectionParameters
    ) -> states.State:
        return self.initialize_persisted_connection_mock(persisted_parameters)

    def start(self):
        pass

    def stop(self):
        pass

    def _get_connection(self):
        return None

    def _validate(cls) -> bool:
        return True

    def _get_priority(cls) -> int:
        return 100


class InvalidVPNConnection(VPNConnection):
    """VPN connection class missing abstract method implementations."""

    backend = "invalid"
    protocol = "protocol"


def test_vpn_connection_subclass_raises_type_exception_if_abstract_methods_were_not_implemented():
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        InvalidVPNConnection(server=None, credentials=None)


def test_vpn_connection_initialized_without_a_persisted_connection():
    """
    When a VPNConnection object is created without passing persisted parameters
    then it should be initialized without a unique id and with the Disconnected
    initial state.
    """
    vpnconn = DummyVPNConnection(
        server=None,
        credentials=None,
        persisted_parameters=None
    )

    assert vpnconn._unique_id is None
    vpnconn.initialize_persisted_connection_mock.assert_not_called()
    assert isinstance(vpnconn.initial_state, states.Disconnected)


def test_vpn_connection_initialized_from_persisted_connection(
        connection_persistence_mock
):
    """
    When a VPNConnection object is created passing persisted parameters
    then it should be initialized with the persisted connection id and
    the initial state should be determined by calling `_initialize_persisted_connection`.
    """
    persisted_parameters = ConnectionParameters(
        connection_id="connection-id",
        backend=DummyVPNConnection.backend,
        protocol=DummyVPNConnection.protocol,
        server_id="server-id",
        server_name="server-name"
    )

    vpnconn = DummyVPNConnection(
        server=None,
        credentials=None,
        persisted_parameters=persisted_parameters
    )

    assert vpnconn._unique_id
    vpnconn.initialize_persisted_connection_mock.assert_called_with(persisted_parameters)
    assert vpnconn.initial_state is vpnconn.initialize_persisted_connection_mock.return_value


def test_add_persistence(vpn_server, vpn_credentials, connection_persistence_mock):
    vpnconn = DummyVPNConnection(
        vpn_server,
        vpn_credentials,
        connection_persistence=connection_persistence_mock,
    )
    vpnconn._unique_id = "add-persistence"

    vpnconn.add_persistence()

    connection_persistence_mock.save.assert_called_once()
    persistence_params = connection_persistence_mock.save.call_args.args[0]
    assert persistence_params.connection_id == "add-persistence"
    assert persistence_params.backend == vpnconn.backend
    assert persistence_params.protocol == vpnconn.protocol
    assert persistence_params.server_id == vpn_server.server_id
    assert persistence_params.server_name == vpn_server.server_name


def test_remove_persistence(vpn_server, vpn_credentials, connection_persistence_mock):
    vpnconn = DummyVPNConnection(
        vpn_server,
        vpn_credentials,
        connection_persistence=connection_persistence_mock
    )
    vpnconn._unique_id = "remove-persistence"

    vpnconn.remove_persistence()

    connection_persistence_mock.remove.assert_called()


def test_register_subscriber_delegates_to_publisher():
    publisher_mock = Mock()
    vpnconn = DummyVPNConnection(
        server=None, credentials=None, publisher=publisher_mock
    )

    def subscriber(event):
        pass
    vpnconn.register(subscriber)

    publisher_mock.register.assert_called_with(subscriber)


def test_unregister_subscriber_delegates_to_publisher():
    publisher_mock = Mock()
    vpnconn = DummyVPNConnection(
        server=None, credentials=None, publisher=publisher_mock
    )

    def subscriber(event):
        pass
    vpnconn.unregister(subscriber)

    publisher_mock.unregister.assert_called_with(subscriber)


@patch("proton.vpn.connection.vpnconnection.Loader")
def test_get_current_connection_returns_connection_initialized_with_persisted_parameters(
        Loader, connection_persistence_mock
):
    persisted_parameters = ConnectionParameters(
        connection_id="connection-id",
        backend="backend",
        protocol="protocol",
        server_id="server-id",
        server_name="server-name"
    )
    connection_persistence_mock.load.return_value = persisted_parameters

    current_connection = VPNConnection.get_current_connection(connection_persistence_mock)

    connection_persistence_mock.load.assert_called_once()
    Loader.get.assert_called_with("backend", persisted_parameters.backend)
    Loader.get.return_value.get_persisted_connection.assert_called_with(persisted_parameters)
    assert current_connection is Loader.get.return_value.get_persisted_connection.return_value


def test_get_current_connection_returns_none_if_persisted_parameters_were_not_found(
        connection_persistence_mock
):
    connection_persistence_mock.load.return_value = None
    current_connection = VPNConnection.get_current_connection(connection_persistence_mock)

    assert not current_connection


@pytest.mark.parametrize("env_var_value", ["False", "no", "test", "bool", "0", "tr!ue"])
def test_not_use_certificate(vpn_server, vpn_credentials, env_var_value):
    vpnconn = DummyVPNConnection(vpn_server, vpn_credentials)
    os.environ["PROTON_VPN_USE_CERTIFICATE"] = env_var_value
    assert vpnconn._use_certificate is False


@pytest.mark.parametrize("env_var_value", ["True", "true", "tr ue", "tru e", "TRue", "TRUe!"])
def test_use_certificate(vpn_server, vpn_credentials, env_var_value):
    vpnconn = DummyVPNConnection(vpn_server, vpn_credentials)
    os.environ["PROTON_VPN_USE_CERTIFICATE"] = env_var_value
    assert vpnconn._use_certificate is True


def test_get_user_pass_with_malformed_args():
    vpnconn = DummyVPNConnection(MalformedVPNServer(), MalformedVPNCredentials())
    with pytest.raises(AttributeError):
        vpnconn._get_user_pass()


def test_get_user_pass(vpn_server, vpn_credentials):
    vpnconn = DummyVPNConnection(vpn_server, vpn_credentials)
    u, p = vpn_credentials.userpass_credentials.username, vpn_credentials.userpass_credentials.password
    user, password = vpnconn._get_user_pass()
    assert u == user and p == password


def test_get_user_with_default_feature_flags(vpn_server, vpn_credentials):
    vpnconn = DummyVPNConnection(vpn_server, vpn_credentials)
    u = vpn_credentials.userpass_credentials.username
    user, _ = vpnconn._get_user_pass(True)
    _u = "+".join([u] + vpnconn._get_feature_flags())
    assert user == _u


@pytest.mark.parametrize(
    "ns, accel, pf, rn, sf",
    [
        ("f1", False, True, False, True),
        ("f2", False, True, False, True),
        ("f3", False, True, False, True),
        ("f1", True, False, True, False),
        ("f2", True, False, True, False),
        ("f3", True, False, True, False),
    ]
)
def test_get_user_with_features(vpn_server, vpn_credentials, ns, accel, pf, rn, sf):
    from proton.vpn.connection.interfaces import Features

    class MockFeatures(Features):

        @property
        def netshield(self):
            return ns

        @property
        def vpn_accelerator(self):
            return accel

        @property
        def port_forwarding(self):
            return pf

        @property
        def random_nat(self):
            return rn

        @property
        def safe_mode(self):
            return sf

    m = MockSettings.features
    MockSettings.features = MockFeatures()

    vpnconn = DummyVPNConnection(vpn_server, vpn_credentials, MockSettings())
    u = vpn_credentials.userpass_credentials.username
    user, _ = vpnconn._get_user_pass(True)
    _u = "+".join([u] + vpnconn._get_feature_flags())

    assert user == _u

    MockSettings.features = m
