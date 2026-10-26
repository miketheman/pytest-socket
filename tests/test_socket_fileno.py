"""Wrapping existing socket descriptors must not create a new socket."""

import os
import socket
import subprocess
import sys
import textwrap
from contextlib import contextmanager

import pytest

import pytest_socket
from pytest_socket import (
    SocketBlockedError,
    SocketBlockedWarning,
    SocketConnectBlockedError,
    disable_socket,
    enable_socket,
    socket_allow_hosts,
)

from .conftest import unix_sockets_only


@contextmanager
def _connected_listener_and_client():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.settimeout(2)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.settimeout(2)
            client.connect(listener.getsockname())
            assert client.getpeername() == listener.getsockname()
            yield listener, client


@contextmanager
def _wrapped_socket_after_disable_socket(original):
    fd = original.detach()
    assert original.fileno() == -1
    try:
        disable_socket()
        wrapped = socket.socket(fileno=fd)
        fd = None
        with wrapped:
            yield wrapped
    finally:
        enable_socket()
        if fd is not None:
            socket.close(fd)


def _assert_bidirectional_exchange(client, accepted):
    client.settimeout(2)
    accepted.settimeout(2)
    client.sendall(b"x")
    assert accepted.recv(1) == b"x"
    accepted.sendall(b"y")
    assert client.recv(1) == b"y"


def test_accept_wraps_existing_connection_after_disable_socket():
    with _connected_listener_and_client() as (listener, client):
        disable_socket()
        try:
            accepted, address = listener.accept()
            with accepted:
                assert address == client.getsockname()
                _assert_bidirectional_exchange(client, accepted)
        finally:
            enable_socket()


def test_detached_socket_fd_can_be_wrapped_after_disable_socket():
    with _connected_listener_and_client() as (listener, client):
        accepted, _ = listener.accept()
        with accepted, _wrapped_socket_after_disable_socket(client) as wrapped:
            _assert_bidirectional_exchange(wrapped, accepted)


def test_creating_a_socket_with_fileno_none_stays_blocked():
    disable_socket()
    try:
        with (
            pytest.raises(SocketBlockedError),
            pytest.warns(UserWarning, match="A test tried to use socket.socket"),
        ):
            socket.socket(fileno=None)
    finally:
        enable_socket()


@pytest.mark.parametrize("fd", [-1, -2, 2**31 - 1])
def test_invalid_socket_fd_preserves_stdlib_error(fd):
    with pytest.raises((ValueError, OSError)) as expected:
        socket.socket(fileno=fd)
    disable_socket()
    try:
        with pytest.raises(type(expected.value)) as actual:
            socket.socket(fileno=fd)
        assert actual.value.args == expected.value.args
    finally:
        enable_socket()


@pytest.mark.skipif(os.name != "posix", reason="Replacing fd 0 requires POSIX")
def test_socket_fd_zero_can_be_wrapped_in_an_isolated_process():
    script = textwrap.dedent("""
        import os
        import socket

        from pytest_socket import disable_socket, enable_socket

        original = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        fd = original.detach()
        if fd != 0:
            os.dup2(fd, 0)
            socket.close(fd)
        fd = 0
        try:
            disable_socket()
            wrapped = socket.socket(fileno=fd)
            fd = None
            with wrapped:
                assert wrapped.fileno() == 0
                assert wrapped.family == socket.AF_INET
                assert wrapped.getsockname() == ("0.0.0.0", 0)
        finally:
            enable_socket()
            if fd is not None:
                socket.close(fd)
        """)
    subprocess.run(
        [sys.executable, "-c", script],
        stdin=subprocess.DEVNULL,
        timeout=10,
        check=True,
    )


@pytest.mark.parametrize("allowed", [True, False])
def test_wrapped_fd_respects_host_restrictions_and_closes_on_denial(allowed):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.settimeout(2)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as original:
            with _wrapped_socket_after_disable_socket(original) as wrapped:
                wrapped.settimeout(2)
                try:
                    socket_allow_hosts(["127.0.0.1" if allowed else "127.0.0.2"])
                    if allowed:
                        wrapped.connect(listener.getsockname())
                        accepted, _ = listener.accept()
                        with accepted:
                            _assert_bidirectional_exchange(wrapped, accepted)
                    else:
                        with (
                            pytest.raises(SocketConnectBlockedError),
                            pytest.warns(UserWarning, match="socket.socket.connect"),
                        ):
                            wrapped.connect(listener.getsockname())
                        assert wrapped.fileno() == -1
                finally:
                    pytest_socket._remove_restrictions()


def test_socketpair_stays_blocked_after_disable_socket():
    disable_socket()
    try:
        with (
            pytest.raises(SocketBlockedError),
            pytest.warns(SocketBlockedWarning),
        ):
            socket.socketpair()
    finally:
        enable_socket()


@unix_sockets_only
@pytest.mark.skipif(os.name != "posix", reason="POSIX socketpair uses Unix sockets")
def test_socketpair_can_be_created_when_unix_sockets_are_allowed():
    disable_socket(allow_unix_socket=True)
    try:
        first, second = socket.socketpair()
        with first, second:
            _assert_bidirectional_exchange(first, second)
    finally:
        enable_socket()


@pytest.mark.skipif(os.name != "nt", reason="Windows socketpair uses a TCP fallback")
def test_socketpair_stays_blocked_on_windows_when_unix_sockets_are_allowed():
    disable_socket(allow_unix_socket=True)
    try:
        with (
            pytest.raises(SocketBlockedError),
            pytest.warns(SocketBlockedWarning),
        ):
            socket.socketpair()
    finally:
        enable_socket()


def test_two_consecutive_tests_can_use_an_existing_local_listener(pytester):
    pytester.makepyfile("""
        import socket

        import pytest
        from pytest_socket import SocketBlockedError


        @pytest.fixture(scope="session")
        def connections():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
                server.settimeout(2)
                server.bind(("127.0.0.1", 0))
                server.listen(2)
                with (
                    socket.socket(socket.AF_INET, socket.SOCK_STREAM) as first,
                    socket.socket(socket.AF_INET, socket.SOCK_STREAM) as second,
                ):
                    clients = (first, second)
                    for client in clients:
                        client.settimeout(2)
                        client.connect(server.getsockname())
                    yield server, clients


        @pytest.mark.enable_socket
        def test_start_listener(connections):
            listener, clients = connections
            for client in clients:
                assert client.getpeername() == listener.getsockname()


        @pytest.mark.parametrize("repeat", range(2))
        def test_local_server(connections, repeat):
            listener, clients = connections
            client = clients[repeat]
            with pytest.raises(SocketBlockedError):
                socket.socket()
            accepted, _ = listener.accept()
            with accepted:
                accepted.settimeout(2)
                client.sendall(b"x")
                assert accepted.recv(1) == b"x"
                accepted.sendall(b"y")
                assert client.recv(1) == b"y"
        """)
    result = pytester.runpytest("--disable-socket", "-p", "no:randomly", "-v")
    result.assert_outcomes(passed=3)
