# -*- coding: utf-8 -*-
import socket

import pytest

_true_socket = socket.socket


class SocketBlockedError(RuntimeError):
    def __init__(self, *args, **kwargs):
        super(SocketBlockedError, self).__init__("A test tried to use socket.socket.")


def pytest_addoption(parser):
    group = parser.getgroup('socket')
    group.addoption(
        '--disable-socket',
        action='store_true',
        dest='disable_socket',
        help='Disable socket.socket by default to block network calls.'
    )


@pytest.fixture(autouse=True)
def _socket_marker(request):
    if request.node.get_marker('disable_socket'):
        request.getfixturevalue('socket_disabled')
    if request.node.get_marker('enable_socket'):
        request.getfixturevalue('socket_enabled')

    if request.config.getoption('--disable-socket'):
        request.getfixturevalue('socket_disabled')


@pytest.fixture
def socket_disabled():
    """ disable socket.socket for duration of this test function """
    disable_socket()
    yield
    enable_socket()


@pytest.fixture
def socket_enabled():
    """ enable socket.socket for duration of this test function """
    enable_socket()
    yield
    disable_socket()


def disable_socket():
    """ disable socket.socket to disable the Internet. useful in testing.
    """

    def guarded(*args, **kwargs):
        raise SocketBlockedError()

    socket.socket = guarded


def enable_socket():
    """ re-enable socket.socket to enable the Internet. useful in testing.
    """
    socket.socket = _true_socket
