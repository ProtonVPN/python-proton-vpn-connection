from abc import ABC, abstractmethod
from ..vpnconfig.abstract_vpnconfig import AbstractVPNConfiguration


class AbstractVPNConnection(ABC):
    @abstractmethod
    def up(self, vpnconfig: AbstractVPNConfiguration):
        pass

    @abstractmethod
    def down(self):
        pass
