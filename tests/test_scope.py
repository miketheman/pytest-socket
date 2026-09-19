"""Where and when the restrictions apply.

Test scope (the default) guards each test's setup, call and teardown, fixture
finalizers included (#537). Session scope (``--socket-scope=session``) guards
the whole pytest run: conftest import, collection, session-scoped fixtures and
``pytest_sessionfinish`` (#539).
"""

import socket

import pytest

import pytest_socket

# Probes that report how a socket call ended without failing the inner test
# run, so one run can show the outcome of every phase at once. A *Blocked*
# name means the guard caught it.
#
# `create` only instantiates a socket: use it wherever `--disable-socket` is in
# play. `dial` connects to the outer suite's HTTP server: use it only where the
# connect guard (`--allow-hosts`) is the thing under test. Do not dial the
# server from a run that installs `GuardedSocket` in a neighbouring phase: the
# server thread's `accept()` looks up `socket.socket` too, and if it races the
# guard it dies and later `urlopen` tests in the outer suite hang.
PROBE = """
    import socket

    def create(label):
        try:
            socket.socket().close()
            print(f"{{label}}: created", flush=True)
        except Exception as exc:
            print(f"{{label}}: {{type(exc).__name__}}", flush=True)

    def dial(label):
        try:
            socket.create_connection(("{host}", {port}), timeout=5).close()
            print(f"{{label}}: connected", flush=True)
        except Exception as exc:
            print(f"{{label}}: {{type(exc).__name__}}", flush=True)
"""


@pytest.fixture
def probe(pytester, httpserver):
    """Write `probe.py` (importable from conftest and test modules) and return
    a helper that asserts a labelled phase's outcome."""
    pytester.makepyfile(probe=PROBE.format(host=httpserver.host, port=httpserver.port))

    def assert_phase(result, label, outcome):
        result.stdout.fnmatch_lines([f"*{label}: {outcome}"])

    return assert_phase


# --- Test scope: fixture teardown (#537) -----------------------------------


def test_fixture_teardown_is_restricted(pytester, probe):
    pytester.makepyfile("""
        import pytest
        from probe import dial

        @pytest.fixture
        def fixture():
            dial("setup")
            yield
            dial("teardown")

        def test_it(fixture):
            dial("call")
        """)
    result = pytester.runpytest("-s", "--disable-socket", "--allow-hosts=10.0.0.1")
    result.assert_outcomes(passed=1)
    probe(result, "setup", "SocketConnectBlockedError")
    probe(result, "call", "SocketConnectBlockedError")
    probe(result, "teardown", "SocketConnectBlockedError")


def test_session_fixture_teardown_is_restricted(pytester, probe):
    """The last test's teardown finalizes the session-scoped fixtures."""
    pytester.makepyfile("""
        import pytest
        from probe import create

        @pytest.fixture(scope="session")
        def sess():
            yield
            create("session teardown")

        def test_it(sess):
            pass
        """)
    result = pytester.runpytest("-s", "--disable-socket")
    result.assert_outcomes(passed=1)
    probe(result, "session teardown", "SocketBlockedError")


def test_teardown_runs_under_the_tests_own_rules(pytester, probe):
    """A test that enables sockets gets an enabled teardown, too."""
    pytester.makepyfile("""
        import pytest
        from probe import create

        @pytest.fixture
        def fixture():
            yield
            create("teardown")

        def test_it(fixture, socket_enabled):
            pass
        """)
    result = pytester.runpytest("-s", "--disable-socket")
    result.assert_outcomes(passed=1)
    probe(result, "teardown", "created")


def test_restrictions_reset_after_teardown_error(pytester, probe):
    """A finalizer that raises must not leak the previous test's restrictions
    into the next test. (A plain `trylast` teardown hook would be skipped when
    pytest's own teardown hook raises, leaving the connect guard installed.)"""
    pytester.makepyfile("""
        import pytest
        from probe import dial

        @pytest.fixture
        def broken_teardown():
            yield
            raise RuntimeError("teardown boom")

        def test_a(broken_teardown):
            pass

        def test_b(socket_enabled):
            dial("next test")
        """)
    result = pytester.runpytest("-s", "-p", "no:randomly", "--allow-hosts=10.0.0.1")
    result.assert_outcomes(passed=2, errors=1)
    probe(result, "next test", "connected")


def test_xunit_teardown_module_is_restricted(pytester, probe):
    pytester.makepyfile("""
        from probe import create

        def teardown_module():
            create("teardown_module")

        def test_it():
            pass
        """)
    result = pytester.runpytest("-s", "--disable-socket")
    result.assert_outcomes(passed=1)
    probe(result, "teardown_module", "SocketBlockedError")


# --- Test scope is the default, and leaves the rest of the run alone --------


def test_test_scope_only_guards_tests(pytester, probe):
    pytester.makeconftest("""
        from probe import create

        create("conftest import")

        def pytest_sessionfinish(session, exitstatus):
            create("sessionfinish")
        """)
    pytester.makepyfile("""
        from probe import create

        create("module import")

        def test_it():
            create("call")
        """)
    result = pytester.runpytest("-s", "--disable-socket")
    result.assert_outcomes(passed=1)
    probe(result, "conftest import", "created")
    probe(result, "module import", "created")
    probe(result, "call", "SocketBlockedError")
    probe(result, "sessionfinish", "created")


# --- Session scope (#539) ---------------------------------------------------


def test_session_scope_guards_the_whole_run(pytester, probe):
    pytester.makeconftest("""
        from probe import create

        create("conftest import")

        def pytest_collection_finish(session):
            create("collection_finish")

        def pytest_sessionfinish(session, exitstatus):
            create("sessionfinish")
        """)
    pytester.makepyfile("""
        import pytest
        from probe import create

        create("module import")

        @pytest.fixture(scope="session")
        def sess():
            create("session setup")
            yield
            create("session teardown")

        def test_it(sess):
            create("call")
        """)
    result = pytester.runpytest("-s", "--disable-socket", "--socket-scope=session")
    result.assert_outcomes(passed=1)
    for phase in (
        "conftest import",
        "module import",
        "collection_finish",
        "session setup",
        "call",
        "session teardown",
        "sessionfinish",
    ):
        probe(result, phase, "SocketBlockedError")


def test_session_scope_via_addopts(pytester, probe):
    pytester.makeini("""
        [pytest]
        addopts = --disable-socket --socket-scope=session
        """)
    pytester.makeconftest("""
        from probe import create

        create("conftest import")
        """)
    pytester.makepyfile("""
        def test_it():
            pass
        """)
    result = pytester.runpytest("-s")
    result.assert_outcomes(passed=1)
    probe(result, "conftest import", "SocketBlockedError")


def test_session_scope_allow_hosts_applies_outside_tests(pytester, probe, httpserver):
    pytester.makeconftest("""
        from probe import dial

        def pytest_sessionfinish(session, exitstatus):
            dial("sessionfinish")
        """)
    pytester.makepyfile("""
        def test_it():
            pass
        """)
    blocked = pytester.runpytest(
        "-s", "--allow-hosts=10.0.0.1", "--socket-scope=session"
    )
    blocked.assert_outcomes(passed=1)
    probe(blocked, "sessionfinish", "SocketConnectBlockedError")

    allowed = pytester.runpytest(
        "-s", f"--allow-hosts={httpserver.host}", "--socket-scope=session"
    )
    allowed.assert_outcomes(passed=1)
    probe(allowed, "sessionfinish", "connected")


def test_session_scope_per_test_overrides_still_apply(pytester, probe):
    """Markers and fixtures override the baseline for their test only; the
    baseline comes back for everything after."""
    pytester.makeconftest("""
        from probe import create

        def pytest_sessionfinish(session, exitstatus):
            create("sessionfinish")
        """)
    pytester.makepyfile("""
        import pytest
        from probe import create, dial

        def test_fixture(socket_enabled):
            create("fixture")

        @pytest.mark.enable_socket
        def test_marker():
            create("marker")

        @pytest.mark.allow_hosts(["10.0.0.1"])
        def test_allow_hosts_marker():
            dial("allow_hosts")

        def test_plain():
            create("plain")
        """)
    result = pytester.runpytest("-s", "--disable-socket", "--socket-scope=session")
    result.assert_outcomes(passed=4)
    probe(result, "fixture", "created")
    probe(result, "marker", "created")
    probe(result, "allow_hosts", "SocketConnectBlockedError")
    probe(result, "plain", "SocketBlockedError")
    probe(result, "sessionfinish", "SocketBlockedError")


def test_session_scope_force_enable_wins(pytester, probe):
    pytester.makeconftest("""
        from probe import create

        create("conftest import")
        """)
    pytester.makepyfile("""
        from probe import create

        def test_it():
            create("call")
        """)
    result = pytester.runpytest(
        "-s", "--disable-socket", "--force-enable-socket", "--socket-scope=session"
    )
    result.assert_outcomes(passed=1)
    probe(result, "conftest import", "created")
    probe(result, "call", "created")


def test_session_scope_finalizers_after_maxfail(pytester, probe):
    """After a teardown error under `-x`, pytest finalizes the remaining
    fixtures in `pytest_sessionfinish`; session scope still guards them."""
    pytester.makepyfile("""
        import pytest
        from probe import create

        @pytest.fixture(scope="session")
        def sess():
            yield
            create("late finalizer")

        @pytest.fixture
        def broken_teardown():
            yield
            raise RuntimeError("teardown boom")

        def test_a(sess, broken_teardown):
            pass

        def test_b(sess):
            pass
        """)
    result = pytester.runpytest(
        "-s", "-x", "-p", "no:randomly", "--disable-socket", "--socket-scope=session"
    )
    result.assert_outcomes(passed=1, errors=1)
    probe(result, "late finalizer", "SocketBlockedError")


def test_session_scope_is_undone_at_unconfigure(pytester):
    """An in-process run (pytester, `pytest.main()`) must hand back the real
    socket module when it finishes."""
    pytester.makepyfile("""
        def test_it():
            pass
        """)
    result = pytester.runpytest("--disable-socket", "--socket-scope=session")
    result.assert_outcomes(passed=1)
    assert socket.socket is pytest_socket._true_socket
    assert socket.socket.connect is pytest_socket._true_connect
    assert socket.getaddrinfo is pytest_socket._true_getaddrinfo


def test_session_scope_with_doctests(pytester):
    pytester.makepyfile('''
        def my_sum(a, b):
            """
            >>> my_sum(1, 1)
            2
            """
            return a + b
        ''')
    result = pytester.runpytest(
        "--doctest-modules", "--disable-socket", "--socket-scope=session"
    )
    result.assert_outcomes(passed=1)


def test_help_lists_socket_scope(pytester):
    result = pytester.runpytest("--help")
    result.stdout.fnmatch_lines(["*--socket-scope={test,session}*"])
