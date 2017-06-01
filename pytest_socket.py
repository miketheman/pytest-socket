# -*- coding: utf-8 -*-
import socket
import sys

import pytest

_module = sys.modules[__name__]


def pytest_runtest_setup():
    """ disable the internet. test-cases can explicitly re-enable """
    disable_socket()


@pytest.fixture(scope='function')
def socket_enabled(request):
    """ re-enable socket.socket for duration of this test function """
    enable_socket()
    request.addfinalizer(disable_socket)


def disable_socket():
    """ disable socket.socket to disable the Internet. useful in testing.
    """
    setattr(_module, u'_socket_disabled', True)

    def guarded(*args, **kwargs):
        if getattr(_module, u'_socket_disabled', False):
            raise RuntimeError(
                u"A test tried to use socket.socket without explicitly un-blocking it.")
        else:
            # SocketType is a valid, public alias of socket.socket,
            # we use it here to avoid namespace collisions
            return socket.SocketType(*args, **kwargs)

    socket.socket = guarded

    print(u'[!] socket.socket is now blocked. The network should be inaccessible.')


def enable_socket():
    """ re-enable socket.socket to enable the Internet. useful in testing.
    """
    setattr(_module, u'_socket_disabled', False)
    print(u'[!] socket.socket is UN-blocked, and the network can be accessed.')
