"""
Interfaces required to be able to establish a VPN connection.


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
from typing import List, Optional, Protocol


class VPNServer(Protocol):  # pylint: disable=too-few-public-methods
    """
    Contains the necessary data about the server to connect to.

    Some properties like server_id and server_name are not used to establish
    the connection, but they are required for bookkeeping.
    When the connection is retrieved from persistence, then VPN clients
    can use this information to be able to identify the server that
    the VPN connection was established to. The server name is there mainly
    for debugging purposes.

    Attributes:
        server_ip: server ip to connect to.
        domain: domain to be used for x509 verification.
        wg_public_key_x25519: x25519 public key for wireguard peer verification.
        tcp_ports: List of TCP ports, if the protocol requires them.
        udp_ports: List of UDP ports, if the protocol requires them.
        server_id: ID of the server to connect to.
        server_name: Name of the server to connect to.
    """
    server_ip: str
    domain: str
    wg_public_key_x25519: str
    tcp_ports: List[int]
    udp_ports: List[int]
    server_id: str
    server_name: str
    label: str = None


class VPNPubkeyCredentials(Protocol):  # pylint: disable=too-few-public-methods
    """
    Object that gets certificates and privates keys
    for certificate based connections.

    An instance of this class is to be passed to VPNCredentials.

    Attributes:
        certificate_pem: X509 client certificate in PEM format.
        wg_private_key: wireguard private key in base64 format.
        openvpn_private_key: OpenVPN private key in PEM format.
    """
    certificate_pem: str
    wg_private_key: str
    openvpn_private_key: str


class VPNUserPassCredentials(Protocol):  # pylint: disable=too-few-public-methods
    """Provides username and password for username/password VPN authentication."""
    username: str
    password: str


class VPNCredentials(Protocol):  # pylint: disable=too-few-public-methods
    """
    Credentials are needed to establish a VPN connection.
    Depending on how these credentials are used, one method or the other may be
    irrelevant.

    Limitation:
    You could define only userpass_credentials, though at the cost that you
    won't be able to connect to wireguard (since it's based on certificates)
    and/or openvpn and ikev2 based with certificates. To guarantee maximum
    compatibility, it is recommended to pass both objects for
    username/password and certificates.
    """
    pubkey_credentials: Optional[VPNPubkeyCredentials]
    userpass_credentials: Optional[VPNUserPassCredentials]


class Features:
    """
    This class is used to define which features are supported.
    Even though there are multiple features that can be passed, they're not
    mandatory. In fact you could override one of the features that you would
    like to pass.

    Usage:
    ::
        from protonvpn.vpnconnection import Features

        class VPNFeatures(Settings):

            @property
            def netshield(self):
                return 0

            @property
            def vpn_accelerator(self):
                return True

            @property
            def port_forwarding(self):
                return False

            @property
            def random_nat(self):
                return True

    Note: Not all fields are mandatory to override, only those that are
    actually needed, ie:

    ::
        from protonvpn.vpnconnection import Settings

        class VPNSettings(Settings):

            @property
            def netshield(self):
                return 0

    Passing only this is perfectly fine.
    """

    @property
    def netshield(self):
        """
        It will always return int since _transform_features_to_flags()
        uses those values directly

        :return: netshield state value
        :rtype: int
        """
        return None

    @property
    def vpn_accelerator(self):
        """
        :return: vpn accelerator state value
        :rtype: bool
        """
        return None

    @property
    def port_forwarding(self):
        """
        :return: port forwarding state value
        :rtype: bool
        """
        return None

    @property
    def random_nat(self):
        """
        :return: random nat state value
        :rtype: bool
        """
        return None


class Settings:
    """Optional.

    If you would like to pass some specific settings for VPN
    configuration then you should derive from this class and override
    its methods.

    Usage:

    .. code-block::

        from proton.vpn.connection import Settings

        class VPNSettings(Settings):

            @property
            def dns_custom_ips(self):
                return ["192.12.2.1", "175.12.3.5"]

            @property
            def split_tunneling_ips(self):
                return ["182.24.1.3", "89.1.32.1"]

            @property
            def ipv6(self):
                return False

    Note: Not all fields are mandatory to override, only those that are
    actually needed, ie:

    .. code-block::

        from proton.vpn.connection import Settings

        class VPNSettings(Settings):

            @property
            def dns_custom_ips(self):
                return ["192.12.2.1", "175.12.3.5"]

    Passing only this is perfectly fine.
    """

    @property
    def dns_custom_ips(self) -> "List[str]":
        """Optional.

        :return: a list with alternative IPs for DNS queries
        :rtype: List[str]
        """
        return []

    @property
    def split_tunneling_ips(self) -> "List[str]":
        """Optional.

        :return: a list with IPs to exclude from VPN tunnel
        :rtype: List[str]
        """
        return []

    @property
    def ipv6(self) -> "bool":
        """Optional.

        :return: True if IPv6 should be enabled and False otherwise.
        :rtype: bool
        """
        return False

    @property
    def features(self) -> "Features":
        """Optional.

        :return: object with features
        :rtype: Features
        """
        return Features()
