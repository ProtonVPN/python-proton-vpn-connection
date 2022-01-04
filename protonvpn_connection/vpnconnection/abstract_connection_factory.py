from abc import ABC, abstractmethod
from .abstract_vpnconnection import AbstractVPNConnection


class AbstractConnectionFactory(ABC):

    @abstractmethod
    def openvpn_certificate_based(self) -> AbstractVPNConnection:
        pass

    @abstractmethod
    def openvpn_user_pass_based(self) -> AbstractVPNConnection:
        pass

    @abstractmethod
    def wireguard_certificate_based(self) -> AbstractVPNConnection:
        pass
