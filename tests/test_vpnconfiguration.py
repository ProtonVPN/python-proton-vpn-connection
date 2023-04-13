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
import os

import pytest
from proton.vpn.connection.vpnconfiguration import (OpenVPNTCPConfig,
                                                    OpenVPNUDPConfig,
                                                    OVPNConfig,
                                                    VPNConfiguration,
                                                    WireguardConfig,
                                                    DefaultSettings)

from .common import (CWD, MalformedVPNCredentials, MalformedVPNServer,
                     MockSettings, MockVpnCredentials, MockVpnServer)
import shutil

VPNCONFIG_DIR = os.path.join(CWD, "vpnconfig")


def setup_module(module):
    if not os.path.isdir(VPNCONFIG_DIR):
        os.makedirs(VPNCONFIG_DIR)


def teardown_module(module):
    if os.path.isdir(VPNCONFIG_DIR):
        shutil.rmtree(VPNCONFIG_DIR)


@pytest.fixture
def modified_exec_env():
    from proton.utils.environment import ExecutionEnvironment
    m = ExecutionEnvironment().path_runtime
    ExecutionEnvironment.path_runtime = VPNCONFIG_DIR
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


def test_custom_settings():
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

    cfg = VPNConfiguration(MockVpnServer(), MockVpnCredentials(), settings=NewSettings())

    assert isinstance(cfg.settings, NewSettings)
    assert cfg.settings.dns_custom_ips == ["99.99.99.99"]
    assert cfg.settings.split_tunneling_ips == ["102.64.10.16"]
    assert cfg.settings.ipv6


def test_default_settings():
    cfg = VPNConfiguration(MockVpnServer(), MockVpnCredentials(), settings=None)
    assert isinstance(cfg.settings, DefaultSettings)


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
def test_ovpnconfig_with_settings(protocol, modified_exec_env):
    ovpn_cfg = OVPNConfig(MockVpnServer(), MockVpnCredentials(), MockSettings())
    ovpn_cfg._protocol = protocol
    output = ovpn_cfg.generate()
    assert ovpn_cfg._vpnserver.server_ip in output
    assert 'pull-filter ignore "ifconfig-ipv6"' not in output  # MockSettings().ipv6 is True
    assert 'pull-filter ignore "route-ipv6"' not in output  # MockSettings().ipv6 is True


@pytest.mark.parametrize("protocol", ["udp", "tcp"])
def test_ovpnconfig_with_missing_settings_applies_expected_defaults(protocol, modified_exec_env):
    ovpn_cfg = OVPNConfig(MockVpnServer(), MockVpnCredentials())
    ovpn_cfg._protocol = protocol
    generated_cfg = ovpn_cfg.generate()
    # By default, IPv6 should be disabled
    assert 'pull-filter ignore "ifconfig-ipv6"' in generated_cfg
    assert 'pull-filter ignore "route-ipv6"' in generated_cfg


@pytest.mark.parametrize("protocol", ["udp", "tcp"])
def test_ovpnconfig_with_malformed_params(protocol, modified_exec_env):
    with pytest.raises(TypeError):
        OVPNConfig(None, None, None)


@pytest.mark.parametrize("protocol", ["udp", "tcp"])
def test_ovpnconfig_with_certificate_and_malformed_credentials(protocol, modified_exec_env):
    ovpn_cfg = OVPNConfig(MockVpnServer(), MalformedVPNCredentials())
    ovpn_cfg._protocol = protocol
    ovpn_cfg.use_certificate = True
    with pytest.raises(AttributeError):
        ovpn_cfg.generate()


@pytest.mark.parametrize("protocol", ["udp", "tcp"])
def test_ovpnconfig_with_malformed_server(protocol, modified_exec_env):
    ovpn_cfg = OVPNConfig(MalformedVPNServer(), MockVpnCredentials())
    ovpn_cfg._protocol = protocol
    with pytest.raises(AttributeError):
        ovpn_cfg.generate()


@pytest.mark.parametrize("protocol", ["udp", "tcp"])
def test_ovpnconfig_with_malformed_server_and_credentials(protocol, modified_exec_env):
    ovpn_cfg = OVPNConfig(MalformedVPNServer(), MalformedVPNCredentials())
    ovpn_cfg._protocol = protocol
    with pytest.raises(AttributeError):
        ovpn_cfg.generate()


def test_wireguard_config_content_generation(modified_exec_env):
    server = MockVpnServer()
    credentials = MockVpnCredentials()
    settings = MockSettings()
    wg_cfg = WireguardConfig(server, credentials, settings)
    wg_cfg.use_certificate = True
    generated_cfg = wg_cfg.generate()
    assert credentials.pubkey_credentials.wg_private_key in generated_cfg
    assert server.wg_public_key_x25519 in generated_cfg
    assert server.server_ip in generated_cfg
    assert "AllowedIPs = 0.0.0.0/0, ::/0" in generated_cfg  # MockSettings().ipv6 is True


def test_wireguard_with_malformed_credentials(modified_exec_env):
    wg_cfg = WireguardConfig(MockVpnServer(), MalformedVPNCredentials())
    wg_cfg.use_certificate = True
    with pytest.raises(AttributeError):
        wg_cfg.generate()


def test_wireguard_with_non_certificate(modified_exec_env):
    wg_cfg = WireguardConfig(MockVpnServer(), MockVpnCredentials())
    with pytest.raises(RuntimeError):
        wg_cfg.generate()


def test_wireguard_without_settings(modified_exec_env):
    server = MockVpnServer()
    credentials = MockVpnCredentials()
    wg_cfg = WireguardConfig(server, credentials, settings=None)
    wg_cfg.use_certificate = True
    generated_cfg = wg_cfg.generate()
    generated_cfg_lines = generated_cfg.splitlines()
    assert "AllowedIPs = 0.0.0.0/0" in generated_cfg_lines


@pytest.mark.parametrize(
    "protocol, expected_class", [
        ("openvpn-tcp", OpenVPNTCPConfig),
        ("openvpn-udp", OpenVPNUDPConfig),
        ("wireguard", WireguardConfig),
    ]
)
def test_get_expected_config_from_factory(protocol, expected_class):
    config = VPNConfiguration.from_factory(protocol)
    assert isinstance(config(MockVpnServer(), MockVpnCredentials()), expected_class)
