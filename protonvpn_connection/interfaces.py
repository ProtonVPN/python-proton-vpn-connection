from typing import List


class VPNServer:
    """
    A VPN server is needed to be able to get the neccessary data about the server to connect to.
    Most of the properties are mandatory as they contain crucial information for connection establishment.

    Usage:
    ::
        from protonvpn_connection.interfaces import VPNServer

        class MyVPNServer(VPNServer):

            @property
            def server_ip(self):
                return "187.135.1.53"

            @property
            def domain(self):
                return "org.my-secure-domain.com"

            @property
            def wg_public_key_x25519(self):
                return "50A864D6C91158719A14040787F0177E968E606DB669DC37359F42E36853085C"

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
    def server_ip(self) -> str:
        """
        :return: server ip to connect to
        :rtype: str
        """
        raise NotImplementedError

    @property
    def domain(self) -> str:
        """
        :return: domain to be used for x509 verification
        :rtype: str
        """
        raise NotImplementedError

    @property
    def wg_public_key_x25519(self) -> str:
        """
        :return: x25519 public key for wg peer verification
        :rtype: str
        """
        raise NotImplementedError

    @property
    def tcp_ports(self) -> List[int]:
        """
        :return: list with tcp ports
        :rtype: List[int]
        """
        raise NotImplementedError

    @property
    def udp_ports(self) -> List[int]:
        """
        :return: list with udp ports
        :rtype: List[int]
        """
        raise NotImplementedError

    @property
    def servername(self) -> str:
        """Optional.

        :return: human readeable servername
        :rtype: str
        """
        return None


class VPNAccount:
    """
    # TO-DO: FIX VPN ACCOUNT INTERFACE, NAME AND DOC

    For VPN connection to be established, credentials are 
    Usage example:
    ::

        user_pass_tuple = vpnaccount.get_username_and_password()
        username = user_pass_tuple.username
        username = user_pass_tuple.paswword

    A named tuple VPNUserPass is received with properties username and password.
    """

    def get_username_and_password(self):
        """
        :return: named tuple
        :rtype: namedtuple(username, password)
        """
        return None

    def get_client_private_wg_key(self):
        return None

    def get_client_private_openvpn_key(self):
        return None

    def get_client_api_pem_certificate(self):
        return None


class Settings:
    """Optional.

    If you would like to pass some specific settings for VPN
    configuration then you should derive from this class and override its methods.

    Usage:
    ::
        from protonvpn_connection.interfaces import Settings

        class VPNSettings(Settings):

            @property
            def dns_custom_ips(self):
                return ["192.12.2.1", "175.12.3.5"]

            @property
            def split_tunneling_ips(self):
                return ["182.24.1.3", "89.1.32.1"]

            @property
            def netshield(self):
                return "f0"

            @property
            def disable_ipv6(self):
                return False

    Note: Not all fields are mandatory to override, only those that are actually needed, ie:
    ::
        from protonvpn_connection.interfaces import Settings

        class VPNSettings(Settings):

            @property
            def dns_custom_ips(self):
                return ["192.12.2.1", "175.12.3.5"]

    Passing only this is perfectly fine.
    """
    @property
    def dns_custom_ips(self) -> List[str]:
        """Optional.

        :return: a list with alternative IPs for DNS queries
        :rtype: List[str]
        """
        return []

    @property
    def split_tunneling_ips(self) -> List[str]:
        """Optional.

        :return: a list with IPs to exclude from VPN tunnel
        :rtype: List[str]
        """
        return []

    @property
    def netshield(self) -> str:
        """Optional.

        :return: the value of netshield in string format. Can either be `f0`, `f1` or `f2`
        :rtype: str
        """
        return ""

    @property
    def disable_ipv6(self) -> bool:
        """Optional.

        :return: if ipv6 should be disabled
        :rtype: bool
        """
        return False
