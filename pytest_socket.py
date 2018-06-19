# -*- coding: utf-8 -*-
import socket

import pytest

_true_connect = socket.socket.connect


class SocketBlockedError(RuntimeError):
    def __init__(self, allowed, host, *args, **kwargs):
        if allowed:
            allowed = ','.join(allowed)
        super(SocketBlockedError, self).__init__(
            'A test tried to use socket.socket.connect() with host "{0}" (allowed: "{1}").'.format(host, allowed)
        )


def pytest_addoption(parser):
    group = parser.getgroup('socket')
    group.addoption(
        '--disable-socket',
        dest='disable_socket',
        nargs='?',
        default=False,
        metavar='ALLOWED_HOSTS_CSV',
        help='Intercept socket.socket.connect() to block network calls (except those optionally specified as CSV ' +
             'argument).'
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "disable_socket([allowed_hosts]): Disable socket connections for a specific " +
                            "test (with optional allowed list of hosts)")
    config.addinivalue_line("markers", "enable_socket(): Enable socket connections for a specific test")


@pytest.fixture()
def socket_allowed_hosts(request):
    marker = request.node.get_marker('disable_socket')
    cli = request.config.getoption('--disable-socket')
    if marker and marker.args:
        return marker.args[0]
    elif isinstance(cli, str):
        return cli


@pytest.fixture(autouse=True)
def _socket_marker(request):
    if request.node.get_marker('disable_socket'):
        request.getfixturevalue('socket_disabled')
    if request.node.get_marker('enable_socket'):
        request.getfixturevalue('socket_enabled')

    if request.config.getoption('--disable-socket') is not False:
        request.getfixturevalue('socket_disabled')


@pytest.fixture
def socket_disabled(socket_allowed_hosts):
    """ disable socket.socket.connect() for duration of this test function """
    disable_socket(socket_allowed_hosts)
    yield
    enable_socket()


@pytest.fixture
def socket_enabled():
    """ enable socket.socket.connect() for duration of this test function """
    enable_socket()
    yield
    disable_socket()


def disable_socket(allowed=None):
    """ disable socket.socket.connect() to disable the Internet. useful in testing.
    """
    if allowed is None:
        allowed = []
    if isinstance(allowed, str):
        allowed = allowed.split(',')

    def guarded_connect(inst, address):
        host, port = address
        if allowed and host in allowed:
            return _true_connect(inst, address)
        raise SocketBlockedError(allowed, host)

    socket.socket.connect = guarded_connect


def enable_socket():
    """ re-enable socket.socket.connect() to enable the Internet. useful in testing.
    """
    socket.socket.connect = _true_connect
