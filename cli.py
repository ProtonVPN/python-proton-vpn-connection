import argparse
import sys
from typing import Tuple

from protonvpn_connection.vpnconfig import (AbstractVPNConfiguration,
                                            AbstractVPNCredentials)
from protonvpn_connection.vpnconnection.vpnconnection import VPNConnection


class Credentials(AbstractVPNCredentials):
    def get_certificate(self) -> str:
        """Get certificate for certificate based authentication"""
        return "Certificate"

    def get_user_pass(self) -> Tuple[str, ...]:
        """Get OpenVPN username and password for authentication"""
        return "user", "pass"


class VPNConfiguration(AbstractVPNConfiguration):

    def __init__(
        self, server_entry_ip, ports, vpnconnection_credentials,
        servername=None, domain=None, virtual_device_type=None, custom_dns_list=None,
        ):
        self._configfile = None
        self._server_entry_ip = server_entry_ip
        self._ports = ports
        self._virtual_device_type = virtual_device_type
        self._custom_dns_list = custom_dns_list
        self._domain = domain
        self._servername = servername
        self._vpnconnection_credentials = vpnconnection_credentials

    @property
    def device_name(self) -> str:
        return self.default_device_name if self._virtual_device_type is None else self._virtual_device_type

    @property
    def servername(self) -> str:
        return self._servername

    @property
    def vpn_credentials(self) -> AbstractVPNCredentials:
        return self._vpnconnection_credentials

    @property
    def protocol(self) -> str:
        raise NotImplementedError()

    def __enter__(self) -> str:
        return "filepath"

    def __exit__(self):
        print("delete filepath")


class OpenVPNUDPConfig(VPNConfiguration):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def protocol(self):
        return "udp"


class OpenVPNTCPConfig(VPNConfiguration):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def protocol(self):
        return "tcp"


class OpenVPNWGConfig(VPNConfiguration):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def protocol(self):
        return "wg"


class CLI:
    def __init__(self):
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("command", nargs="?")

        args = parser.parse_args(sys.argv[1:2])

        if not args.command or not hasattr(self, args.command):
            print("Either use \"connect\" or \"disconnect\"")
        else:
            getattr(self, args.command)()

    def connect(self):
        protocols = {
            "tcp": OpenVPNTCPConfig,
            "udp": OpenVPNUDPConfig,
            "wg": OpenVPNWGConfig,
        }

        parser = argparse.ArgumentParser(
            description="Connect to ProtonVPN", prog="protonvpn-cli c",
            add_help=False
        )
        parser.add_argument(
            "servername",
            nargs="?",
            help="Servername (CH#4, CH-US-1, HK5-Tor).",
            metavar=""
        )
        parser.add_argument(
            "-p", "--protocol", help="Connect via specified protocol.",
            choices=[
                "tcp",
                "udp",
                "wg",
            ], metavar="", type=str.lower, default="udp"
        )
        args = parser.parse_args(sys.argv[2:])

        if not args.servername:
            print("\nPlease provide a servername")
            sys.exit(1)

        print("Connecting with {} protocol to {}".format(args.protocol, args.servername))

        credentials = Credentials()

        vpnconfig = protocols[args.protocol]("192.168.0.1", [80, 88, 1143], credentials, args.servername)
        vpnconnection = VPNConnection()

        vpnconnection.up(vpnconfig)

    def disconnect(self):
        pass


CLI()
