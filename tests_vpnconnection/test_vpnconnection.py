import os
import shutil

import pytest
from proton.vpn.connection import VPNConnection, states

from .common import (CWD, PERSISTANCE_CWD, MalformedVPNCredentials,
                     MalformedVPNServer, MockSettings, MockVpnCredentials,
                     MockVpnServer)

PREFIX = "persistance-prefix_"


def teardown_module(module):
    shutil.rmtree(PERSISTANCE_CWD)


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
def modified_exec_env():
    from proton.vpn.connection.utils import ExecutionEnvironment
    m = ExecutionEnvironment().path_runtime
    ExecutionEnvironment.path_runtime = CWD
    yield ExecutionEnvironment().path_runtime
    ExecutionEnvironment.path_runtime = m


class MockVpnConnection(VPNConnection):
    _persistence_prefix = PREFIX

    def _determine_initial_state(self):
        self._update_connection_state(states.Disconnected())

    def _start_connection(self):
        pass

    def _stop_connection(self):
        pass

    def _get_connection(self):
        return True


class MockVpnConnectionMissingGetConnection(VPNConnection):
    _persistence_prefix = PREFIX

    def _determine_initial_state(self):
        self._update_connection_state(states.Disconnected())

    def _start_connection(self):
        pass

    def _stop_connection(self):
        pass


class MockListenerClass:
    def status_update(self, status):
        pass


def test_not_implemented_get_connection(vpn_server, vpn_credentials, settings):
    vpconn = MockVpnConnectionMissingGetConnection(vpn_server, vpn_credentials)
    with pytest.raises(NotImplementedError):
        vpconn._get_connection()


def test_init(vpn_server, vpn_credentials, settings):
    MockVpnConnection(vpn_server, vpn_credentials, settings)


def test_ensure_settings_change(vpn_server, vpn_credentials, settings):
    vpnconn = MockVpnConnection(vpn_server, vpn_credentials, settings)
    assert vpnconn.settings.split_tunneling_ips == settings.split_tunneling_ips
    vpnconn.settings = None
    assert vpnconn.settings is None


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


def test_ensure_unique_id_is_set_with_no_persistence(vpn_server, vpn_credentials, modified_exec_env):
    vpnconn = MockVpnConnection(vpn_server, vpn_credentials)
    vpnconn._persistence_prefix = "ensure-unique-id"
    vpnconn._ensure_unique_id_is_set()
    assert vpnconn._unique_id is None


def test_ensure_unique_id_is_set_with_persistence(vpn_server, vpn_credentials, modified_exec_env):
    _prefix = "unique-id-with-persistence"
    vpnconn = MockVpnConnection(vpn_server, vpn_credentials)

    assert vpnconn._unique_id is None

    vpnconn._persistence_prefix = _prefix
    vpnconn._unique_id = "test-unique-id"
    vpnconn._add_persistence()

    assert os.path.isfile(
        os.path.join(
            PERSISTANCE_CWD, "{}{}".format(
                vpnconn._persistence_prefix,
                vpnconn._unique_id
            )
        )
    )

    assert vpnconn._unique_id is not None

    del vpnconn
    _vpnconn = MockVpnConnection(vpn_server, vpn_credentials)
    _vpnconn._persistence_prefix = _prefix
    _vpnconn._ensure_unique_id_is_set()

    assert _vpnconn._unique_id


def test_add_persistence(vpn_server, vpn_credentials, modified_exec_env):
    vpnconn = MockVpnConnection(vpn_server, vpn_credentials)
    vpnconn._unique_id = "add-persistance"
    vpnconn._add_persistence()
    assert os.path.isfile(
        os.path.join(
            PERSISTANCE_CWD, "{}{}".format(
                vpnconn._persistence_prefix,
                vpnconn._unique_id
            )
        )
    )
    vpnconn._remove_persistence()


def test_remove_persistence(vpn_server, vpn_credentials, modified_exec_env):
    vpnconn = MockVpnConnection(vpn_server, vpn_credentials)
    vpnconn._unique_id = "remove-persistance"
    vpnconn._add_persistence()
    assert os.path.isfile(
        os.path.join(
            PERSISTANCE_CWD, "{}{}".format(
                vpnconn._persistence_prefix,
                vpnconn._unique_id
            )
        )
    )
    vpnconn._remove_persistence()
    assert not os.path.isfile(
        os.path.join(
            PERSISTANCE_CWD, "{}{}".format(
                vpnconn._persistence_prefix,
                vpnconn._unique_id
            )
        )
    )


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


def test_up(vpn_server, vpn_credentials):
    vpnconn = MockVpnConnection(vpn_server, vpn_credentials)
    vpnconn.register(MockListenerClass())
    old_state = vpnconn.status.state
    vpnconn.up()
    assert vpnconn.status.state == states.Connecting().state and old_state != vpnconn.status.state


def test_down(vpn_server, vpn_credentials):
    def _determine_initial_state(self):
        self._update_connection_state(states.Connected())

    m = MockVpnConnection._determine_initial_state
    MockVpnConnection._determine_initial_state = _determine_initial_state

    vpnconn = MockVpnConnection(vpn_server, vpn_credentials)
    vpnconn.register(MockListenerClass())

    old_state = vpnconn.status.state
    vpnconn.down()
    assert vpnconn.status.state == states.Disconnecting().state and old_state != vpnconn.status.state

    MockVpnConnection._determine_initial_state = m
