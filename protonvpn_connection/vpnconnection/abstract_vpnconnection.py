from abc import ABC, abstractmethod
from ..vpnconfig.abstract_vpnconfig import AbstractVPNConfiguration
from enum import Enum


class ProtocolEnum(Enum):
    OPENVPN = 0
    WIREGUARD = 1


class AbstractConnection(ABC):

    @abstractmethod
    def up(self, vpnconfig: AbstractVPNConfiguration):
        pass

    @abstractmethod
    def down(self):
        pass


class AbstractVPNConnection(AbstractConnection, ABC):
    pass
