"""Fixture teardown runs under the socket policy its setup ran under (#537)."""

import socket
from types import SimpleNamespace

import pytest

import pytest_socket

from .common import assert_host_blocked

PROBE = """
    import socket

    import pytest_socket


    def state(label):
        try:
            socket.socket().close()
            result = "open"
        except pytest_socket.SocketBlockedError:
            result = "blocked"
        print(f"{label}: {result}")
"""


def run(pytester, *args):
    return pytester.runpytest("-s", "-p", "no:randomly", *args)


@pytest.mark.parametrize("scope", ["function", "class", "module", "session"])
def test_fixture_teardown_runs_under_setup_policy(pytester, scope):
    pytester.makepyfile(
        probe=PROBE,
        test_scope=f"""
            import pytest
            from probe import state

            @pytest.fixture(scope="{scope}")
            def yielding():
                state("yield setup")
                yield
                state("yield teardown")

            @pytest.fixture(scope="{scope}")
            def finalizing(request):
                state("addfinalizer setup")
                request.addfinalizer(lambda: state("addfinalizer teardown"))

            class TestIt:
                def test_it(self, yielding, finalizing):
                    state("call")
        """,
    )
    result = run(pytester, "--disable-socket")
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(
        [
            "*yield setup: blocked*",
            "*addfinalizer setup: blocked*",
            "*call: blocked*",
            "*addfinalizer teardown: blocked*",
            "*yield teardown: blocked*",
        ]
    )
    result.stdout.no_fnmatch_line("*: open*")


def test_xunit_and_unittest_teardown_run_under_setup_policy(pytester):
    pytester.makepyfile(
        probe=PROBE,
        test_xunit="""
            import unittest
            from probe import state

            def setup_module():
                state("setup_module")

            def teardown_module():
                state("teardown_module")

            class TestCase(unittest.TestCase):
                @classmethod
                def setUpClass(cls):
                    state("setUpClass")

                @classmethod
                def tearDownClass(cls):
                    state("tearDownClass")

                def test_it(self):
                    state("call")
        """,
    )
    result = run(pytester, "--disable-socket")
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(
        ["*tearDownClass: blocked*", "*teardown_module: blocked*"]
    )
    result.stdout.no_fnmatch_line("*: open*")


@pytest.mark.parametrize(
    "first, expected",
    [("integration", "open"), ("unit", "blocked")],
)
def test_shared_fixture_teardown_follows_the_test_that_set_it_up(
    pytester, first, expected
):
    """The last test in a scope doesn't decide how the scope's fixtures tear
    down, so the outcome can't depend on test order."""
    tests = {
        "integration": """
            @pytest.mark.enable_socket
            def test_integration(service):
                pass
        """,
        "unit": """
            def test_unit(service):
                pass
        """,
    }
    second = "unit" if first == "integration" else "integration"
    pytester.makepyfile(
        probe=PROBE,
        test_order="""
            import pytest
            from probe import state

            @pytest.fixture(scope="session")
            def service():
                state("service setup")
                yield
                state("service teardown")
        """ + tests[first] + tests[second],
    )
    result = run(pytester, "--disable-socket")
    result.assert_outcomes(passed=2)
    result.stdout.fnmatch_lines(
        [f"*service setup: {expected}*", f"*service teardown: {expected}*"]
    )


def test_enable_socket_in_teardown_reaches_the_network(pytester):
    """The README's workaround for a fixture first set up by a blocked test."""
    pytester.makepyfile(
        probe=PROBE,
        test_workaround="""
            import pytest
            import pytest_socket
            from probe import state

            @pytest.fixture(scope="session")
            def service():
                yield
                pytest_socket.enable_socket()
                state("service teardown")

            def test_unit(service):
                pass

            @pytest.mark.enable_socket
            def test_integration(service):
                pass
        """,
    )
    result = run(pytester, "--disable-socket")
    result.assert_outcomes(passed=2)
    result.stdout.fnmatch_lines(["*service teardown: open*"])


def test_policy_changed_by_the_test_body_does_not_reach_earlier_fixtures(pytester):
    pytester.makepyfile(
        probe=PROBE,
        test_body="""
            import pytest
            import pytest_socket
            from probe import state

            @pytest.fixture
            def client():
                state("client setup")
                yield
                state("client teardown")

            def test_disables_midway(client):
                pytest_socket.disable_socket()
                state("call")

            def test_after():
                state("after")
        """,
    )
    result = run(pytester)
    result.assert_outcomes(passed=2)
    result.stdout.fnmatch_lines(
        [
            "*client setup: open*",
            "*call: blocked*",
            "*client teardown: open*",
            "*after: open*",
        ]
    )


@pytest.mark.parametrize("register", ["request.addfinalizer", "factory"])
def test_runtime_finalizers_run_before_cli_baseline_is_restored(pytester, register):
    pytester.makeconftest("""
        from probe import state

        def pytest_sessionfinish(session, exitstatus):
            state("sessionfinish")
        """)
    pytester.makepyfile(
        probe=PROBE,
        test_finalizer=f"""
            import pytest
            from probe import state

            @pytest.fixture
            def factory(request):
                return request.addfinalizer

            def test_it(request, factory):
                state("call")
                {register}(lambda: state("runtime finalizer"))
            """,
    )
    result = run(pytester, "--disable-socket")
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(
        [
            "*call: blocked*",
            "*runtime finalizer: open*",
            "*sessionfinish: blocked*",
        ]
    )


def test_allow_hosts_applies_to_fixture_teardown(pytester, httpserver):
    pytester.makepyfile(f"""
        import socket

        import pytest

        @pytest.fixture
        def dial_on_teardown():
            yield
            socket.create_connection(("{httpserver.host}", {httpserver.port})).close()

        def test_it(dial_on_teardown):
            pass
    """)
    result = pytester.runpytest("--allow-hosts=1.2.3.4")
    result.assert_outcomes(passed=1, errors=1)
    assert_host_blocked(result, httpserver.host)


def test_teardown_after_a_skipped_last_test_runs_under_setup_policy(pytester):
    pytester.makepyfile(
        probe=PROBE,
        test_skip="""
            import pytest
            from probe import state

            @pytest.fixture(scope="module")
            def resource():
                yield
                state("resource teardown")

            def test_uses(resource):
                pass

            @pytest.mark.skip
            def test_skipped():
                pass
        """,
    )
    result = run(pytester, "--disable-socket")
    result.assert_outcomes(passed=1, skipped=1)
    result.stdout.fnmatch_lines(["*resource teardown: blocked*"])


def test_teardown_deferred_by_exitfirst_runs_under_setup_policy(pytester):
    pytester.makepyfile(
        probe=PROBE,
        test_exitfirst="""
            import pytest
            from probe import state

            @pytest.fixture(scope="module")
            def resource():
                yield
                state("resource teardown")

            @pytest.fixture
            def broken():
                yield
                raise ValueError("teardown failed")

            def test_one(resource, broken):
                pass

            def test_two(resource):
                pass
        """,
    )
    result = run(pytester, "--disable-socket", "-x")
    result.assert_outcomes(passed=1, errors=1)
    result.stdout.fnmatch_lines(["*resource teardown: blocked*"])


def test_failing_teardown_does_not_leak_into_the_next_test(pytester):
    pytester.makepyfile(
        probe=PROBE,
        test_leak="""
            import pytest
            from probe import state

            @pytest.fixture
            def broken():
                yield
                state("broken teardown")
                raise ValueError("teardown failed")

            @pytest.mark.disable_socket
            def test_disabled(broken):
                pass

            def test_after():
                state("after")
        """,
    )
    result = run(pytester)
    result.assert_outcomes(passed=2, errors=1)
    result.stdout.fnmatch_lines(["*broken teardown: blocked*", "*after: open*"])


def test_failing_fixture_setup_wrapper_does_not_leak(pytester):
    """Another plugin's fixture setup wrapper raising must not leave a
    snapshot applied, on any pluggy version."""
    pytester.makeconftest("""
        import pytest

        @pytest.hookimpl(hookwrapper=True)
        def pytest_fixture_setup(fixturedef):
            outcome = yield
            if fixturedef.argname == "fragile":
                raise ValueError("wrapper failed")
    """)
    pytester.makepyfile(
        probe=PROBE,
        test_wrapper="""
            import pytest
            from probe import state

            @pytest.fixture
            def fragile():
                yield

            @pytest.mark.disable_socket
            def test_disabled(fragile):
                pass

            def test_after():
                state("after")
        """,
    )
    result = run(pytester)
    result.assert_outcomes(passed=1, errors=1)
    result.stdout.fnmatch_lines(["*after: open*"])


def test_abandoned_fixture_setup_wrapper_leaves_state_alone():
    """pluggy < 1.6 stops resuming outer wrappers once an inner one raises,
    so only the restore half is registered and it must do nothing."""
    finalizers = []
    wrapper = pytest_socket.pytest_fixture_setup(
        SimpleNamespace(addfinalizer=finalizers.append)
    )
    next(wrapper)
    pytest_socket.disable_socket()
    try:
        guarded = socket.socket
        for finalizer in reversed(finalizers):
            finalizer()
        assert socket.socket is guarded
    finally:
        pytest_socket.enable_socket()


def test_teardown_leaves_other_patches_of_socket_alone(pytester):
    """Patches from other tools, like monkeypatch, are theirs to undo."""
    pytester.makepyfile(test_monkeypatch="""
        import socket

        def fake_getaddrinfo(*args, **kwargs):
            return []

        def test_patch(monkeypatch):
            monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
            monkeypatch.setattr(socket, "socket", object)

        def test_after():
            assert socket.getaddrinfo is not fake_getaddrinfo
            assert socket.socket is not object
    """)
    for args in ([], ["--disable-socket"], ["--allow-hosts=1.2.3.4"]):
        result = run(pytester, *args)
        result.assert_outcomes(passed=2)


def test_teardown_brackets_finalizers_from_other_fixture_wrappers(pytester):
    """Finalizers another plugin's fixture setup wrapper registers run under
    the fixture's setup state too, so ours has to be the outermost wrapper."""
    pytester.makeconftest("""
        import pytest
        from probe import state

        @pytest.hookimpl(hookwrapper=True)
        def pytest_fixture_setup(fixturedef):
            yield
            if fixturedef.argname == "resource":
                fixturedef.addfinalizer(lambda: state("plugin finalizer"))
    """)
    pytester.makepyfile(
        probe=PROBE,
        test_plugin="""
            import pytest

            @pytest.fixture
            def resource():
                yield

            def test_it(resource):
                pass
        """,
    )
    result = run(pytester, "--disable-socket")
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(["*plugin finalizer: blocked*"])
