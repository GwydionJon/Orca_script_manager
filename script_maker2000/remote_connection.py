import logging
import traceback
from threading import Timer, Event

from fabric import Connection
from fabric.config import Config
from binascii import hexlify
import paramiko
from paramiko.ssh_exception import (
    BadAuthenticationType,
    PartialAuthentication,
    AuthenticationException,
    SSHException,
)


class RemoteConnection:
    @classmethod
    def connect(cls, user, host, password=None):

        logger = logging.getLogger(__name__)
        # job.client.send(['auth_start'])

        ssh_agent_allowed = False

        try:
            connection_config = Config(
                overrides={
                    "load_ssh_configs": False,
                    "timeouts": {"command": 10, "connect": None},
                },
                lazy=True,
            )
            # TODO: Determine encoding of remote host and dont assume UTF-8.
            connection_config.run.encoding = "UTF-8"
            remote_connection = Connection(
                host,
                user=user,
                config=connection_config,
                connect_kwargs={"allow_agent": ssh_agent_allowed, "auth_timeout": 10},
            )
            remote_connection.client = RemoteXLSSHClient(
                UserAuthHandler(password=password)
            )
            remote_connection.open()
            remote_connection.transport.set_keepalive(300)

            return remote_connection
        except Exception as e:
            errorstring = "Connecting to remote host failed:\n{}: {}".format(
                type(e).__name__, str(e)
            )
            #   job.client.send(['auth_error',errorstring])
            logger.warning(errorstring)
            logger.warning(
                "\n"
                + "".join(traceback.format_tb(e.__traceback__))
                + "\n"
                + str(type(e).__name__)
                + ": "
                + str(e)
            )
            # Log and send the real error and raise AuthenticationException,
            # so the client handler only has to catch this to allow another Authentication attempt.
            raise AuthenticationException() from e


class UserAuthHandler:
    fileno = None

    def __init__(self, password=None):
        # self.client = client
        # self.backend = backend
        self.timeout_timer_args = None
        self.timeout_timer = None
        self.password_ = password

    def interactive_handler(self, title, instructions, prompt_list):
        answers = []
        for prompt, should_echo in prompt_list:
            if "OTP" in prompt:  # If the prompt asks for OTP
                otp = input("Enter your OTP: ")
                answers.append(otp)
            elif "Password" in prompt:
                if self.password_ is None:
                    self.password_ = input(prompt)
                answers.append(self.password_)
            else:
                answer = input(prompt)
                answers.append(answer)
        return answers


# Subclassed paramiko.SSHClient to improve _auth method
# and allow authentication over own interactive handler.
class RemoteXLSSHClient(paramiko.SSHClient):
    def __init__(self, handler):
        super().__init__()
        self.user_auth_handler = handler
        self.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def _auth(
        self,
        username,
        password,
        pkey,
        key_filenames,
        allow_agent,
        look_for_keys,
        gss_auth,
        gss_kex,
        gss_deleg_creds,
        gss_host,
        passphrase,
    ):  # noqa
        saved_exception = None
        allowed_types = set()
        already_used_types = []

        try:
            allowed_types = set(self.get_transport().auth_none(username))
        except BadAuthenticationType as ex:
            allowed_types = set(ex.allowed_types)

        if self._transport.authenticated:
            return
        if self.user_auth_handler is None:
            raise SSHException("No authentication methods available")

        while True:
            # Try publickey authentication
            if (
                "publickey" in allowed_types
                and allow_agent
                and "publickey" not in already_used_types
            ):
                already_used_types.append("publickey")

                if self._agent is None:
                    self._agent = paramiko.Agent()
                    self._agent._connect(self.user_auth_handler)

                if self._agent._conn is None:
                    self._agent._connect(self.user_auth_handler)

                keys = self._agent.get_keys()
                if not keys:
                    self._log(logging.DEBUG, "No SSH agent key available")
                for key in keys:
                    try:
                        id_ = hexlify(key.get_fingerprint())
                        self._log(logging.DEBUG, "Trying SSH agent key {}".format(id_))
                        allowed_types = set(
                            self._transport.auth_publickey(username, key)
                        )
                        if self._transport.authenticated:
                            return
                        break
                    except SSHException as e:
                        saved_exception = e
                continue

            if "keyboard-interactive" in allowed_types:
                try:
                    if (not self._transport.active) or (
                        not self._transport.initial_kex_done
                    ):
                        raise SSHException("No existing session")

                    auth_event = Event()
                    if self._transport.auth_timeout is not None:
                        timeout_event = Event()
                        timeout_timer = Timer(
                            self._transport.auth_timeout, timeout_event.set
                        )
                        timeout_timer.start()
                    self._transport.auth_handler = paramiko.auth_handler.AuthHandler(
                        self._transport
                    )
                    self._transport.auth_handler.auth_interactive(
                        username, self.user_auth_handler.interactive_handler, auth_event
                    )

                    allowed_types = set()
                    while True:
                        auth_event.wait(0.1)
                        if not self._transport.is_active():
                            e = self._transport.get_exception()
                            if (e is None) or issubclass(e.__class__, EOFError):
                                e = AuthenticationException("Authentication failed.")
                            raise e
                        if auth_event.is_set():
                            break
                    # if timeout_event.is_set():
                    #     raise AuthenticationException("Authentication timeout.")

                    if not self._transport.auth_handler.is_authenticated():
                        e = self._transport.get_exception()
                        if e is None:
                            e = AuthenticationException("Authentication failed.")
                        if issubclass(e.__class__, PartialAuthentication):
                            allowed_types = set(e.allowed_types)
                        raise e

                    if self._transport.authenticated:
                        return

                except SSHException as e:
                    saved_exception = e

                continue

            if "password" in allowed_types and "password" not in already_used_types:
                already_used_types.append("password")
                print("test")
                if password is None:
                    password = self.user_auth_handler.interactive_handler()
                try:
                    allowed_types = set(
                        self._transport.auth_password(username, password)
                    )
                    if self._transport.authenticated:
                        return
                except SSHException as e:
                    saved_exception = e

                continue

            if saved_exception is not None:
                raise saved_exception
            raise SSHException("No authentication methods available")
