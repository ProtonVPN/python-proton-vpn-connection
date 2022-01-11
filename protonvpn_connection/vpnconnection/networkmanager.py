
class NMVPNConnection(VPNConnection):
    """Returns VPN connections based on Network Manager implementation.

    This is the default backend that will be returned. See docstring for
    VPNConnection.get_vpnconnection() for further explanation on how priorities work.

    A NMVPNConnection can return a VPNConnection based on protocols such as OpenVPN, IKEv2 or Wireguard.
    """
    implementation = "networkmanager"

    @classmethod
    def get_connection(cls, protocol: str = None, usersettings: object = None):
        """Get VPN connection.

        The type of procotol returned here is based on some conditions, and these conditions are:
        - If only the protocol has been passed, then it should return the respective
          connection based on the desired protocol
        - If only usersettings has been passed, it has to be checked if smart_routing is enabled
          or not. If yes the follow the logic for smart routing, if not then user protocol
          is selected from usersettings.
        - If both are passed then protocol takes always precedence.
        - If none are passed, then a custom logic takes precedence [TBD].
        """
        pass

    def _priority(cls):
        return 100

    def _setup(self):
        raise NotImplementedError

    def up(self):
        raise NotImplementedError

    def down(self):
        raise NotImplementedError


class OpenVPN(NMVPNConnection):
    def get_openvpnconnection(self, protocol: str):
        """Get VPN connection based on protocol."""
        pass


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


class Wireguard(NMVPNConnection):
    """Creates a Wireguard connection."""
    protocol = "wg"

    def _setup(self):
        pass

    def up(self):
        pass

    def down(self):
        pass