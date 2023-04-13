"""VPN connection enums.


Copyright (c) 2023 Proton AG

This file is part of Proton VPN.

Proton VPN is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Proton VPN is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with ProtonVPN.  If not, see <https://www.gnu.org/licenses/>.
"""

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
