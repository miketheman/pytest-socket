"""Wrapping existing socket descriptors must not create a new socket."""

import os
import socket
import subprocess
import sys
import textwrap
from contextlib import ExitStack, contextmanager
from pathlib import Path

import pytest

import pytest_socket
from pytest_socket import (
    SocketBlockedError,
    SocketConnectBlockedError,
    disable_socket,
    enable_socket,
    socket_allow_hosts,
)


class _AcceptFdListener(socket.socket):
    """Keep accepted fds owned until the real stdlib wrapper takes ownership."""

    fd_cleanup: ExitStack

    def _accept(self):
        fd, address = super()._accept()
        self.fd_cleanup.callback(socket.close, fd)
        return fd, address


@contextmanager
def _connected_listener_and_client():
    with _AcceptFdListener(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.settimeout(2)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.settimeout(2)
            client.connect(listener.getsockname())
            assert client.getpeername() == listener.getsockname()
            yield listener, client


def _accept_with_fd_cleanup(listener):
    with ExitStack() as cleanup:
        listener.fd_cleanup = cleanup
        result = listener.accept()
        cleanup.pop_all()
        return result


@contextmanager
def _wrapped_socket_after_disable_socket(original):
    with ExitStack() as fd_cleanup:
        fd = original.detach()
        fd_cleanup.callback(socket.close, fd)
        assert original.fileno() == -1
        disable_socket()
        try:
            wrapped = socket.socket(fileno=fd)
            fd_cleanup.pop_all()
            with wrapped:
                yield wrapped
        finally:
            enable_socket()


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
            accepted, address = _accept_with_fd_cleanup(listener)
            with accepted:
                assert address == client.getsockname()
                _assert_bidirectional_exchange(client, accepted)
        finally:
            enable_socket()


def test_detached_socket_fd_can_be_wrapped_after_disable_socket():
    with _connected_listener_and_client() as (listener, client):
        accepted, _ = _accept_with_fd_cleanup(listener)
        with accepted, _wrapped_socket_after_disable_socket(client) as wrapped:
            _assert_bidirectional_exchange(wrapped, accepted)


@pytest.mark.parametrize("kwargs", [{}, {"fileno": None}])
def test_creating_a_socket_without_an_existing_fd_stays_blocked(kwargs):
    disable_socket()
    try:
        with (
            pytest.raises(SocketBlockedError),
            pytest.warns(UserWarning, match="A test tried to use socket.socket"),
        ):
            socket.socket(**kwargs)
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
def test_socket_fd_zero_can_be_wrapped_in_an_isolated_process(tmp_path):
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
    env = {
        "HOME": str(tmp_path / "home"),
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
        "XDG_CONFIG_HOME": str(tmp_path / "config"),
        "PATH": os.defpath,
        "PYTHONPATH": str(Path(pytest_socket.__file__).resolve().parents[1]),
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    }
    subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=env,
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


@pytest.mark.parametrize(
    "method,args",
    [
        ("getaddrinfo", ("127.0.0.1", None)),
        ("gethostbyname", ("127.0.0.1",)),
    ],
)
def test_wrapping_an_existing_fd_keeps_dns_guards(method, args):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as original:
        with _wrapped_socket_after_disable_socket(original):
            with (
                pytest.raises(SocketBlockedError),
                pytest.warns(UserWarning, match=f"socket.{method}"),
            ):
                getattr(socket, method)(*args)


def test_two_consecutive_tests_can_use_an_existing_local_listener(pytester):
    pytester.makepyfile("""
        import socket
        from contextlib import ExitStack

        import pytest
        from pytest_socket import disable_socket, enable_socket


        class Listener(socket.socket):
            def _accept(self):
                fd, address = super()._accept()
                self.fd_cleanup.callback(socket.close, fd)
                return fd, address


        def accept_with_fd_cleanup(listener):
            with ExitStack() as cleanup:
                listener.fd_cleanup = cleanup
                result = listener.accept()
                cleanup.pop_all()
                return result


        @pytest.fixture(scope="session")
        def listener():
            with Listener(socket.AF_INET, socket.SOCK_STREAM) as server:
                server.settimeout(2)
                server.bind(("127.0.0.1", 0))
                server.listen(1)
                yield server


        @pytest.fixture
        def guarded_client(listener):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
                client.settimeout(2)
                client.connect(listener.getsockname())
                assert client.getpeername() == listener.getsockname()
                disable_socket()
                try:
                    yield client
                finally:
                    enable_socket()


        @pytest.mark.parametrize("repeat", range(2))
        def test_local_server(listener, guarded_client, repeat):
            accepted, _ = accept_with_fd_cleanup(listener)
            with accepted:
                accepted.settimeout(2)
                guarded_client.sendall(b"x")
                assert accepted.recv(1) == b"x"
        """)
    result = pytester.runpytest("-p", "pytest_socket", "-v")
    result.assert_outcomes(passed=2)
