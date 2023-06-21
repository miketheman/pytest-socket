import pytest

from conftest import unix_sockets_only
from tests.common import assert_socket_blocked

PYFILE_SOCKET_USED_IN_TEST_ARGS = """
    import socket

    def test_socket():
        socket.socket(socket.AF_INET, socket.SOCK_STREAM)
"""


PYFILE_SOCKET_USED_IN_TEST_KWARGS = """
    import socket

    def test_socket():
        socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
"""


PYFILE_SOCKET_NO_ARGS = """
    import socket

    def test_socket():
        socket.socket()
"""


@pytest.mark.parametrize(
    "pyfile",
    [
        PYFILE_SOCKET_USED_IN_TEST_ARGS,
        PYFILE_SOCKET_USED_IN_TEST_KWARGS,
        PYFILE_SOCKET_NO_ARGS,
    ],
)
def test_socket_enabled_by_default(testdir, pyfile):
    testdir.makepyfile(pyfile)
    result = testdir.runpytest()
    result.assert_outcomes(1, 0, 0)
    with pytest.raises(BaseException):
        assert_socket_blocked(result)


def test_global_disable_via_fixture(testdir):
    testdir.makepyfile(
        """
        import pytest
        import pytest_socket
        import socket

        @pytest.fixture(autouse=True)
        def disable_socket_for_all():
            pytest_socket.disable_socket()

        def test_socket():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """
    )
    result = testdir.runpytest()
    assert_socket_blocked(result)


@pytest.mark.parametrize(
    "pyfile",
    [
        PYFILE_SOCKET_USED_IN_TEST_ARGS,
        PYFILE_SOCKET_USED_IN_TEST_KWARGS,
        PYFILE_SOCKET_NO_ARGS,
    ],
)
def test_global_disable_via_cli_flag(testdir, pyfile):
    testdir.makepyfile(pyfile)
    result = testdir.runpytest("--disable-socket")
    assert_socket_blocked(result)


def test_help_message(testdir):
    result = testdir.runpytest(
        "--help",
    )
    result.stdout.fnmatch_lines(
        [
            "socket:",
            "*--disable-socket*Disable socket.socket by default to block network*",
        ]
    )


@pytest.mark.parametrize(
    "pyfile",
    [
        PYFILE_SOCKET_USED_IN_TEST_ARGS,
        PYFILE_SOCKET_USED_IN_TEST_KWARGS,
        PYFILE_SOCKET_NO_ARGS,
    ],
)
def test_global_disable_via_config(testdir, pyfile):
    testdir.makepyfile(pyfile)
    testdir.makeini(
        """
        [pytest]
        addopts = --disable-socket
        """
    )
    result = testdir.runpytest()
    assert_socket_blocked(result)


def test_disable_socket_marker(testdir):
    testdir.makepyfile(
        """
        import pytest
        import socket

        @pytest.mark.disable_socket
        def test_socket():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """
    )
    result = testdir.runpytest()
    assert_socket_blocked(result)


def test_enable_socket_marker(testdir):
    testdir.makepyfile(
        """
        import pytest
        import socket

        @pytest.mark.enable_socket
        def test_socket():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """
    )
    result = testdir.runpytest("--disable-socket")
    result.assert_outcomes(1, 0, 0)
    with pytest.raises(BaseException):
        assert_socket_blocked(result)


def test_urllib_succeeds_by_default(testdir):
    testdir.makepyfile(
        """
        try:
            from urllib.request import urlopen
        except ImportError:
            from urllib2 import urlopen

        def test_disable_socket_urllib():
            assert urlopen('https://httpstat.us/200').getcode() == 200
        """
    )
    result = testdir.runpytest()
    result.assert_outcomes(1, 0, 0)
    with pytest.raises(BaseException):
        assert_socket_blocked(result)


def test_enabled_urllib_succeeds(testdir):
    testdir.makepyfile(
        """
        import pytest
        import pytest_socket
        try:
            from urllib.request import urlopen
        except ImportError:
            from urllib2 import urlopen

        @pytest.mark.enable_socket
        def test_disable_socket_urllib():
            assert urlopen('https://httpstat.us/200').getcode() == 200
        """
    )
    result = testdir.runpytest("--disable-socket")
    result.assert_outcomes(1, 0, 0)
    with pytest.raises(BaseException):
        assert_socket_blocked(result)


def test_disabled_urllib_fails(testdir):
    testdir.makepyfile(
        """
        import pytest
        try:
            from urllib.request import urlopen
        except ImportError:
            from urllib2 import urlopen

        @pytest.mark.disable_socket
        def test_disable_socket_urllib():
            assert urlopen('https://httpstat.us/200').getcode() == 200
        """
    )
    result = testdir.runpytest()
    assert_socket_blocked(result)


def test_double_call_does_nothing(testdir):
    testdir.makepyfile(
        """
        import pytest
        import pytest_socket
        import socket

        def test_double_enabled():
            pytest_socket.enable_socket()
            pytest_socket.enable_socket()
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        def test_double_disabled():
            pytest_socket.disable_socket()
            pytest_socket.disable_socket()
            with pytest.raises(pytest_socket.SocketBlockedError):
                socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        def test_disable_enable():
            pytest_socket.disable_socket()
            pytest_socket.enable_socket()
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """
    )
    result = testdir.runpytest()
    result.assert_outcomes(3, 0, 0)
    with pytest.raises(BaseException):
        assert_socket_blocked(result)


def test_socket_enabled_fixture(testdir, socket_enabled):
    testdir.makepyfile(
        """
        import socket
        def test_socket_enabled(socket_enabled):
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """
    )
    result = testdir.runpytest()
    result.assert_outcomes(1, 0, 0)
    with pytest.raises(BaseException):
        assert_socket_blocked(result)


def test_mix_and_match(testdir, socket_enabled):
    testdir.makepyfile(
        """
        import socket

        def test_socket1():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        def test_socket_enabled(socket_enabled):
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        def test_socket2():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """
    )
    result = testdir.runpytest("--disable-socket")
    result.assert_outcomes(1, 0, 2)


def test_socket_subclass_is_still_blocked(testdir):
    testdir.makepyfile(
        """
        import pytest
        import pytest_socket
        import socket

        @pytest.mark.disable_socket
        def test_subclass_is_still_blocked():

            class MySocket(socket.socket):
                pass

            MySocket(socket.AF_INET, socket.SOCK_STREAM)
        """
    )
    result = testdir.runpytest()
    assert_socket_blocked(result)


@unix_sockets_only
def test_unix_domain_sockets_blocked_with_disable_socket(testdir):
    testdir.makepyfile(
        """
        import socket

        def test_unix_socket():
            socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        """
    )
    result = testdir.runpytest("--disable-socket")
    assert_socket_blocked(result)


@unix_sockets_only
def test_enabling_unix_domain_sockets_with_disable_socket(testdir):
    testdir.makepyfile(
        """
        import socket

        def test_inet():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        def test_unix_socket():
            socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        """
    )
    result = testdir.runpytest("--disable-socket", "--allow-unix-socket")
    result.assert_outcomes(passed=1, skipped=0, failed=1)
