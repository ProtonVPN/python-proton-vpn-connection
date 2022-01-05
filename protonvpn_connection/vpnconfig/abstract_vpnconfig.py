from abc import ABC, abstractmethod


class AbstractVPNCredentials(ABC):

    @abstractmethod
    def get_certificate(self) -> str:
        """Get certificate for certificate based authentication"""
        pass

    @abstractmethod
    def get_user_pass(self) -> tuple(str):
        """Get OpenVPN username and password for authentication"""
        pass


class AbstractVPNConfiguration(ABC):

    @property
    @abstractmethod
    def servername(self) -> str:
        pass

    @property
    @abstractmethod
    def vpn_credentials(self) -> AbstractVPNCredentials:
        pass

    @property
    @abstractmethod
    def protocol(self) -> str:
        pass

    @abstractmethod
    def __enter__(self) -> str:
        pass

    @abstractmethod
    def __exit__(self):
        pass
