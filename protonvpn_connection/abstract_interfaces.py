from abc import ABC


class AbstractVPNServer(ABC):
    """Abstract vpn server class.

    Mandatory properties are server_ip, domain,  tcp_ports and udp_ports being servername optional.
    If no servername is provided then the connection name will assume a default
    one provided by the system.
    """

    @property
    def server_ip(self):
        raise NotImplementedError

    @property
    def domain(self):
        raise NotImplementedError

    @property
    def tcp_ports(self):
        raise NotImplementedError

    @property
    def udp_ports(self):
        raise NotImplementedError

    @property
    def servername(self):
        return None


class AbstractVPNAccount(ABC):
    """Abstract vpn credentials.

    For credentials to be corrected fetched, the object being passed
    should have a method get_username_and_password() that return a named
    tuple. Usage example:
    .. ::

        user_pass_tuple = vpnaccount.get_username_and_password()
        username = user_pass_tuple.username
        username = user_pass_tuple.paswword

    A named tuple VPNUserPass is received with properties username and password.
    """

    def get_username_and_password(self):
        raise NotImplementedError
