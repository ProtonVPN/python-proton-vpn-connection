"""VPN connection enums."""

from enum import IntEnum


class ConnectionStateEnum(IntEnum):
    """VPN connection states."""
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2
    TRANSIENT_ERROR = 3
    DISCONNECTING = 4
    ERROR = 5


class StateMachineEventEnum(IntEnum):
    """VPN connection events."""
    UP = 0
    DOWN = 1
    CONNECTED = 2
    DISCONNECTED = 3
    TIMEOUT = 4
    AUTH_DENIED = 5
    TUNNEL_SETUP_FAIL = 6
    RETRY = 7
    UNKNOWN_ERROR = 8
