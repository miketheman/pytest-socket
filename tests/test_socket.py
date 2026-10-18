import pickle
import warnings

import pytest

from pytest_socket import (
    SocketBlockedError,
    SocketConnectBlockedError,
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


@pytest.mark.parametrize(
    "call, arg, name",
    [
        ("socket.socket()", "--disable-socket", "socket.socket."),
        (
            "socket.socket().connect(('1.1.1.1', 80))",
            "--allow-hosts=127.0.0.1",
            "socket.socket.connect()",
        ),
    ],
    ids=["socket", "connect"],
)
def test_blocked_call_emits_warning(pytester, call, arg, name):
    """A blocked call warns before raising, so it stays visible in the output
    even when the code under test swallows the exception."""
    pytester.makepyfile(f"""
        import socket

        def test_swallowed():
            try:
                {call}
            except Exception:
                pass
        """)
    result = pytester.runpytest("-W", "always::UserWarning", arg)
    result.assert_outcomes(passed=1, warnings=1)
    result.stdout.fnmatch_lines(f"*SocketBlockedWarning: A test tried to use {name}*")


SWALLOWED_WITH_UNRELATED_WARNING = """
    import socket
    import warnings

    def test_filtered(socket_disabled):
        warnings.warn("unrelated")
        try:
            socket.socket()
        except Exception:
            pass
    """


def test_block_warning_category_can_be_filtered(pytester):
    """Filtering SocketBlockedWarning hides only the block warning."""
    pytester.makepyfile(SWALLOWED_WITH_UNRELATED_WARNING)
    result = pytester.runpytest("-W", "always::UserWarning")
    result.assert_outcomes(passed=1, warnings=2)
    result.stdout.fnmatch_lines("*SocketBlockedWarning: A test tried*")

    result = pytester.runpytest(
        "-W", "always::UserWarning", "-W", "ignore::pytest_socket.SocketBlockedWarning"
    )
    result.assert_outcomes(passed=1, warnings=1)
    result.stdout.fnmatch_lines("*UserWarning: unrelated*")
    result.stdout.no_fnmatch_line("*A test tried*")


def test_blocked_call_raises_with_warnings_as_errors(pytester):
    """With warnings as errors, ignoring the block warning lets tests still
    assert on the plugin's exception."""
    pytester.makepyfile("""
        import pytest
        import socket
        from pytest_socket import SocketBlockedError

        def test_blocked(socket_disabled):
            with pytest.raises(SocketBlockedError):
                socket.socket()
        """)
    result = pytester.runpytest(
        "-W", "error", "-W", "ignore::pytest_socket.SocketBlockedWarning"
    )
    result.assert_outcomes(passed=1)


def test_constructing_exceptions_does_not_warn():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        SocketBlockedError()
        SocketConnectBlockedError(["127.0.0.1"], "192.0.80.239")


@pytest.mark.parametrize(
    "exc",
    [
        pytest.param(SocketBlockedError(), id="SocketBlockedError"),
        pytest.param(
            SocketConnectBlockedError(["0.0.0.0", "127.0.0.1"], "192.0.80.239"),
            id="SocketConnectBlockedError",
        ),
    ],
)
def test_exceptions_are_pickleable(exc):
    """Exceptions must survive a pickle round-trip.

    Multiprocessing test runners (Django's ``--parallel``, pytest-xdist)
    serialize exceptions across process boundaries; a non-pickleable
    exception masks the real failure with a confusing ``TypeError``.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        restored = pickle.loads(pickle.dumps(exc))
    assert type(restored) is type(exc)
    assert restored.args == exc.args


def test_connect_blocked_error_preserves_context_when_pickleable():
    """Pickling must retain the host and allowlist in the error message."""
    exc = SocketConnectBlockedError(["127.0.0.1", "::1"], "192.0.80.239")

    restored = pickle.loads(pickle.dumps(exc))

    assert str(restored) == str(exc)


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


@pytest.mark.parametrize("scope", ["function", "class", "module", "session"])
@pytest.mark.parametrize(
    "use_addfinalizer", [False, True], ids=["yield", "addfinalizer"]
)
def test_global_disable_remains_active_during_fixture_teardown(
    pytester, scope, use_addfinalizer
):
    """Fixture finalizers at every scope remain covered by --disable-socket."""
    teardown = (
        'request.addfinalizer(lambda: print("teardown:", socket_state()))'
        if use_addfinalizer
        else 'yield\n            print("teardown:", socket_state())'
    )
    pytester.makepyfile(f"""
        import socket
        import pytest

        def socket_state():
            try:
                sock = socket.socket()
            except RuntimeError:
                return "blocked"
            else:
                sock.close()
                return "open"

        @pytest.fixture(scope="{scope}")
        def check_socket(request):
            print("setup:", socket_state())
            {teardown}

        class TestSocket:
            def test_socket(self, check_socket):
                print("call:", socket_state())
    """)
    result = pytester.runpytest("--disable-socket", "-s", "-p", "no:randomly")
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(
        ["*setup: blocked*", "*call: blocked*", "*teardown: blocked*"]
    )


def test_restrictions_remain_through_failing_teardown(pytester):
    pytester.makepyfile("""
        import socket
        import pytest

        def socket_state():
            try:
                sock = socket.socket()
            except RuntimeError:
                return "blocked"
            else:
                sock.close()
                return "open"

        @pytest.fixture
        def failing_teardown(request):
            def finalize():
                print("teardown:", socket_state())
                raise ValueError("teardown failed")
            request.addfinalizer(finalize)

        @pytest.mark.disable_socket
        def test_socket(failing_teardown):
            pass

        def test_next_test_is_not_left_restricted():
            print("next test:", socket_state())
    """)
    result = pytester.runpytest("-s", "-p", "no:randomly")
    result.assert_outcomes(passed=2, errors=1)
    result.stdout.fnmatch_lines(["*teardown: blocked*", "*next test: open*"])


def test_restrictions_remain_until_other_teardown_wrappers_finish(pytester):
    pytester.makeconftest("""
        import socket
        import pytest

        @pytest.hookimpl(hookwrapper=True)
        def pytest_runtest_teardown(item):
            yield
            try:
                sock = socket.socket()
            except RuntimeError:
                print("other wrapper: blocked")
            else:
                sock.close()
                print("other wrapper: open")
    """)
    pytester.makepyfile("""
        import pytest

        @pytest.fixture
        def fixture():
            yield
            print("fixture teardown")

        def test_socket(fixture):
            pass
    """)
    result = pytester.runpytest("--disable-socket", "-s", "-p", "no:randomly")
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(["*fixture teardown*", "*other wrapper: blocked*"])


def test_consecutive_markers_keep_each_tests_socket_policy_in_teardown(pytester):
    pytester.makepyfile("""
        import socket
        import pytest

        def socket_state():
            try:
                sock = socket.socket()
            except RuntimeError:
                return "blocked"
            else:
                sock.close()
                return "open"

        @pytest.fixture
        def observe_socket(request):
            name = request.node.name
            print("setup", name, socket_state())
            yield
            print("teardown", name, socket_state())

        @pytest.mark.enable_socket
        def test_enabled(observe_socket):
            print("call", "test_enabled", socket_state())

        @pytest.mark.disable_socket
        def test_disabled(observe_socket):
            print("call", "test_disabled", socket_state())

        def test_default(observe_socket):
            print("call", "test_default", socket_state())
    """)
    result = pytester.runpytest("--disable-socket", "-s", "-p", "no:randomly")
    result.assert_outcomes(passed=3)
    result.stdout.fnmatch_lines(
        [
            "*setup test_enabled open*",
            "*call test_enabled open*",
            "*teardown test_enabled open*",
            "*setup test_disabled blocked*",
            "*call test_disabled blocked*",
            "*teardown test_disabled blocked*",
            "*setup test_default blocked*",
            "*call test_default blocked*",
            "*teardown test_default blocked*",
        ]
    )


def test_socket_enable_and_disable_fixtures_keep_policy_in_teardown(pytester):
    pytester.makepyfile("""
        import socket
        import pytest

        def socket_state():
            try:
                sock = socket.socket()
            except RuntimeError:
                return "blocked"
            else:
                sock.close()
                return "open"

        @pytest.fixture
        def observe_enabled(socket_enabled, request):
            print("setup", request.node.name, socket_state())
            yield
            print("teardown", request.node.name, socket_state())

        @pytest.fixture
        def observe_disabled(socket_disabled, request):
            print("setup", request.node.name, socket_state())
            yield
            print("teardown", request.node.name, socket_state())

        @pytest.fixture
        def observe_default(request):
            print("setup", request.node.name, socket_state())
            yield
            print("teardown", request.node.name, socket_state())

        def test_enabled_fixture(observe_enabled):
            print("call", "test_enabled_fixture", socket_state())

        def test_disabled_fixture(observe_disabled):
            print("call", "test_disabled_fixture", socket_state())

        def test_default_fixture(observe_default):
            print("call", "test_default_fixture", socket_state())
    """)
    result = pytester.runpytest("-s", "-p", "no:randomly")
    result.assert_outcomes(passed=3)
    result.stdout.fnmatch_lines(
        [
            "*setup test_enabled_fixture open*",
            "*call test_enabled_fixture open*",
            "*teardown test_enabled_fixture open*",
            "*setup test_disabled_fixture blocked*",
            "*call test_disabled_fixture blocked*",
            "*teardown test_disabled_fixture blocked*",
            "*setup test_default_fixture open*",
            "*call test_default_fixture open*",
            "*teardown test_default_fixture open*",
        ]
    )


def test_allow_hosts_restriction_remains_active_in_fixture_teardown(pytester):
    pytester.makepyfile("""
        import socket
        import pytest

        def connection_state():
            try:
                with socket.socket() as sock:
                    sock.connect(("0.0.0.0", 0))
            except RuntimeError:
                return "blocked"
            except OSError:
                return "open"
            return "open"

        @pytest.fixture
        def check_connection():
            yield
            print("teardown:", connection_state())

        def test_connection(check_connection):
            print("call:", connection_state())
    """)
    result = pytester.runpytest("--allow-hosts=127.0.0.1", "-s", "-p", "no:randomly")
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(["*call: blocked*", "*teardown: blocked*"])
