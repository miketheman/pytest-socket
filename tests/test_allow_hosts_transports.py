"""Entry points other than ``connect()`` must honour the --allow-hosts list.

``connect()`` is not the only way to reach a host: ``connect_ex()``,
``sendto()`` and ``sendmsg()`` all take an address, and under an allow-list the
socket itself is created by the real ``socket.socket``, so nothing else stops
them.
"""

import socket

import pytest

import pytest_socket
from pytest_socket import (
    SocketConnectBlockedError,
    _remove_restrictions,
    socket_allow_hosts,
)

OUTSIDE_THE_LIST = ("192.0.2.1", 80)


def _listener() -> tuple[socket.socket, int]:
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    return srv, srv.getsockname()[1]


def test_connect_ex_outside_allow_list_is_blocked():
    socket_allow_hosts(["127.0.0.1"])
    try:
        sock = socket.socket()
        with (
            pytest.raises(SocketConnectBlockedError),
            pytest.warns(UserWarning, match=r"socket\.socket\.connect_ex"),
        ):
            sock.connect_ex(OUTSIDE_THE_LIST)
    finally:
        _remove_restrictions()


def test_connect_ex_to_allowed_host_is_permitted():
    srv, port = _listener()
    socket_allow_hosts(["127.0.0.1"])
    try:
        sock = socket.socket()
        assert sock.connect_ex(("127.0.0.1", port)) == 0
        sock.close()
    finally:
        _remove_restrictions()
        srv.close()


def test_udp_sendto_outside_allow_list_is_blocked():
    socket_allow_hosts(["127.0.0.1"])
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        with (
            pytest.raises(SocketConnectBlockedError),
            pytest.warns(UserWarning, match=r"socket\.socket\.sendto"),
        ):
            sock.sendto(b"ping", OUTSIDE_THE_LIST)
    finally:
        _remove_restrictions()


def test_udp_sendto_to_allowed_host_is_permitted():
    receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver.bind(("127.0.0.1", 0))
    port = receiver.getsockname()[1]
    socket_allow_hosts(["127.0.0.1"])
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        assert sock.sendto(b"ping", ("127.0.0.1", port)) == 4
        assert receiver.recv(4) == b"ping"
        sock.close()
    finally:
        _remove_restrictions()
        receiver.close()


@pytest.mark.skipif(
    not hasattr(socket.socket, "sendmsg"), reason="sendmsg is not available"
)
def test_sendmsg_outside_allow_list_is_blocked():
    socket_allow_hosts(["127.0.0.1"])
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        with (
            pytest.raises(SocketConnectBlockedError),
            pytest.warns(UserWarning, match=r"socket\.socket\.sendmsg"),
        ):
            sock.sendmsg([b"ping"], [], 0, OUTSIDE_THE_LIST)
    finally:
        _remove_restrictions()


def test_remove_restrictions_restores_every_guard():
    socket_allow_hosts(["127.0.0.1"])
    _remove_restrictions()
    assert socket.socket.connect_ex is pytest_socket._true_connect_ex
    assert socket.socket.sendto is pytest_socket._true_sendto
    if pytest_socket._true_sendmsg is not None:
        assert socket.socket.sendmsg is pytest_socket._true_sendmsg


def test_cli_allow_hosts_blocks_udp_sendto(pytester):
    pytester.makepyfile("""
        import socket

        import pytest

        from pytest_socket import SocketConnectBlockedError


        def test_udp():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            with pytest.raises(SocketConnectBlockedError):
                sock.sendto(b"ping", ("192.0.2.1", 53))
        """)
    result = pytester.runpytest("--disable-socket", "--allow-hosts=127.0.0.1")
    result.assert_outcomes(passed=1)
