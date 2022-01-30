import os
import os.path
import socket
import subprocess
import time
import select
import tempfile
import logging
import struct
import json
from .vpnconnection import VPNConnection
from .exceptions import ConnectionTimeoutError


class MGMTSocketNotFoundError(Exception):
    pass

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
    backend = "native"

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
        classes = [OpenVPN,Wireguard]

        for _class in classes:
            vpnconnection = _class.get_current_connection()
            if vpnconnection._get_protonvpn_connection():
                return vpnconnection
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
            raise MGMTSocketNotFoundError("{}: {}".format(type(e).__name__, e))
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
        from .vpnconfiguration import VPNConfiguration
        vpnconfig = VPNConfiguration.from_factory(self.protocol)
        self._vpnconfig = vpnconfig(self._vpnserver, self._vpncredentials, self._settings)
        self._vpnconfig.use_certificate = self._use_certificate
        self._create_cfg_file()
        self._requires_sudo = (os.getenv("VPNCONNECTIONNATIVE_SUDO_OPENVPN", "True").lower() == "true")
        ProtocolAdapter.register_log_level_trace()
        self._logger = logging.getLogger("NativeVPNConnection")
        self._buffer_mgmt_socket = []
        self._connect_timeout=10
        self._logger.level= logging.DEBUG -3

    def _create_temporary_credential_file(self, username, password):
        self._temp_credentials_file = tempfile.NamedTemporaryFile(suffix=".tmp-credentials.txt")
        with open(self._temp_credentials_file.name, "w") as f:
            f.writelines([username + "\n", password + "\n"])

    @property
    def _auth_using_credentials(self):
        return self._use_certificate == False

    def _create_cfg_file(self):
        self._tmp_cfg_file = tempfile.NamedTemporaryFile(suffix=".tmp-config.ovpn")
        with open(self._tmp_cfg_file.name, "w") as f:
            f.write(self._vpnconfig.generate())

    def _write_props_file(self):
        properties={}
        with open(OpenVPN.NATIVE_PROPS_FILEPATH,'w') as f:
            properties['remote_ctrl_path']=self._management_socket_name
            json.dump(properties,f)

    def _read_props_file(self):
        with open(OpenVPN.NATIVE_PROPS_FILEPATH,'r') as f:
            data=json.load(f)
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
        if os.path.exists("/etc/openvpn/update-resolv-conf"):
            commands+= ["--up", "/etc/openvpn/update-resolv-conf"]
            commands+= ["--down", "/etc/openvpn/update-resolv-conf"]
            commands+= ["--script-security", "2"]

        if self._auth_using_credentials:
            username, password = self._get_user_pass()
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
            except (FileNotFoundError, MGMTSocketNotFoundError):
                if time.time() - time_begin >= timeout:
                    raise ConnectionTimeoutError("Timeout opening management socket ({} secs)".format(timeout))
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
            if not ignore_failure:
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
        res=ovpnkind(None,None)
        res._mgmt_socket=None
        res._buffer_mgmt_socket = []
        res._management_socket_family = socket.AF_UNIX
        ProtocolAdapter.register_log_level_trace()
        res._logger = logging.getLogger("NativeVPNConnection")
        res._temp_credentials_file=None
        res._tmp_cfg_file=None
        try:
            res._read_props_file()
            res._connection_found=True
        except:
            res._connection_found=False
        res._subprocess=None
        return res

    def _get_protonvpn_connection(self):
        return self._connection_found

    def _get_state(self, ask_for_state):
        if self._subprocess.poll() is not None:
            raise NativeVPNConnectionFailed("openvpn subprocess has finished with returncode = {}".format(self._subprocess.returncode))
        if ask_for_state:
            self._trace("writing to mgmt socket : {}".format(b'state\n'))
            self._write_to_mgmt_socket(b'state\n', flush=False)
        timeout = 0.5
        time_begin = time.time()
        while True:
            if ask_for_state:
                self._read_input_mgmt_socket()
            if not self._buffer_mgmt_socket:
                self._trace("_get_state() : _read_input_mgmt_socket() finished ; _buffer_mgmt_socket = {} => quiting".format(self._buffer_mgmt_socket))
                return None
            buffer_utf8 = b''.join(self._buffer_mgmt_socket).decode("utf-8")
            # self._trace("Read from mgmt socket :\n{}".format(buffer_utf8))
            lines = buffer_utf8.split('\r\n')
            # self._trace("Lines from mgmt socket :\n{}".format(lines))
            all_blocks = []
            current_block = []
            for line in lines:
                current_block.append(line)
                if line.strip() == "END":
                    all_blocks.append(current_block)
                    current_block = []

            state = None
            for block in all_blocks:
                reached_end_of_state = False
                block_state = None
                for line in block:
                    if not line:
                        continue
                    if line.strip() == "END":
                        # self._trace("   Found 'END' from management socket output ; state = {}".format(block_state))
                        reached_end_of_state = True
                        break
                    tokens = line.split(",")
                    if len(tokens) >= 4:
                        # at least 4 comma-separated parameters : https://openvpn.net/community-resources/management-interface/
                        try:
                            _ = int(tokens[0])  # check 1st token is a unix timestamp
                            state = tokens
                        except:
                            pass
                if reached_end_of_state:
                    if block_state:
                        state = block_state
                    # self._trace("    Read 'END' from management socket output")

            if state:
                self._trace("Found state in management socket : state = {}".format(state))
                break

            if time.time() - time_begin >= timeout:
                self._trace("Not read 'END' from management socket output ; timeout : {} seconds ...")
                raise TimeoutError("Not read 'END' from management buffer")
            if not ask_for_state:
                self._trace("Not read 'END' from management socket output ; ask_for_state = {} : break".format(ask_for_state))
                break
            time.sleep(0.2)
            # self._trace("Not read 'END' from management socket output ; keep going...")

        return state

    @staticmethod
    def _is_state_connected(state):
        return state and state[1] == "CONNECTED"


    def _waitstatus(self):
        self._debug("Waiting VPN connection to be established...")
        time_begin = time.time()
        self._buffer_mgmt_socket = []
        while True:
            current_state = self._get_state(ask_for_state=True)
            if self._is_state_connected(current_state):
                break
            self._trace("Waiting VPN connection to be established : current_state = {}...".format(current_state))
            if time.time() - time_begin >= self._connect_timeout:
                self._debug("Timeout establishing VPN connection ({} secs) : current_state = {}".format(self._connect_timeout, current_state))
                raise TimeoutError("Timeout establishing VPN connection ({} secs)".format(self._connect_timeout))
            time.sleep(0.5)
        self._debug("        VPN connection       established : current_state = {}...".format(current_state))


class OpenVPNTCP(OpenVPN):
    """Creates a OpenVPNTCP connection."""
    protocol = "openvpn_tcp"

    def up(self):
        self._setup()
        self._create_process()
        self._waitstatus()

    def down(self):
        self._disconnect()


class OpenVPNUDP(OpenVPN):
    """Creates a OpenVPNUDP connection."""
    protocol = "openvpn_udp"

    def up(self):
        self._setup()
        self._create_process()

    def down(self):
        self._disconnect()

class WGNativeConnectionPropertiesName:
    NATIVE_PROPS_FILENAME = "wg-native-connection-props.json"

class Wireguard(NativeConnection):
    from proton.utils import ExecutionEnvironment
    NATIVE_PROPS_FILEPATH = os.path.join(ExecutionEnvironment().path_runtime,WGNativeConnectionPropertiesName.NATIVE_PROPS_FILENAME)

    """Creates a Wireguard connection."""
    protocol = "wireguard"

    @staticmethod
    def _get_wg_quick_path():
        paths_to_try=["/usr/bin/wg-quick", "/usr/local/bin/wg-quick"]
        for path in paths_to_try:
            if os.path.exists(path):
                return path
        return os.getenv("VPNCONNECTION_NATIVE_WGQUICK_PATH")

    def _setup(self):
        from .vpnconfiguration import VPNConfiguration
        vpnconfig = VPNConfiguration.from_factory(self.protocol)
        self._vpnconfig = vpnconfig(self._vpnserver, self._vpncredentials, self._settings)
        self._create_cfg_file()
        self._requires_sudo = (os.getenv("VPNCONNECTIONNATIVE_SUDO_WG", "True").lower() == "true")
        ProtocolAdapter.register_log_level_trace()
        self._logger = logging.getLogger("NativeVPNConnection")

    def _create_cfg_file(self):
        self._tmp_cfg_file = tempfile.NamedTemporaryFile(suffix=".conf")
        self._wgconfig_filename = self._tmp_cfg_file.name
        with open(self._tmp_cfg_file.name, "w") as f:
            print(self._vpnconfig.generate())
            f.write(self._vpnconfig.generate())

    def _create_process(self):
        commands = []
        if self._requires_sudo:
            commands += ["sudo"]
        commands += [self._get_wg_quick_path(), "up", self._tmp_cfg_file.name ]
        stdin = subprocess.DEVNULL
        stdout = subprocess.DEVNULL
        stderr = subprocess.DEVNULL
        if self._logger.level < logging.DEBUG:
            stdout = None
            stderr = None
        self._subprocess = subprocess.Popen(commands, stdin=stdin, stdout=stdout, stderr=stderr)
        self._write_props_file()
        self._subprocess.communicate(timeout=10)

    def _write_props_file(self):
        properties={}
        with open(Wireguard.NATIVE_PROPS_FILEPATH,'w') as f:
            properties['configuration_name']=self._wgconfig_filename
            json.dump(properties,f)

    def _read_props_file(self):
        with open(Wireguard.NATIVE_PROPS_FILEPATH,'r') as f:
            data=json.load(f)
            self._wgconfig_filename=data['configuration_name']

    def _remove_props_file(self):
        os.unlink(Wireguard.NATIVE_PROPS_FILEPATH)

    def _wgquickdown(self):
        commands = []
        if self._requires_sudo:
            commands += ["sudo"]
        conf_name=os.path.join(tempfile.gettempdir(),self._wgconfig_filename)
        with open(conf_name,'w') as f:
            commands += [self._get_wg_quick_path(), "down", conf_name ]
            stdin = subprocess.DEVNULL
            stdout = subprocess.DEVNULL
            stderr = subprocess.DEVNULL
            if self._logger.level < logging.DEBUG:
                stdout = None
                stderr = None
            self._subprocess = subprocess.Popen(commands, stdin=stdin, stdout=stdout, stderr=stderr)

    def terminate_process(self, ignore_failure=False):
        if self._tmp_cfg_file:
            self._tmp_cfg_file.close()
        self._tmp_cfg_file = None

        self._wgquickdown()

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

        del self._subprocess
        self._subprocess = None
        self._management_socket_name = None
        self._mgmt_socket = None

    def _disconnect(self, ignore_failure=False):
        self._temp_credentials_file = None
        self.terminate_process(ignore_failure=ignore_failure)
        self._remove_props_file()

    @staticmethod
    def get_current_connection():
        res=Wireguard(None,None)
        ProtocolAdapter.register_log_level_trace()
        res._logger = logging.getLogger("NativeVPNConnection")
        res._tmp_cfg_file=None
        try:
            res._read_props_file()
            res._connection_found=True
        except:
            res._connection_found=False
        res._subprocess=None
        res._requires_sudo = (os.getenv("VPNCONNECTIONNATIVE_SUDO_WG", "True").lower() == "true")
        return res

    def _get_protonvpn_connection(self):
        return self._connection_found

    def up(self):
        self._setup()
        self._create_process()

    def down(self):
        self._disconnect()

class Strongswan(NativeConnection):
    """Creates a Strongswan/IKEv2 connection."""
    protocol = "ikev2"

    def _setup(self):
        pass

    def up(self):
        pass

    def down(self):
        pass
