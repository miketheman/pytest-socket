import pytest

from pytest_socket import (
    SocketBlockedError,
    disable_socket,
    enable_socket,
    host_from_address,
    pytest_runtest_setup,
)

from .common import assert_socket_blocked
from .conftest import unix_sockets_only

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
def test_socket_enabled_by_default(pytester, pyfile):
    pytester.makepyfile(pyfile)
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)
    with pytest.raises(BaseException):
        assert_socket_blocked(result)


def test_global_disable_via_fixture(pytester):
    pytester.makepyfile("""
        import pytest
        import pytest_socket
        import socket

        @pytest.fixture(autouse=True)
        def disable_socket_for_all():
            pytest_socket.disable_socket()

        def test_socket():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """)
    result = pytester.runpytest()
    assert_socket_blocked(result)


@pytest.mark.parametrize(
    "pyfile",
    [
        PYFILE_SOCKET_USED_IN_TEST_ARGS,
        PYFILE_SOCKET_USED_IN_TEST_KWARGS,
        PYFILE_SOCKET_NO_ARGS,
    ],
)
def test_global_disable_via_cli_flag(pytester, pyfile):
    pytester.makepyfile(pyfile)
    result = pytester.runpytest("--disable-socket")
    assert_socket_blocked(result)


def test_help_message(pytester):
    result = pytester.runpytest(
        "--help",
    )
    result.stdout.fnmatch_lines(
        [
            "socket:",
            "*--disable-socket*Disable socket.socket by default to block network*",
            "*Force enable socket.socket network calls*",
            "*--allow-unix-socket*Allow calls if they are to Unix domain sockets*",
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
def test_global_disable_via_config(pytester, pyfile):
    pytester.makepyfile(pyfile)
    pytester.makeini("""
        [pytest]
        addopts = --disable-socket
        """)
    result = pytester.runpytest()
    assert_socket_blocked(result)


def test_disable_socket_marker(pytester):
    pytester.makepyfile("""
        import pytest
        import socket

        @pytest.mark.disable_socket
        def test_socket():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """)
    result = pytester.runpytest()
    assert_socket_blocked(result)


def test_enable_socket_marker(pytester):
    pytester.makepyfile("""
        import pytest
        import socket

        @pytest.mark.enable_socket
        def test_socket():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """)
    result = pytester.runpytest("--disable-socket")
    result.assert_outcomes(passed=1)
    with pytest.raises(BaseException):
        assert_socket_blocked(result)


def test_urllib_succeeds_by_default(pytester):
    pytester.makepyfile("""
        from urllib.request import urlopen

        def test_disable_socket_urllib():
            assert urlopen('https://http.codes/200').getcode() == 200
        """)
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)
    with pytest.raises(BaseException):
        assert_socket_blocked(result)


def test_enabled_urllib_succeeds(pytester):
    pytester.makepyfile("""
        import pytest
        import pytest_socket
        from urllib.request import urlopen

        @pytest.mark.enable_socket
        def test_disable_socket_urllib():
            assert urlopen('https://http.codes/200').getcode() == 200
        """)
    result = pytester.runpytest("--disable-socket")
    result.assert_outcomes(passed=1)
    with pytest.raises(BaseException):
        assert_socket_blocked(result)


def test_disabled_urllib_fails(pytester):
    pytester.makepyfile("""
        import pytest
        from urllib.request import urlopen

        @pytest.mark.disable_socket
        def test_disable_socket_urllib():
            assert urlopen('https://http.codes/200').getcode() == 200
        """)
    result = pytester.runpytest()
    assert_socket_blocked(result)


def test_double_call_does_nothing(pytester):
    pytester.makepyfile("""
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
        """)
    result = pytester.runpytest()
    result.assert_outcomes(passed=3)
    with pytest.raises(BaseException):
        assert_socket_blocked(result)


def test_socket_enabled_fixture(pytester, socket_enabled):
    pytester.makepyfile("""
        import socket
        def test_socket_enabled(socket_enabled):
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """)
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)
    with pytest.raises(BaseException):
        assert_socket_blocked(result)


def test_mix_and_match(pytester, socket_enabled):
    pytester.makepyfile("""
        import socket

        def test_socket1():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        def test_socket_enabled(socket_enabled):
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        def test_socket2():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """)
    result = pytester.runpytest("--disable-socket")
    result.assert_outcomes(passed=1, failed=2)


def test_socket_subclass_is_still_blocked(pytester):
    pytester.makepyfile("""
        import pytest
        import pytest_socket
        import socket

        @pytest.mark.disable_socket
        def test_subclass_is_still_blocked():

            class MySocket(socket.socket):
                pass

            MySocket(socket.AF_INET, socket.SOCK_STREAM)
        """)
    result = pytester.runpytest()
    assert_socket_blocked(result)


def test_blocked_socket_emits_warning(pytester):
    """Ensure SocketBlockedError emits a warning before raising.

    This makes blocked calls visible in test output even when the
    exception is caught by a bare ``except Exception`` block.
    """
    pytester.makepyfile("""
        import socket

        def test_swallowed_socket(socket_disabled):
            try:
                socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            except Exception:
                pass  # swallow the error, simulating legacy code
        """)
    result = pytester.runpytest("-W", "always::UserWarning", "--disable-socket")
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines("*A test tried to use socket.socket.*")


def test_blocked_connect_emits_warning(pytester, httpserver):
    """Ensure SocketConnectBlockedError emits a warning before raising."""
    pytester.makepyfile(f"""
        import socket

        def test_swallowed_connect():
            try:
                socket.socket().connect(('{httpserver.host}', {httpserver.port}))
            except Exception:
                pass  # swallow the error
        """)
    result = pytester.runpytest("-W", "always::UserWarning", "--allow-hosts=1.2.3.4")
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines("*A test tried to use socket.socket.connect()*")


@unix_sockets_only
def test_unix_domain_sockets_blocked_with_disable_socket(pytester):
    pytester.makepyfile("""
        import socket

        def test_unix_socket():
            socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        """)
    result = pytester.runpytest("--disable-socket")
    assert_socket_blocked(result)


@unix_sockets_only
def test_enabling_unix_domain_sockets_with_disable_socket(pytester):
    pytester.makepyfile("""
        import socket

        def test_inet():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        def test_unix_socket():
            socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        """)
    result = pytester.runpytest("--disable-socket", "--allow-unix-socket")
    result.assert_outcomes(passed=1, skipped=0, failed=1)


def test_runtest_setup_skips_items_without_fixturenames():
    """Items lacking `fixturenames` (non-function tests) are skipped."""

    class FakeItem:
        pass

    assert pytest_runtest_setup(FakeItem()) is None


def test_host_from_address_non_string_returns_none():
    """A non-string host in the address tuple resolves to None."""
    assert host_from_address((123, 80)) is None


@unix_sockets_only
def test_disable_socket_blocks_unix_by_default():
    """disable_socket() with no arguments blocks Unix sockets too."""
    import socket

    disable_socket()
    try:
        with (
            pytest.raises(SocketBlockedError),
            pytest.warns(UserWarning, match="A test tried to use socket.socket."),
        ):
            socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    finally:
        enable_socket()


@unix_sockets_only
def test_disable_socket_marker_respects_allow_unix_socket(pytester):
    """The `disable_socket` marker honors `--allow-unix-socket`, passing the
    configured value through (not a hard-coded default)."""
    pytester.makepyfile("""
        import pytest
        import socket

        @pytest.mark.disable_socket
        def test_unix_socket():
            socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        """)
    result = pytester.runpytest("--allow-unix-socket")
    result.assert_outcomes(passed=1)


def test_socket_disabled_fixture_blocks_during_setup(pytester):
    """The socket_disabled fixture disables sockets early in setup, so a sibling
    fixture that opens a socket during its own setup is blocked too."""
    pytester.makepyfile("""
        import pytest
        import socket

        @pytest.fixture
        def network_fixture():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            yield

        def test_sibling(network_fixture, socket_disabled):
            pass
        """)
    result = pytester.runpytest()
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines("*SocketBlockedError*")
