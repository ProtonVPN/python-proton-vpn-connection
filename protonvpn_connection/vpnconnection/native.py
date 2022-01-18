import os
import socket
import subprocess
import time
import select
import tempfile
import logging
import struct
import json
from .vpnconnection import VPNConnection

class NativeVPNConnectionFailed(Exception):
    pass

class ProtocolAdapter:
    message_header = struct.Struct('>H')

    _IS_LOG_LEVEL_TRACE_REGISTERED = False
    _LOG_LEVEL_TRACE = logging.DEBUG - 3

    @staticmethod
    def register_log_level_trace():
        # https://stackoverflow.com/questions/2183233/how-to-add-a-custom-loglevel-to-pythons-logging-facility

        if ProtocolAdapter._IS_LOG_LEVEL_TRACE_REGISTERED:
            return

        logging.addLevelName(ProtocolAdapter._LOG_LEVEL_TRACE, "TRACE")

        def _trace(self, message, *args, **kws):
            if self.isEnabledFor(ProtocolAdapter._LOG_LEVEL_TRACE):
                # Yes, logger takes its '*args' as 'args'.
                self._log(ProtocolAdapter._LOG_LEVEL_TRACE, message, args, **kws)

        logging.Logger.trace = _trace
        ProtocolAdapter._IS_LOG_LEVEL_TRACE_REGISTERED = True


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
        classes = [OpenVPN]

        for _class in classes:
            vpnconnection = _class.get_current_connection()
            if vpnconnection._get_protonvpn_connection():
                return vpnconnection
        return None

    @staticmethod
    def _priority():
        return 99

    def _setup(self):
        raise NotImplementedError

    def up(self):
        raise NotImplementedError

    def down(self):
        raise NotImplementedError


class NativeConnectionPropertiesName:
    NATIVE_PROPS_FILENAME = "native-connection-props.json"

class OpenVPN(NativeConnection):
    from proton.utils import ExecutionEnvironment
    NATIVE_PROPS_FILEPATH = os.path.join(ExecutionEnvironment().path_runtime,NativeConnectionPropertiesName.NATIVE_PROPS_FILENAME)

    @staticmethod
    def get_by_protocol(protocol: str):
        """Get VPN connection based on protocol."""
        if "tcp" in protocol:
            return OpenVPNTCP
        else:
            return OpenVPNUDP

    @staticmethod
    def _get_openvpn_path():
        return os.getenv("VPNCONNECTION_NATIVE_OPENVPN_PATH", "/usr/sbin/openvpn")

    def _debug(self, *args):
        self._logger.debug(*args)

    def _trace(self, *args):
        # trace() available thanks to ProtocolAdapter.register_log_level_trace()
        self._logger.trace(*args)

    def _read_input_mgmt_socket(self):
        if not self._mgmt_socket:
            self._open_mgmt_socket()
        while True:
            read_socket_list, _, _ = select.select([self._mgmt_socket], [], [], 0)
            if not read_socket_list:
                break
            for read_socket in read_socket_list:
                try:
                    b = read_socket.recv(2048)
                except:
                    self._trace("_read_input_mgmt_socket() : recv() raised exception => closing socket()")
                    self._close_mgmt_socket()
                    return
                # self._trace("_read_input_mgmt_socket() : read in management socket : {}".format(b))

                if not b:
                    self._trace("_read_input_mgmt_socket() : recv() returned b\'\' => closing socket()")
                    self._close_mgmt_socket()
                    return  # socket has shutdown
                # self._trace("_read_input_mgmt_socket() : recv() returned {}, buffer_last_read = {}".format(b, self._buffer_mgmt_last_read))
                if b != self._buffer_mgmt_last_read:
                    self._buffer_mgmt_socket.append(b)
                    self._trace("_read_input_mgmt_socket() : recv() returned {}, buffer_last_read = {} ; _buffer_mgmt_socket = \n{}".format(b, self._buffer_mgmt_last_read, b''.join(self._buffer_mgmt_socket).decode("utf-8")))
                self._buffer_mgmt_last_read = b

    def _open_mgmt_socket(self):
        self._trace("_open_mgmt_socket() : _management_socket_name = {}".format(self._management_socket_name))
        self._mgmt_socket = socket.socket(self._management_socket_family, socket.SOCK_STREAM)
        self._mgmt_socket.settimeout(0.5)
        try:
            self._mgmt_socket.connect(self._management_socket_name)
        except FileNotFoundError as e:
            raise NativeVPNConnectionFailed("{}: {}".format(type(e).__name__, e))
        self._buffer_mgmt_last_read = None

    def _close_mgmt_socket(self):
        if self._mgmt_socket:
            self._mgmt_socket.close()
            del self._mgmt_socket
            self._mgmt_socket = None

    def _write_to_mgmt_socket(self, line, flush=True):
        if not self._mgmt_socket:
            self._open_mgmt_socket()
        try:
            self._mgmt_socket.send(line)
        except BrokenPipeError:
            # openvpn mgmt socket is sometimes a bit stupid, let's try close and reopen
            self._close_mgmt_socket()
            self._open_mgmt_socket()
            self._mgmt_socket.send(line)
        if flush:
            self._read_input_mgmt_socket()

    @property
    def _flags(self):
        return [""]

    def _setup(self):
        from ..vpnconfiguration import OVPNFileConfig
        self._vpnconfig = OVPNFileConfig(self._vpnserver, self._vpnaccount, self._settings)
        self._vpnconfig.protocol = self.protocol
        self._create_cfg_file()
        self._requires_sudo = (os.getenv("VPNCONNECTIONNATIVE_SUDO_OPENVPN", "True").lower() == "true")
        ProtocolAdapter.register_log_level_trace()
        self._logger = logging.getLogger("NativeVPNConnection")
        self._buffer_mgmt_socket = []

    def _create_temporary_credential_file(self, username, password):
        self._temp_credentials_file = tempfile.NamedTemporaryFile(suffix=".tmp-credentials.txt")
        with open(self._temp_credentials_file.name, "w") as f:
            f.writelines([username + "\n", password + "\n"])

    def _get_credentials(self):
        user_data = self._vpnaccount.get_username_and_password()
        return user_data.username, user_data.password

    @property
    def _auth_using_credentials(self):
        return self._vpnconfig._is_certificate == False

    def _create_cfg_file(self):
        self._tmp_cfg_file = tempfile.NamedTemporaryFile(suffix=".tmp-config.ovpn")
        with open(self._tmp_cfg_file.name, "w") as f:
            print(self._vpnconfig.generate())
            f.write(self._vpnconfig.generate())

    def _write_props_file(self):
        properties={}
        with open(OpenVPN.NATIVE_PROPS_FILEPATH,'w') as f:
            properties['remote_ctrl_path']=self._management_socket_name
            json.dump(properties,f)

    def _read_props_file(self):
        print('reading props file')
        with open(OpenVPN.NATIVE_PROPS_FILEPATH,'r') as f:
            print('props file opened')
            data=json.load(f)
            print(data)
            self._management_socket_name=data['remote_ctrl_path']

    def _remove_props_file(self):
        os.unlink(OpenVPN.NATIVE_PROPS_FILEPATH)

    def _create_process(self):
        commands = []
        if self._requires_sudo:
            commands += ["sudo"]

        commands += [self._get_openvpn_path(), "--config", self._tmp_cfg_file.name ]
        # XXX This requires the resolvconf package to be installed
        # sudo apt install revolvconf
        commands+= ["--up", "/etc/openvpn/update-resolv-conf"]
        commands+= ["--down", "/etc/openvpn/update-resolv-conf"]
        commands+= ["--script-security", "2"]

        if self._auth_using_credentials:
            username, password = self._get_credentials()
            self._create_temporary_credential_file(username, password)
            commands += ["--auth-user-pass", self._temp_credentials_file.name]
        else:
            self._create_temporary_credential_file("", "")  # dummy file : management socket name is derived from credentials file name

        try:
            self._management_socket_family = socket.AF_UNIX  # will raise error if AF_UNIX not defined
            self._management_socket_name = self._temp_credentials_file.name + ".sock"
            commands += ["--management", self._management_socket_name, "unix", ]
        except AttributeError:
            # TODO : if the OS is not supporting AF_UNIX, we should create a tcp socket...
            # TODO : chose TCP port
            self._management_socket_name = ("127.0.0.1", 2999)
            self._management_socket_family = socket.AF_INET
            commands += ["--management", self._management_socket_name[0], str(self._management_socket_name[1]), ]

        self._debug("VPN command line = {} (flags {})".format(" ".join(commands), "+".join([""] + self._flags)))
        stdin = subprocess.DEVNULL
        stdout = subprocess.DEVNULL
        stderr = subprocess.DEVNULL
        if self._logger.level < logging.DEBUG:
            stdout = None
            stderr = None
        self._subprocess = subprocess.Popen(commands, stdin=stdin, stdout=stdout, stderr=stderr)
        timeout = 10
        time_begin = time.time()
        self._write_props_file()
        while True:
            try:
                self._open_mgmt_socket()
            except (FileNotFoundError, NativeVPNConnectionFailed):
                if time.time() - time_begin >= timeout:
                    raise TimeoutError("Timeout opening management socket ({} secs)".format(timeout))
                time.sleep(0.1)
                continue
            break

    def terminate_process(self, ignore_failure=False):
        if self._tmp_cfg_file:
            self._tmp_cfg_file.close()
        self._tmp_cfg_file = None



        self._debug("Gently asking OpenVPN to finish...")
        try:
            self._write_to_mgmt_socket(b'signal SIGTERM\r\n')
        except:
            if ignore_failure:
                pass
            else:
                raise

        #if no subprocess, just wait a bit
        if not self._subprocess:
            time.sleep(1)
            return

        timeout_terminate = 5
        time_begin = time.time()
        while True:
            status = self._subprocess.poll()
            if status is not None:
                break
            if time.time() - time_begin >= timeout_terminate:
                break
            time.sleep(0.1)
        if status is None:
            self._debug("Warning: OpenVPN process not ended (timeout {} s)...".format(timeout_terminate))
        else:
            self._debug("OpenVPN has finished")
        del self._subprocess
        self._subprocess = None
        self._management_socket_name = None
        self._mgmt_socket = None

    def _disconnect(self, ignore_failure=False):
        if self._temp_credentials_file:
            self._temp_credentials_file.close()
        self._temp_credentials_file = None
        self.terminate_process(ignore_failure=ignore_failure)
        self._remove_props_file()

    @staticmethod
    def get_current_connection():
        ovpnkind=OpenVPN.get_by_protocol('udp')
        print(f'Got a VPN Connection kind {ovpnkind}')
        res=ovpnkind(None,None)
        res._mgmt_socket=None
        res._buffer_mgmt_socket = []
        res._management_socket_family = socket.AF_UNIX
        ProtocolAdapter.register_log_level_trace()
        res._logger = logging.getLogger("NativeVPNConnection")
        res._temp_credentials_file=None
        res._tmp_cfg_file=None
        res._read_props_file()
        res._subprocess=None
        return res

    def _get_protonvpn_connection(self):
        return True


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

    def up(self):
        self._setup()
        self._create_process()

    def down(self):
        # FIXME : This doesn't work if the client code exited.
        # We need something like :
        # v=VPNConnection.get_current_connection()
        # v.down()
        self._disconnect()

class Wireguard(NativeConnection):
    """Creates a Wireguard connection."""
    protocol = "wg"

    def _setup(self):
        pass

    def up(self):
        pass

    def down(self):
        pass
