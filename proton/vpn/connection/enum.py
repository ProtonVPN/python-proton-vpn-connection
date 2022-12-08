"""VPN connection enums."""

from enum import IntEnum


class ConnectionStateEnum(IntEnum):
    """VPN connection states."""
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2
    DISCONNECTING = 3
    ERROR = 4


class StateMachineEventEnum(IntEnum):
    """VPN connection events."""
    UP = 0
    DOWN = 1
    CONNECTED = 2
    DISCONNECTED = 3
    TIMEOUT = 4
    AUTH_DENIED = 5
    TUNNEL_SETUP_FAILED = 6
    RETRY = 7
    UNEXPECTED_ERROR = 8
    DEVICE_DISCONNECTED = 9
