"""Test module to express odd combinations of configurations."""

from .conftest import unix_sockets_only


def test_parametrize_with_socket_enabled_and_allow_hosts(pytester, httpserver):
    """This is a complex test that demonstrates the use of `parametrize`,
    `enable_socket` fixture, allow_hosts CLI flag.

    From: https://github.com/miketheman/pytest-socket/issues/56
    """
    pytester.makepyfile(f"""
        import socket
        import pytest
        from urllib.request import urlopen


        @pytest.mark.parametrize(
            "host",
            ["google.com", "www.amazon.com", "www.microsoft.com"],
        )
        def test_domain(host, socket_enabled):
            # Just verify socket creation and connect aren't blocked
            sock = socket.create_connection((host, 443), timeout=5)
            sock.close()

        def test_localhost_works():
            urlopen("{httpserver.url}/")

        def test_remote_not_allowed_fails():
            urlopen("http://172.1.1.1/")
        """)
    pytester.makeini(f"""
        [pytest]
        addopts = --disable-socket --allow-hosts={httpserver.host}
        """)
    result = pytester.runpytest()
    result.assert_outcomes(passed=4, failed=1)
    result.stdout.fnmatch_lines(
        "*SocketConnectBlockedError: "
        "A test tried to use socket.socket.connect() with host*"
    )


@unix_sockets_only
def test_combine_unix_and_allow_hosts(pytester, httpserver):
    """Test combination of disable, allow-unix and allow-hosts.

    From https://github.com/miketheman/pytest-socket/issues/78
    """
    pytester.makepyfile(f"""
        import socket

        import pytest


        def test_unix_connect():
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            with pytest.raises(FileNotFoundError):
                sock.connect('/tmp/socket.sock')


        def test_inet_connect():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('{httpserver.host}', {httpserver.port}))
        """)
    result = pytester.runpytest(
        "--disable-socket", "--allow-unix-socket", f"--allow-hosts={httpserver.host}"
    )
    result.assert_outcomes(passed=2)
