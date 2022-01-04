from abc import ABC

class AbstractVPNConfiguration(ABC):

    def get_vpn_config_filepath(self, is_certificate: bool) -> str:
        """Get filepath to where the config was created."""
        pass

    def get_user_pass(self) -> tuple(str):
        """Get OpenVPN username and password for authentication"""
        pass

    def get_certificate(self) -> str:
        """Get certificate for certificate based authentication"""
        pass
