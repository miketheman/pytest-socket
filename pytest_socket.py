# -*- coding: utf-8 -*-
import socket

import pytest

_true_socket = socket.socket


@pytest.fixture(autouse=True)
def _socket_marker(request):
    if request.node.get_marker('disable_socket'):
        request.getfixturevalue('socket_disabled')
    if request.node.get_marker('enable_socket'):
        request.getfixturevalue('socket_enabled')


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
        raise RuntimeError("A test tried to use socket.socket.")

    socket.socket = guarded


def enable_socket():
    """ re-enable socket.socket to enable the Internet. useful in testing.
    """
    socket.socket = _true_socket
