from abc import ABC, abstractmethod

from .abstract_vpnconnection import (NativeOpenVPNCertificate,
                                     NativeOpenVPNUserPass, NativeWireguard,
                                     NetworkManagerWireguard,
                                     NetworkMangerOpenVPNCertificate,
                                     NetworkMangerOpenVPNUserPass)


class AbstractConnectionFactory(ABC):

    @abstractmethod
    def openvpn_certificate_based(self):
        pass

    @abstractmethod
    def openvpn_user_pass_based(self):
        pass

    @abstractmethod
    def wireguard_certificate_based(self):
        pass


class NetworkManagerConnectionFactory(AbstractConnectionFactory):

    def openvpn_certificate_based(self):
        return NetworkMangerOpenVPNCertificate

    def openvpn_user_pass_based(self):
        return NetworkMangerOpenVPNUserPass

    def wireguard_certificate_based(self):
        return NetworkManagerWireguard


class NativeConnectionFactory(AbstractConnectionFactory):

    def openvpn_certificate_based(self):
        return NativeOpenVPNCertificate

    def openvpn_user_pass_based(self):
        return NativeOpenVPNUserPass

    def wireguard_certificate_based(self):
        return NativeWireguard
