import os

import pytest
from proton.vpn.connection.vpnconfiguration import (OpenVPNTCPConfig,
                                                    OpenVPNUDPConfig,
                                                    OVPNConfig,
                                                    VPNConfiguration,
                                                    WireguardConfig)

from .common import (CWD, MalformedVPNCredentials, MalformedVPNServer,
                     MockSettings, MockVpnCredentials, MockVpnServer)


@pytest.fixture
def modified_exec_env():
    from proton.vpn.connection.utils import ExecutionEnvironment
    m = ExecutionEnvironment().path_runtime
    ExecutionEnvironment.path_runtime = CWD
    yield ExecutionEnvironment().path_runtime
    ExecutionEnvironment.path_runtime = m


class MockVpnConfiguration(VPNConfiguration):
    extension = ".test-extension"

    def generate(self):
        return "test-content"


def test_init_with_expected_args():
    VPNConfiguration(MockVpnServer(), MockVpnCredentials())


def test_init_with_unexpected_args():
    with pytest.raises(TypeError):
        VPNConfiguration(None, None, None)


def test_not_implemented_generate():
    cfg = VPNConfiguration(MockVpnServer(), MockVpnCredentials())
    with pytest.raises(NotImplementedError):
        cfg.generate()


def test_change_certificate():
    cfg = VPNConfiguration(MockVpnServer(), MockVpnCredentials())
    assert cfg.use_certificate is False
    cfg.use_certificate = True
    assert cfg.use_certificate is True


def test_change_settings():
    class NewSettings:
        @property
        def dns_custom_ips(self):
            return ["99.99.99.99"]

        @property
        def split_tunneling_ips(self):
            return ["102.64.10.16"]

        @property
        def ipv6(self):
            return True

    cfg = VPNConfiguration(MockVpnServer(), MockVpnCredentials())
    assert cfg.settings.ipv6 is False
    assert cfg.settings.dns_custom_ips == []
    assert cfg.settings.split_tunneling_ips == []

    cfg.settings = NewSettings()

    assert cfg.settings.ipv6 is not False
    assert cfg.settings.dns_custom_ips != []
    assert cfg.settings.split_tunneling_ips != []


def test_change_settings_to_none():
    cfg = VPNConfiguration(MockVpnServer(), MockVpnCredentials(), MockSettings())
    assert cfg.settings.dns_custom_ips != []
    assert cfg.settings.split_tunneling_ips != []

    cfg.settings = None

    assert cfg.settings.dns_custom_ips == []
    assert cfg.settings.split_tunneling_ips == []


def test_ensure_configuration_file_is_created(modified_exec_env):
    cfg = MockVpnConfiguration(MockVpnServer(), MockVpnCredentials())
    with cfg as f:
        assert os.path.isfile(f)


def test_ensure_configuration_file_is_deleted():
    cfg = MockVpnConfiguration(MockVpnServer(), MockVpnCredentials())
    fp = None
    with cfg as f:
        fp = f
        assert os.path.isfile(fp)

    assert not os.path.isfile(fp)


def test_ensure_generate_is_returning_expected_content():
    cfg = MockVpnConfiguration(MockVpnServer(), MockVpnCredentials())
    with cfg as f:
        with open(f) as _f:
            line = _f.readline()
            _cfg = MockVpnConfiguration(MockVpnServer(), MockVpnCredentials())
            assert line == _cfg.generate()


def test_ensure_same_configuration_file_in_case_of_duplicate():
    cfg = MockVpnConfiguration(MockVpnServer(), MockVpnCredentials())
    with cfg as f:
        with cfg as _f:
            assert os.path.isfile(f) and os.path.isfile(_f) and f == _f


@pytest.mark.parametrize(
    "expected_mask, cidr", [
        ("0.0.0.0", "0"),
        ("255.0.0.0", "8"),
        ("255.255.0.0", "16"),
        ("255.255.255.0", "24"),
        ("255.255.255.255", "32")
    ]
)
def test_cidr_to_netmask(cidr, expected_mask):
    cfg = MockVpnConfiguration(MockVpnServer(), MockVpnCredentials())
    assert cfg.cidr_to_netmask(cidr) == expected_mask


@pytest.mark.parametrize("ipv4", ["192.168.1.1", "109.162.10.9", "1.1.1.1", "10.10.10.10"])
def test_valid_ips(ipv4):
    cfg = MockVpnConfiguration(MockVpnServer(), MockVpnCredentials())
    cfg.is_valid_ipv4(ipv4)


@pytest.mark.parametrize("ipv4", ["192.168.1.90451", "109.", "1.-.1.1", "1111.10.10.10"])
def test_not_valid_ips(ipv4):
    cfg = MockVpnConfiguration(MockVpnServer(), MockVpnCredentials())
    cfg.is_valid_ipv4(ipv4)


@pytest.mark.parametrize("protocol", ["udp", "tcp"])
def test_ovpnconfig_with_default_settings(protocol, modified_exec_env):
    ovpn_cfg = OVPNConfig(MockVpnServer(), MockVpnCredentials(), MockSettings())
    ovpn_cfg._protocol = protocol
    output = ovpn_cfg.generate()
    assert ovpn_cfg._vpnserver.server_ip in output


@pytest.mark.parametrize("protocol", ["udp", "tcp"])
def test_ovpnconfig_with_missing_settings(protocol):
    ovpn_cfg = OVPNConfig(MockVpnServer(), MockVpnCredentials())
    ovpn_cfg._protocol = protocol
    ovpn_cfg.generate()


@pytest.mark.parametrize("protocol", ["udp", "tcp"])
def test_ovpnconfig_with_malformed_params(protocol):
    with pytest.raises(TypeError):
        OVPNConfig(None, None, None)


@pytest.mark.parametrize("protocol", ["udp", "tcp"])
def test_ovpnconfig_with_certificate_and_malformed_credentials(protocol):
    ovpn_cfg = OVPNConfig(MockVpnServer(), MalformedVPNCredentials())
    ovpn_cfg._protocol = protocol
    ovpn_cfg.use_certificate = True
    with pytest.raises(AttributeError):
        ovpn_cfg.generate()


@pytest.mark.parametrize("protocol", ["udp", "tcp"])
def test_ovpnconfig_with_malformed_server(protocol):
    ovpn_cfg = OVPNConfig(MalformedVPNServer(), MockVpnCredentials())
    ovpn_cfg._protocol = protocol
    with pytest.raises(AttributeError):
        ovpn_cfg.generate()


@pytest.mark.parametrize("protocol", ["udp", "tcp"])
def test_ovpnconfig_with_malformed_server_and_credentials(protocol):
    ovpn_cfg = OVPNConfig(MalformedVPNServer(), MalformedVPNCredentials())
    ovpn_cfg._protocol = protocol
    with pytest.raises(AttributeError):
        ovpn_cfg.generate()


def test_wireguard_expected_configurations():
    wg_cfg = WireguardConfig(MockVpnServer(), MockVpnCredentials())
    wg_cfg.use_certificate = True
    with wg_cfg as f:
        assert os.path.isfile(f)
        with open(f) as _f:
            content = _f.read()
            assert MockVpnCredentials().pubkey_credentials.wg_private_key in content
            assert MockVpnServer().wg_public_key_x25519 in content
            assert MockVpnServer().server_ip in content


def test_wireguard_with_malformed_credentials():
    wg_cfg = WireguardConfig(MockVpnServer(), MalformedVPNCredentials())
    wg_cfg.use_certificate = True
    with pytest.raises(AttributeError):
        with wg_cfg:
            pass


def test_wireguard_with_non_certificate():
    wg_cfg = WireguardConfig(MockVpnServer(), MockVpnCredentials())
    with pytest.raises(RuntimeError):
        with wg_cfg:
            pass


@pytest.mark.parametrize(
    "protocol, expected_class", [
        ("openvpn_tcp", OpenVPNTCPConfig),
        ("openvpn_udp", OpenVPNUDPConfig),
        ("wireguard", WireguardConfig),
    ]
)
def test_get_expected_config_from_factory(protocol, expected_class):
    config = VPNConfiguration.from_factory(protocol)
    assert isinstance(config(MockVpnServer(), MockVpnCredentials()), expected_class)
