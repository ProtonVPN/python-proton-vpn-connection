from protonvpn_connection.vpnconnection import VPNConnection


class VPNServer:
    @property
    def server_ip(self):
        return "195.158.248.226"

    @property
    def domain(self):
        return "node-pt-02b.protonvpn.net"

    @property
    def tcp_ports(self):
        return [443, 5995, 8443]

    @property
    def udp_ports(self):
        return [5060, 1194, 4569, 443, 80]

    @property
    def servername(self):
        """Optional.

        :return: human readeable value
        :rtype: str
        """
        return "PT#10"


class UserPass:

    @property
    def username(self):
        return "2faEOAZxA5nP1xV827-HbRRG"

    @property
    def password(self):
        return "4iwP/sD+WvFHoU4I3lFQm38j"


class VPNAccount:
    def get_username_and_password(self):
        return UserPass()

    def get_client_private_wg_key(self):
        return "wg_private_key"

    def get_client_private_openvpn_key(self):
        return "openvpn_private_key"

    def get_client_api_pem_certificate(self):
        return "certificate"


# vpnconnection = VPNConnection.get_from_factory(protocol="openvpn_tcp")
# vpnconnection = vpnconnection(VPNServer(), VPNAccount())

# vpnconnection.up()

vpnconnection = VPNConnection.get_current_connection()
print(vpnconnection)
if vpnconnection:
    vpnconnection.down()
