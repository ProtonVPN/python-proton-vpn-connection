from abc import ABC, abstractmethod


class AbstractVPNConfiguration(ABC):

    @property
    def protocol(self) -> str:
        pass

    @abstractmethod
    def get_vpn_config_filepath(self, is_certificate: bool) -> str:
        """Get filepath to where the config was created."""
        pass

    @abstractmethod
    def get_user_pass(self) -> tuple(str):
        """Get OpenVPN username and password for authentication"""
        pass

    @abstractmethod
    def get_certificate(self) -> str:
        """Get certificate for certificate based authentication"""
        pass
