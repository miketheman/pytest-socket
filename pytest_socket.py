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
            allowed = ','.join(allowed)
        super(SocketConnectBlockedError, self).__init__(
            'A test tried to use socket.socket.connect() with host "{0}" (allowed: "{1}").'.format(host, allowed)
        )


def pytest_addoption(parser):
    group = parser.getgroup('socket')
    group.addoption(
        '--disable-socket',
        action='store_true',
        dest='disable_socket',
        help='Disable socket.socket by default to block network calls.'
    )
    group.addoption(
        '--allow-hosts',
        dest='allow_hosts',
        metavar='ALLOWED_HOSTS_CSV',
        help='Only allow specified hosts through socket.socket.connect((host, port)).'
    )
    group.addoption(
        '--allow-unix-socket',
        action='store_true',
        dest='allow_unix_socket',
        help='Allow calls if they are to Unix domain sockets'
    )


@pytest.fixture(autouse=True)
def _socket_marker(request):
    """
    Create an automatically-used fixture that every test function will load.

    The last option to set the fixture wins priority.
    The expected behavior is that higher granularity options should override
    lower granularity options.
    """
    if request.config.getoption('--disable-socket'):
        request.getfixturevalue('socket_disabled')

    if request.node.get_closest_marker('disable_socket'):
        request.getfixturevalue('socket_disabled')
    if request.node.get_closest_marker('enable_socket'):
        request.getfixturevalue('socket_enabled')


@pytest.fixture
def socket_disabled(pytestconfig):
    """ disable socket.socket for duration of this test function """
    allow_unix_socket = pytestconfig.getoption('--allow-unix-socket')
    disable_socket(allow_unix_socket)
    yield
    enable_socket()


@pytest.fixture
def socket_enabled(pytestconfig):
    """ enable socket.socket for duration of this test function """
    enable_socket()
    yield
    allow_unix_socket = pytestconfig.getoption('--allow-unix-socket')
    disable_socket(allow_unix_socket)


def disable_socket(allow_unix_socket=False):
    """ disable socket.socket to disable the Internet. useful in testing.
    """

    class GuardedSocket(socket.socket):
        """ socket guard to disable socket creation (from pytest-socket) """
        def __new__(cls, *args, **kwargs):
            try:
                is_unix_socket = args[0] == socket.AF_UNIX
            except AttributeError:
                # AF_UNIX not supported on Windows https://bugs.python.org/issue33408
                is_unix_socket = False

            if is_unix_socket and allow_unix_socket:
                return super().__new__(cls, *args, **kwargs)

            raise SocketBlockedError()

    socket.socket = GuardedSocket


def enable_socket():
    """ re-enable socket.socket to enable the Internet. useful in testing.
    """
    socket.socket = _true_socket


def pytest_configure(config):
    config.addinivalue_line("markers", "disable_socket(): Disable socket connections for a specific test")
    config.addinivalue_line("markers", "enable_socket(): Enable socket connections for a specific test")
    config.addinivalue_line("markers", "allow_hosts([hosts]): Restrict socket connection to defined list of hosts")


def pytest_runtest_setup(item):
    mark_restrictions = item.get_closest_marker('allow_hosts')
    cli_restrictions = item.config.getoption('--allow-hosts')
    hosts = None
    if mark_restrictions:
        hosts = mark_restrictions.args[0]
    elif cli_restrictions:
        hosts = cli_restrictions
    socket_allow_hosts(hosts)


def pytest_runtest_teardown():
    remove_host_restrictions()


def host_from_address(address):
    host = address[0]
    if isinstance(host, str):
        return host


def host_from_connect_args(args):
    address = args[0]

    if isinstance(address, tuple):
        return host_from_address(address)


def socket_allow_hosts(allowed=None):
    """ disable socket.socket.connect() to disable the Internet. useful in testing.
    """
    if isinstance(allowed, str):
        allowed = allowed.split(',')
    if not isinstance(allowed, list):
        return

    def guarded_connect(inst, *args):
        host = host_from_connect_args(args)
        if host and host in allowed:
            return _true_connect(inst, *args)
        raise SocketConnectBlockedError(allowed, host)

    socket.socket.connect = guarded_connect


def remove_host_restrictions():
    """ restore socket.socket.connect() to allow access to the Internet. useful in testing.
    """
    socket.socket.connect = _true_connect
