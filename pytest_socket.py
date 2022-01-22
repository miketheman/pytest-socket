# -*- coding: utf-8 -*-
import socket

import pytest

_true_socket = socket.socket
_true_connect = socket.socket.connect


class SocketBlockedError(RuntimeError):
    def __init__(self, *args, **kwargs):
        super(SocketBlockedError, self).__init__("A test tried to use socket.socket.")


class SocketConnectBlockedError(RuntimeError):
    def __init__(self, allowed, host, *args, **kwargs):
        if allowed:
            allowed = ",".join(allowed)
        super(SocketConnectBlockedError, self).__init__(
            "A test tried to use socket.socket.connect() "
            f'with host "{host}" (allowed: "{allowed}").'
        )


def pytest_addoption(parser):
    group = parser.getgroup("socket")
    group.addoption(
        "--disable-socket",
        action="store_true",
        dest="disable_socket",
        help="Disable socket.socket by default to block network calls.",
    )
    group.addoption(
        "--allow-hosts",
        dest="allow_hosts",
        metavar="ALLOWED_HOSTS_CSV",
        help="Only allow specified hosts through socket.socket.connect((host, port)).",
    )
    group.addoption(
        "--allow-unix-socket",
        action="store_true",
        dest="allow_unix_socket",
        help="Allow calls if they are to Unix domain sockets",
    )


@pytest.fixture
def socket_disabled(pytestconfig):
    """disable socket.socket for duration of this test function"""
    disable_socket(allow_unix_socket=pytestconfig.__socket_allow_unix_socket)
    yield


@pytest.fixture
def socket_enabled(pytestconfig):
    """enable socket.socket for duration of this test function"""
    enable_socket()
    yield


def _is_unix_socket(family) -> bool:
    try:
        is_unix_socket = family == socket.AF_UNIX
    except AttributeError:
        # AF_UNIX not supported on Windows https://bugs.python.org/issue33408
        is_unix_socket = False
    return is_unix_socket


def disable_socket(allow_unix_socket=False):
    """disable socket.socket to disable the Internet. useful in testing."""

    class GuardedSocket(socket.socket):
        """socket guard to disable socket creation (from pytest-socket)"""

        def __new__(cls, family=-1, type=-1, proto=-1, fileno=None):
            if _is_unix_socket(family) and allow_unix_socket:
                return super().__new__(cls, family, type, proto, fileno)

            raise SocketBlockedError()

    socket.socket = GuardedSocket


def enable_socket():
    """re-enable socket.socket to enable the Internet. useful in testing."""
    socket.socket = _true_socket


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "disable_socket(): Disable socket connections for a specific test"
    )
    config.addinivalue_line(
        "markers", "enable_socket(): Enable socket connections for a specific test"
    )
    config.addinivalue_line(
        "markers",
        "allow_hosts([hosts]): Restrict socket connection to defined list of hosts",
    )

    # Store the global configs in the `pytest.Config` object.
    config.__socket_disabled = config.getoption("--disable-socket")
    config.__socket_allow_unix_socket = config.getoption("--allow-unix-socket")
    config.__socket_allow_hosts = config.getoption("--allow-hosts")


def pytest_runtest_setup(item) -> None:
    """During each test item's setup phase,
    choose the behavior based on the configurations supplied.

    This is the bulk of the logic for the plugin.
    As the logic can be extensive, this method is allowed complexity.
    It may be refactored in the future to be more readable.

    If the given item is not a function test (i.e a DoctestItem)
    or otherwise has no support for fixtures, skip it.
    """
    if not hasattr(item, "fixturenames"):
        return

    # If test has the `enable_socket` marker, we accept this as most explicit.
    if "socket_enabled" in item.fixturenames or item.get_closest_marker(
        "enable_socket"
    ):
        enable_socket()
        return

    # If the test has the `disable_socket` marker, it's explicitly disabled.
    if "socket_disabled" in item.fixturenames or item.get_closest_marker(
        "disable_socket"
    ):
        disable_socket(item.config.__socket_allow_unix_socket)
        return

    # Resolve `allow_hosts` behaviors.
    hosts = _resolve_allow_hosts(item)

    # Finally, check the global config and disable socket if needed.
    if item.config.__socket_disabled and not hosts:
        disable_socket(item.config.__socket_allow_unix_socket)


def _resolve_allow_hosts(item):
    """Resolve `allow_hosts` behaviors."""
    mark_restrictions = item.get_closest_marker("allow_hosts")
    cli_restrictions = item.config.__socket_allow_hosts
    hosts = None
    if mark_restrictions:
        hosts = mark_restrictions.args[0]
    elif cli_restrictions:
        hosts = cli_restrictions
    socket_allow_hosts(hosts, allow_unix_socket=item.config.__socket_allow_unix_socket)
    return hosts


def pytest_runtest_teardown():
    _remove_restrictions()


def host_from_address(address):
    host = address[0]
    if isinstance(host, str):
        return host


def host_from_connect_args(args):
    address = args[0]

    if isinstance(address, tuple):
        return host_from_address(address)


def socket_allow_hosts(allowed=None, allow_unix_socket=False):
    """disable socket.socket.connect() to disable the Internet. useful in testing."""
    if isinstance(allowed, str):
        allowed = allowed.split(",")
    if not isinstance(allowed, list):
        return

    def guarded_connect(inst, *args):
        host = host_from_connect_args(args)
        if host in allowed or (_is_unix_socket(inst.family) and allow_unix_socket):
            return _true_connect(inst, *args)

        raise SocketConnectBlockedError(allowed, host)

    socket.socket.connect = guarded_connect


def _remove_restrictions():
    """restore socket.socket.* to allow access to the Internet. useful in testing."""
    socket.socket = _true_socket
    socket.socket.connect = _true_connect
