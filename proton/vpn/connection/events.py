"""
VPN connection events to react to.
"""
from __future__ import annotations
from typing import Any

from .enum import StateMachineEventEnum


# pylint: disable=too-few-public-methods


class BaseEvent:
    """Skeleton event that all the other events should inherit from."""
    event = None
    error_occurred = False

    def __init__(self, context: Any = None):
        if self.event is None:
            raise AttributeError("event attribute not defined")

        self.context = context


class Up(BaseEvent):
    """Signals that the VPN connection should be started."""
    event = StateMachineEventEnum.UP


class Down(BaseEvent):
    """Signals that the VPN connection should be stopped."""
    event = StateMachineEventEnum.DOWN


class Connected(BaseEvent):
    """Signals that the VPN connection was successfully established."""
    event = StateMachineEventEnum.CONNECTED


class Disconnected(BaseEvent):
    """Signals that the VPN connection was successfully disconnected by the user."""
    event = StateMachineEventEnum.DISCONNECTED


class Error(BaseEvent):
    """Parent class for events signaling VPN disconnection."""


class DeviceDisconnected(Error):
    """Signals that the VPN connection dropped unintentionally."""
    event = StateMachineEventEnum.DEVICE_DISCONNECTED


class Timeout(Error):
    """Signals that a timeout occurred while trying to establish the VPN
    connection."""
    event = StateMachineEventEnum.TIMEOUT


class AuthDenied(Error):
    """Signals that an authentication denied occurred while trying to establish
    the VPN connection."""
    event = StateMachineEventEnum.AUTH_DENIED


class TunnelSetupFailed(Error):
    """Signals that there was an error setting up the VPN tunnel."""
    event = StateMachineEventEnum.TUNNEL_SETUP_FAILED


class UnexpectedError(Error):
    """Signals that an unexpected error occurred."""
    event = StateMachineEventEnum.UNEXPECTED_ERROR


class Retry(BaseEvent):
    """Signals that a connection retry is required."""
    event = StateMachineEventEnum.RETRY


_event_types = [
    event_type for event_type in BaseEvent.__subclasses__()
    if event_type is not Error  # As error is an abstract class.
]
_event_types.extend(Error.__subclasses__())
EVENT_TYPES = tuple(_event_types)
