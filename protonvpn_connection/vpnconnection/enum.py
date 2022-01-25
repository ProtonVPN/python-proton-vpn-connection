from enum import Enum


class ConnectionStateEnum(Enum):
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2
    TRANSCIENT_ERROR = 3
    DISCONNECTING = 4
