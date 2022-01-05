from abc import ABC, abstractmethod, ABCMeta
from typing import Tuple

class AbstractVPNCredentials(ABC):

    @abstractmethod
    def get_certificate(self) -> str:
        """Get certificate for certificate based authentication"""
        raise NotImplementedError

    @abstractmethod
    def get_user_pass(self) -> Tuple[str, ...]:
        """Get OpenVPN username and password for authentication"""
        raise NotImplementedError


class AbstractVPNConfiguration(ABC):

    @property
    def default_device_name(self) -> str:
        return "proton0"

    @property
    def device_name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def servername(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def vpn_credentials(self) -> AbstractVPNCredentials:
        raise NotImplementedError

    @property
    @abstractmethod
    def protocol(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def __enter__(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def __exit__(self):
        raise NotImplementedError
