from enum import Enum


class ConnectionStateEnum(Enum):
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2
    TRANSCIENT_ERROR = 3
    DISCONNECTING = 4
    ERROR = 5


class StateMachineEventEnum(Enum):
    UP = 0
    DOWN = 1
    CONNECTED = 2
    DISCONNECTED = 3
    TIMEOUT = 4
    AUTH_DENIED = 5
    UNKOWN_ERROR = 6
