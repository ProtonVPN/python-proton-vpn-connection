"""
Exceptions raised by the VPN connection module.
"""


class VPNConnectionError(Exception):
    """Base class for VPN specific exceptions"""
    def __init__(self, message, additional_context=None):
        self.message = message
        self.additional_context = additional_context
        super().__init__(self.message)


class AuthenticationError(VPNConnectionError):
    """When server answers with auth_denied this exception is thrown.

    In many cases, an auth_denied can be thrown for multiple reasons, thus it's up to
    the user to decide how to proceed further.
    """


class ConnectionTimeoutError(VPNConnectionError):
    """When a connection takes too long to connect, this exception will be thrown."""


class MissingBackendDetails(VPNConnectionError):
    """When no VPN backend is found (NetworkManager, Native, etc) then this exception is thrown.

    In rare cases where it can happen that a user has some default packages installed, where the
    services for those packages are actually not running. Ie:
    NetworkManager is installed but not running and for some reason we can't access native backend,
    thus this exception is thrown as we can't do anything.
    """


class MissingProtocolDetails(VPNConnectionError):
    """
    When no VPN protocol is found (OpenVPN, Wireguard, IKEv2, etc) then this exception is thrown.
    """


class ConflictError(VPNConnectionError):
    """
    When attempting an up(), if for some reason another current connection is found,
    this exception thrown. Since no two simultaneous connections are allowed, the user of this
    componenet will have to first stop the current connection and then connect with a new one.

    Ideally this should be handled automatically by the state machine, but if for some reason
    a cleanup is not possible, then it should get detected on up().
    """


class UnexpectedError(VPNConnectionError):
    """For any unexpected or unhandled error this exception will be thrown."""
