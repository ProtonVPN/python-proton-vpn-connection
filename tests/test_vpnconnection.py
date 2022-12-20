import os
from unittest.mock import Mock

import pytest
from proton.vpn.connection import VPNConnection, states
from proton.vpn.connection.persistence import ConnectionPersistence, ConnectionParameters

from .common import (
    MalformedVPNCredentials, MalformedVPNServer, MockSettings,
    MockVpnCredentials, MockVpnServer
)

@pytest.fixture
def settings():
    return MockSettings()


@pytest.fixture
def vpn_credentials():
    return MockVpnCredentials()


@pytest.fixture
def vpn_server():
    return MockVpnServer()


@pytest.fixture
def connection_persistence_mock():
    return Mock(ConnectionPersistence)


# <<<<<<<<<<<<<
# <<<<<<<<<<<<< Needed mocks classes for testing
# <<<<<<<<<<<<<

class classproperty(object):
    def __init__(self, f):
        self.f = f

    def __get__(self, obj, owner):
        return self.f(owner)


class MockOptimalBackend:
    backend = "optimal"

    def __init__(self, protocol):
        self.protocol = protocol

    @classproperty
    def class_name(cls):
        return MockOptimalBackend.backend

    @classproperty
    def priority(cls):
        return 100

    @classproperty
    def cls(cls):
        return MockCls


class MockBackendLowPriority:
    backend = "lowpriority"

    def __init__(self, protocol):
        self.protocol = protocol

    @classproperty
    def class_name(cls):
        return MockBackendLowPriority.backend

    @classproperty
    def priority(cls):
        return 10

    @classproperty
    def cls(cls):
        return MockLowPriorityCls


class MockBackendNotValid:
    backend = "notvalid"

    def __init__(self, protocol):
        self.protocol = protocol

    @classproperty
    def class_name(cls):
        return MockBackendNotValid.backend

    @classproperty
    def priority(cls):
        return 50

    @classproperty
    def cls(cls):
        return MockNotValidCls


class MockCls:

    @classmethod
    def factory(cls, protocol):
        backend = MockOptimalBackend(protocol)
        return backend

    @classmethod
    def _validate(cls):
        return True

    @classmethod
    def _get_connection(cls):
        return True


class MockLowPriorityCls:

    @classmethod
    def factory(cls, protocol):
        backend = MockBackendLowPriority(protocol)
        return backend

    @classmethod
    def _validate(cls):
        return True

    @classmethod
    def _get_connection(cls):
        return True


class MockNotValidCls:

    @classmethod
    def factory(cls, protocol):
        backend = MockBackendNotValid(protocol)
        return backend

    @classmethod
    def _validate(cls):
        return False

    @classmethod
    def _get_connection(cls):
        return True


def modified_single_get_all(self, *args):
    return [MockOptimalBackend]


def modified_multiple_get_all(self, *args):
    return [MockOptimalBackend, MockBackendLowPriority, MockBackendNotValid]


@pytest.fixture
def modified_loader_single_backend():
    from proton.loader import Loader
    m = Loader.get_all
    Loader.get_all = modified_single_get_all
    yield Loader
    Loader.get_all = m


@pytest.fixture
def modified_loader_multiple_backend():
    from proton.loader import Loader
    m = Loader.get_all
    Loader.get_all = modified_multiple_get_all
    yield Loader
    Loader.get_all = m


@pytest.fixture
def modified_loader_with_not_valid_backend():
    def _loader(self, *args, **kwargs):
        return [MockBackendNotValid]

    from proton.loader import Loader
    m = Loader.get_all
    Loader.get_all = _loader
    yield Loader
    Loader.get_all = m

# >>>>>>>>>>>>>>>>>>>>>>
# >>>>>>>>>>>>>>>>>>>>>>
# >>>>>>>>>>>>>>>>>>>>>>


class MockVpnConnection(VPNConnection):
    backend = "mock-backend2"
    protocol = "mock-protocol2"

    def determine_initial_state(self):
        self.update_connection_state(states.Disconnected())

    def start_connection(self):
        pass

    def stop_connection(self):
        pass

    def _get_connection(self):
        return True


class MockVpnConnectionMissingGetConnection(VPNConnection):
    backend = "mock-backend"
    protocol = "mock-protocol"

    def determine_initial_state(self):
        self.update_connection_state(states.Disconnected())

    def start_connection(self):
        pass

    def stop_connection(self):
        pass


class MockListenerClass:
    def status_update(self, status):
        pass


def test_not_implemented_get_connection(vpn_server, vpn_credentials, settings):
    vpconn = MockVpnConnectionMissingGetConnection(vpn_server, vpn_credentials)
    with pytest.raises(NotImplementedError):
        vpconn._get_connection()


def test_up(vpn_server, vpn_credentials, connection_persistence_mock):
    def _get_connection():
        return False

    vpnconn = MockVpnConnection(
        vpn_server,
        vpn_credentials,
        connection_persistence=connection_persistence_mock
    )
    vpnconn._get_connection = _get_connection
    vpnconn.register(MockListenerClass())
    vpnconn.up()
    assert vpnconn.status.state == states.Connecting().state


def test_down(vpn_server, vpn_credentials):
    def determine_initial_state(self):
        self.update_connection_state(states.Connected())

    m = MockVpnConnection.determine_initial_state
    MockVpnConnection.determine_initial_state = determine_initial_state

    vpnconn = MockVpnConnection(vpn_server, vpn_credentials)
    vpnconn.register(MockListenerClass())

    vpnconn.down()
    assert vpnconn.status.state == states.Disconnecting().state

    MockVpnConnection.determine_initial_state = m


def test_ensure_there_are_no_other_current_protonvpn_connections(vpn_server, vpn_credentials, settings):
    from proton.vpn.connection.exceptions import ConflictError
    vpnconn = MockVpnConnection(vpn_server, vpn_credentials, settings)
    with pytest.raises(ConflictError):
        vpnconn._ensure_there_are_no_other_current_protonvpn_connections()


@pytest.mark.parametrize("env_var_value", ["False", "no", "test", "bool", "0", "tr!ue"])
def test_not_use_certificate(vpn_server, vpn_credentials, env_var_value):
    vpnconn = MockVpnConnection(vpn_server, vpn_credentials)
    os.environ["PROTONVPN_USE_CERTIFICATE"] = env_var_value
    assert vpnconn._use_certificate is False


@pytest.mark.parametrize("env_var_value", ["True", "true", "tr ue", "tru e", "TRue", "TRUe!"])
def test_use_certificate(vpn_server, vpn_credentials, env_var_value):
    vpnconn = MockVpnConnection(vpn_server, vpn_credentials)
    os.environ["PROTONVPN_USE_CERTIFICATE"] = env_var_value
    assert vpnconn._use_certificate is True


def test_default_validate_value():
    assert MockVpnConnection._validate() is False


def test_default_get_validate_value():
    assert MockVpnConnection._get_priority() is None


def test_ensure_unique_id_is_set_initializes_id_as_none_without_a_persisted_connection(
        connection_persistence_mock
):
    connection_persistence_mock.load.return_value = None
    vpnconn = MockVpnConnection(
        vpnserver=None,
        vpncredentials=None,
        connection_persistence=connection_persistence_mock
    )

    vpnconn._ensure_unique_id_is_set()

    connection_persistence_mock.load.assert_called_once()
    assert vpnconn._unique_id is None


def test_ensure_unique_id_is_set_loads_connection_id_from_persisted_connection(
        vpn_server, vpn_credentials, connection_persistence_mock
):
    connection_persistence_mock.load.return_value = ConnectionParameters(
        connection_id="connection_id",
        backend="backend",
        protocol="protocol",
        server_id="server_id",
        server_name="server_name"
    )
    vpnconn = MockVpnConnection(
        vpn_server,
        vpn_credentials,
        connection_persistence=connection_persistence_mock
    )
    assert vpnconn._unique_id is None

    vpnconn._ensure_unique_id_is_set()

    connection_persistence_mock.load.assert_called_once()
    assert vpnconn._unique_id


def test_add_persistence(vpn_server, vpn_credentials, connection_persistence_mock):
    vpnconn = MockVpnConnection(
        vpn_server,
        vpn_credentials,
        connection_persistence=connection_persistence_mock
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
    vpnconn = MockVpnConnection(
        vpn_server,
        vpn_credentials,
        connection_persistence=connection_persistence_mock
    )
    vpnconn._unique_id = "remove-persistance"

    vpnconn.remove_persistence()

    connection_persistence_mock.remove.assert_called()


def test_get_user_pass_with_malformed_args():
    vpnconn = MockVpnConnection(MalformedVPNServer(), MalformedVPNCredentials())
    with pytest.raises(AttributeError):
        vpnconn._get_user_pass()


def test_get_user_pass(vpn_server, vpn_credentials):
    vpnconn = MockVpnConnection(vpn_server, vpn_credentials)
    u, p = vpn_credentials.userpass_credentials.username, vpn_credentials.userpass_credentials.password
    user, password = vpnconn._get_user_pass()
    assert u == user and p == password


def test_get_user_with_default_feature_flags(vpn_server, vpn_credentials):
    vpnconn = MockVpnConnection(vpn_server, vpn_credentials)
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

    vpnconn = MockVpnConnection(vpn_server, vpn_credentials, MockSettings())
    u = vpn_credentials.userpass_credentials.username
    user, _ = vpnconn._get_user_pass(True)
    _u = "+".join([u] + vpnconn._get_feature_flags())

    assert user == _u

    MockSettings.features = m


def test_get_from_factory_single_backend(modified_loader_single_backend):
    backend = VPNConnection.get_from_factory()
    assert isinstance(backend, MockOptimalBackend)


def test_get_from_factory_multiple_backends(modified_loader_multiple_backend):
    backend = VPNConnection.get_from_factory()
    assert isinstance(backend, MockOptimalBackend)


def test_get_low_priority_backend_from_factory(modified_loader_multiple_backend):
    backend = VPNConnection.get_from_factory(backend="lowpriority")
    assert isinstance(backend, MockBackendLowPriority)


def test_get_not_valid_from_factory(modified_loader_multiple_backend):
    from proton.vpn.connection.exceptions import MissingBackendDetails
    with pytest.raises(MissingBackendDetails):
        VPNConnection.get_from_factory(backend="nonexistent")


def test_get_connection_from_optimal_backend(modified_loader_multiple_backend):
    assert VPNConnection.get_current_connection()
