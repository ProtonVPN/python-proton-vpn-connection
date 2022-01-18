from .vpnconnection import VPNConnection


class NativeConnection(VPNConnection):
    """Dummy class to emulate native implementation"""
    implementation = "native"

    @classmethod
    def factory(cls, protocol: str = None):
        """Get VPN connection.

        The type of procotol returned.
        """
        if "openvpn" in protocol:
            return OpenVPN.get_by_protocol(protocol)
        elif "wireguard" in protocol:
            return Wireguard

    @classmethod
    def _get_connection(cls):
        return None

    @staticmethod
    def _priority():
        return 101

    def _setup(self):
        raise NotImplementedError

    def up(self):
        raise NotImplementedError

    def down(self):
        raise NotImplementedError


class OpenVPN(NativeConnection):

    @staticmethod
    def get_by_protocol(protocol: str):
        """Get VPN connection based on protocol."""
        if "tcp" in protocol:
            return OpenVPNTCP
        else:
            return OpenVPNUDP


class OpenVPNTCP(OpenVPN):
    """Creates a OpenVPNTCP connection."""
    protocol = "tcp"

    def _setup(self):
        pass

    def up(self):
        pass

    def down(self):
        pass


class OpenVPNUDP(OpenVPN):
    """Creates a OpenVPNUDP connection."""
    protocol = "udp"

    def _setup(self):
        pass

    def up(self):
        pass

    def down(self):
        pass


class Wireguard(NativeConnection):
    """Creates a Wireguard connection."""
    protocol = "wg"

    def _setup(self):
        pass

    def up(self):
        pass

    def down(self):
        pass
