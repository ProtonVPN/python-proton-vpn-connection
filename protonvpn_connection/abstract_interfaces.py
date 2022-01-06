from abc import ABC

"""
These classes can either be implemented or just used as a guide on which methods
should be available for VPNConnection to use. Any object that is passed to VPNConnection
should have these methods implemented, with certain exceptions which will be described in each class if
it has any.
"""


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


class AbstractVPNCredentials(ABC):
    """Abstract vpn credentials.

    For credentials to be corrected fetched, the object being passed
    should have a method get_username_password() that return a named
    tuple. Usage example:
    .. code-block::

        user_pass_tuple = vpncredentials.get_username_password()
        username = user_pass_tuple.username
        password = user_pass_tuple.password
    """

    @property
    def get_username_password(self):
        raise NotImplementedError
