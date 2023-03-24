"""
VPN connection events to react to.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING, Optional

from .enum import StateMachineEventEnum

if TYPE_CHECKING:
    from proton.vpn.connection.vpnconnection import VPNConnection


# pylint: disable=too-few-public-methods

@dataclass
class EventContext:
    """
    Relevant event context.

    It should always contain the VPN connection that emitted the event.
    """

    connection: "VPNConnection"
    error: Optional[Any] = None


class Event:
    """Base event that all the other events should inherit from."""
    type = None

    def __init__(self, context: EventContext):
        if self.type is None:
            raise AttributeError("event attribute not defined")

        self.context = context


class Up(Event):
    """Signals that the VPN connection should be started."""
    type = StateMachineEventEnum.UP


class Down(Event):
    """Signals that the VPN connection should be stopped."""
    type = StateMachineEventEnum.DOWN


class Connected(Event):
    """Signals that the VPN connection was successfully established."""
    type = StateMachineEventEnum.CONNECTED


class Disconnected(Event):
    """Signals that the VPN connection was successfully disconnected by the user."""
    type = StateMachineEventEnum.DISCONNECTED


class Error(Event):
    """Parent class for events signaling VPN disconnection."""


class DeviceDisconnected(Error):
    """Signals that the VPN connection dropped unintentionally."""
    type = StateMachineEventEnum.DEVICE_DISCONNECTED


class Timeout(Error):
    """Signals that a timeout occurred while trying to establish the VPN
    connection."""
    type = StateMachineEventEnum.TIMEOUT


class AuthDenied(Error):
    """Signals that an authentication denied occurred while trying to establish
    the VPN connection."""
    type = StateMachineEventEnum.AUTH_DENIED


class TunnelSetupFailed(Error):
    """Signals that there was an error setting up the VPN tunnel."""
    type = StateMachineEventEnum.TUNNEL_SETUP_FAILED


class UnexpectedError(Error):
    """Signals that an unexpected error occurred."""
    type = StateMachineEventEnum.UNEXPECTED_ERROR


_event_types = [
    event_type for event_type in Event.__subclasses__()
    if event_type is not Error  # As error is an abstract class.
]
_event_types.extend(Error.__subclasses__())
EVENT_TYPES = tuple(_event_types)
