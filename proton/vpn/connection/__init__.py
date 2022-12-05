"""
The public interface and the functionality that's common to all supported
VPN connection backends is defined in this module.
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("proton-vpn-connection")
except PackageNotFoundError:
    __version__ = "development"


# pylint: disable=wrong-import-position
from .vpnconnection import VPNConnection
from .interfaces import (
    Settings, VPNPubkeyCredentials, VPNServer,
    VPNUserPassCredentials, VPNCredentials
)

__all__ = [
    "VPNConnection", "Settings", "VPNPubkeyCredentials",
    "VPNServer", "VPNUserPassCredentials", "VPNCredentials"
]
