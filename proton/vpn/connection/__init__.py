from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("proton-vpn-connection")
except PackageNotFoundError:
    __version__ = "development"


from .vpnconnection import VPNConnection
from .interfaces import (
    Settings, VPNPubkeyCredentials, VPNServer,
    VPNUserPassCredentials, VPNCredentials
)

__all__ = [
    "VPNConnection", "Settings", "VPNPubkeyCredentials",
    "VPNServer", "VPNUserPassCredentials", "VPNCredentials"
]
