"""Test module to express precedence tests between the different
configuration combinations"""

from .common import assert_socket_blocked


def test_disable_via_fixture(pytester):
    pytester.makepyfile("""
        import socket

        def test_socket(socket_disabled):
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """)
    result = pytester.runpytest()
    assert_socket_blocked(result)


def test_disable_via_marker(pytester):
    pytester.makepyfile("""
        import socket
        import pytest

        @pytest.mark.disable_socket
        def test_socket():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """)
    result = pytester.runpytest()
    assert_socket_blocked(result)


def test_global_disable_via_cli_flag(pytester):
    pytester.makepyfile("""
        import socket

        def test_socket():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """)
    result = pytester.runpytest("--disable-socket")
    assert_socket_blocked(result)


def test_force_enable_socket_via_cli_flag(pytester):
    pytester.makepyfile("""
        import socket
        import pytest

        @pytest.mark.disable_socket
        def test_socket():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """)
    result = pytester.runpytest("--force-enable-socket")
    result.assert_outcomes(passed=1)


def test_force_enable_cli_flag_precedence(pytester):
    pytester.makepyfile("""
        import socket

        def test_socket():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """)
    result = pytester.runpytest("--disable-socket", "--force-enable-socket")
    result.assert_outcomes(passed=1)


def test_global_disable_via_config(pytester):
    pytester.makepyfile("""
        import socket

        def test_socket():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """)
    pytester.makeini("""
        [pytest]
        addopts = --disable-socket
        """)
    result = pytester.runpytest()
    assert_socket_blocked(result)


def test_enable_via_fixture(pytester):
    pytester.makepyfile("""
        import socket

        def test_socket(socket_enabled):
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        def test_socket_disabled():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """)
    result = pytester.runpytest("--disable-socket")
    assert_socket_blocked(result, passed=1, failed=1)


def test_enable_via_marker(pytester):
    pytester.makepyfile("""
        import socket
        import pytest

        @pytest.mark.enable_socket
        def test_socket():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        def test_socket_disabled():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """)
    result = pytester.runpytest("--disable-socket")
    assert_socket_blocked(result, passed=1, failed=1)


def test_enable_marker_for_test_class(pytester):
    pytester.makepyfile("""
        import socket
        import pytest

        @pytest.mark.enable_socket
        class TestSocket:
            def test_socket(self):
                socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        def test_socket_disabled():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """)
    result = pytester.runpytest("--disable-socket")
    assert_socket_blocked(result, passed=1, failed=1)


def test_global_disable_and_allow_host(pytester, httpbin):
    """Disable socket globally, but allow a specific host"""
    pytester.makepyfile(f"""
        from urllib.request import urlopen

        def test_urlopen():
            assert urlopen("{httpbin.url}/")

        def test_urlopen_disabled():
            assert urlopen("https://google.com/")
        """)
    result = pytester.runpytest("--disable-socket", f"--allow-hosts={httpbin.host}")
    assert_socket_blocked(result, passed=1, failed=1)
