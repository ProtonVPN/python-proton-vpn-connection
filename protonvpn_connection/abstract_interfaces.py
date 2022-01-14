from abc import ABC
from typing import List


class AbstractVPNServer(ABC):
    """Abstract vpn server class.

    Mandatory properties are server_ip, domain,  tcp_ports and udp_ports being servername optional.
    If no servername is provided then the connection name will assume a default
    one provided by the system.
    """

    @property
    def server_ip(self):
        """
        :return: server ip to connect to
        :rtype: str
        """
        raise NotImplementedError

    @property
    def domain(self):
        """
        :return: domain for x509 verification
        :rtype: str
        """
        raise NotImplementedError

    @property
    def tcp_ports(self):
        """
        :return: list with tcp ports
        :rtype: [int]
        """
        raise NotImplementedError

    @property
    def udp_ports(self):
        """
        :return: list with udp ports
        :rtype: [int]
        """
        raise NotImplementedError

    @property
    def servername(self):
        """Optional.

        :return: human readeable value
        :rtype: str
        """
        return None


class AbstractVPNAccount(ABC):
    """Abstract vpn credentials.

    For credentials to be corrected fetched, the object being passed
    should have a method get_username_and_password() that return a named
    tuple. Usage example:
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
        raise NotImplementedError


class AbstractSettings(ABC):
    """Abstract settings.

    This is completly optional. If you would like to pass some specific settings for VPN
    configuration then you should follow this signature. Either create own class that provides the
    specified properties below or implement the abstract class directly and only
    override the necessary methods.
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

        :return: netshield configuration value. Incorrect values are ignored by the server
        :rtype: List[str]
        """
        return None
