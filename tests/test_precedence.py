"""Test module to express precedence tests between the different
configuration combinations"""

from tests.common import assert_socket_blocked


def test_disable_via_fixture(testdir):
    testdir.makepyfile(
        """
        import socket

        def test_socket(socket_disabled):
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """
    )
    result = testdir.runpytest()
    assert_socket_blocked(result)


def test_disable_via_marker(testdir):
    testdir.makepyfile(
        """
        import socket
        import pytest

        @pytest.mark.disable_socket
        def test_socket():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """
    )
    result = testdir.runpytest()
    assert_socket_blocked(result)


def test_global_disable_via_cli_flag(testdir):
    testdir.makepyfile(
        """
        import socket

        def test_socket():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """
    )
    result = testdir.runpytest("--disable-socket")
    assert_socket_blocked(result)


def test_force_enable_socket_via_cli_flag(testdir):
    testdir.makepyfile(
        """
        import socket
        import pytest

        @pytest.mark.disable_socket
        def test_socket():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """
    )
    result = testdir.runpytest("--force-enable-socket")
    result.assert_outcomes(passed=1)


def test_force_enable_cli_flag_precedence(testdir):
    testdir.makepyfile(
        """
        import socket

        def test_socket():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """
    )
    result = testdir.runpytest("--disable-socket", "--force-enable-socket")
    result.assert_outcomes(passed=1)


def test_global_disable_via_config(testdir):
    testdir.makepyfile(
        """
        import socket

        def test_socket():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """
    )
    testdir.makeini(
        """
        [pytest]
        addopts = --disable-socket
        """
    )
    result = testdir.runpytest()
    assert_socket_blocked(result)


def test_enable_via_fixture(testdir):
    testdir.makepyfile(
        """
        import socket

        def test_socket(socket_enabled):
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        def test_socket_disabled():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """
    )
    result = testdir.runpytest("--disable-socket")
    assert_socket_blocked(result, passed=1, failed=1)


def test_enable_via_marker(testdir):
    testdir.makepyfile(
        """
        import socket
        import pytest

        @pytest.mark.enable_socket
        def test_socket():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        def test_socket_disabled():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """
    )
    result = testdir.runpytest("--disable-socket")
    assert_socket_blocked(result, passed=1, failed=1)


def test_enable_marker_for_test_class(testdir):
    testdir.makepyfile(
        """
        import socket
        import pytest

        @pytest.mark.enable_socket
        class TestSocket:
            def test_socket(self):
                socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        def test_socket_disabled():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """
    )
    result = testdir.runpytest("--disable-socket")
    assert_socket_blocked(result, passed=1, failed=1)


def test_global_disable_and_allow_host(testdir, httpbin):
    """Disable socket globally, but allow a specific host"""
    testdir.makepyfile(
        f"""
        from urllib.request import urlopen

        def test_urlopen():
            assert urlopen("{httpbin.url}/")

        def test_urlopen_disabled():
            assert urlopen("https://google.com/")
        """
    )
    result = testdir.runpytest("--disable-socket", f"--allow-hosts={httpbin.host}")
    assert_socket_blocked(result, passed=1, failed=1)
