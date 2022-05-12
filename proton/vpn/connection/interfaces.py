from typing import List, NamedTuple, Optional


class VPNServer:
    """
    A VPN server is needed to be able to get the neccessary data about the server to connect to.
    Most of the properties are mandatory as they contain crucial information for connection establishment.

    Usage:

    .. code-block::

        from proton.vpn.connection import VPNServer

        class MyVPNServer(VPNServer):

            @property
            def server_ip(self):
                return "187.135.1.53"

            @property
            def domain(self):
                return "org.my-secure-domain.com"

            @property
            def wg_public_key_x25519(self):
                return "wOnn8kz6l6l3Tbwi7F7rvg/iyFB9yQneYETbp4xMJF0="

            @property
            def tcp_ports(self):
                return [443, 5995]

            @property
            def udp_ports(self):
                return [80, 443, 5060]

    Note:
        1. Since `servername` is optional, it has been ommited.
        2. If you intend to connect via a non-wireguard protocol then `wg_public_key_x25519`
           can just return `None` as it won't be used, as this is specific to the wireguard protocol.

    """

    @property
    def server_ip(self) -> "str":
        """
        :return: server ip to connect to
        :rtype: str
        """
        raise NotImplementedError

    @property
    def domain(self) -> "str":
        """
        :return: domain to be used for x509 verification
        :rtype: str
        """
        raise NotImplementedError

    @property
    def wg_public_key_x25519(self) -> "str":
        """
        :return: x25519 public key for wg peer verification
        :rtype: str
        """
        raise NotImplementedError

    @property
    def tcp_ports(self) -> "List[int]":
        """
        :return: list with tcp ports
        :rtype: List[int]
        """
        raise NotImplementedError

    @property
    def udp_ports(self) -> "List[int]":
        """
        :return: list with udp ports
        :rtype: List[int]
        """
        raise NotImplementedError

    @property
    def servername(self) -> "str":
        """Optional.

        :return: human readeable servername
        :rtype: str
        """
        return None


class VPNPubkeyCredentials:
    """
    Object that gets certificates and privates keys
    for certificate based connections.

    An instance of this class is to be passed to VPNCredentials.

    Usage:

    .. code-block::

        from proton.vpn.connection import VPNPubkeyCredentials

        class MyVPNPubkeyCredentials(VPNPubkeyCredentials):

            @property
            def certificate_pem(self):
                return "-----BEGIN CERTIFICATE-----\\nMIICJjCCAdigAwIBAgIECTD...=\\n-----END CERTIFICATE-----\\n"

            @property
            def wg_privage_key(self):
                return "wOnn8kz6l6l3Tbwi7F7rvg/iyFB9yQneYETbp4xMJF0="

            @property
            def openvpn_private_key(self):
                return "-----BEGIN PRIVATE KEY-----\\nMC4CAQAwBQYDK2VwBCIEIKzVt3S+Q...\\n-----END PRIVATE KEY-----\\n"
    """

    @property
    def certificate_pem(self) -> "str":
        """
        :return: X509 client certificate in PEM format
        :rtype: str
        """
        raise NotImplementedError

    @property
    def wg_private_key(self) -> "str":
        """
        :return: Wireguard private key in base64 format
        :rtype: str
        """
        raise NotImplementedError

    @property
    def openvpn_private_key(self) -> "str":
        """
        :return: OpenVPN private key in PEM format
        :rtype: str
        """
        raise NotImplementedError


class VPNUserPassCredentials:
    """Provides username and password for username/password VPN authentication.

    Usage:

    .. code-block::

        from proton.vpn.connection import VPNUserPassCredentials

        class MyVPNUserPassCredentials(VPNUserPassCredentials):

            @property
            def username(self):
                return "my-openvpn/ikev2-username"

            @property
            def password(self):
                return "my-openvpn/ikev2-password"

    """

    @property
    def username(self) -> "str":
        raise NotImplementedError

    @property
    def password(self) -> "str":
        raise NotImplementedError


class VPNCredentials:
    """
    For VPN connection to be established, credentials are needed.
    Depending of how these credentials are used, one method or the other may be
    irrelevant.

    Usage:

    .. code-block::

        class MyVPNCredentials:

            def userpass_credentials(self):
                # See how you can create a VPNUserPass object at `VPNUserPassCredentials`
                return VPNUserPassCredentials

            def pubkey_credentials(self):
                # See how you can create a VPNCertificate object at `VPNPubkeyCredentials`
                return VPNPubkeyCredentials

    Limitation:
    You could define only userpass_credentials, though at the cost that you won't be able
    to connect to wireguard (since it's based on certificates) and/or openvpn and ikev2 based
    with certificates. To guarantee maximum compatibility, it is recommended to pass both objects
    for username/password and certificates.
    """

    @property
    def pubkey_credentials(self) -> "Optional[VPNPubkeyCredentials]":
        """
        :return: instance of VPNPubkeyCredentials, which allows to make connections
            with certificates
        :rtype: VPNPubkeyCredentials
        """
        raise NotImplementedError

    @property
    def userpass_credentials(self) -> "Optional[VPNUserPassCredentials]":
        """
        :return: instance of VPNUserPassCredentials, which allows to make connections
            with user/password
        :rtype: VPNUserPassCredentials
        """
        raise NotImplementedError


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

            @property
            def safe_mode(self):
                return True

    Note: Not all fields are mandatory to override, only those that are actually needed, ie:
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

    @property
    def safe_mode(self):
        """
        :return: safe mode state value
        :rtype: bool
        """
        return None


class Settings:
    """Optional.

    If you would like to pass some specific settings for VPN
    configuration then you should derive from this class and override its methods.

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
            def disable_ipv6(self):
                return False

    Note: Not all fields are mandatory to override, only those that are actually needed, ie:

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
