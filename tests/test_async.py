import socket

import pytest


unix_sockets_only = pytest.mark.skipif(
    not hasattr(socket, "AF_UNIX"),
    reason="Skip any platform that does not support AF_UNIX",
)


@unix_sockets_only
def test_asynctest(testdir):
    testdir.makepyfile("""
        import asynctest


        class AnExampleWithTestCaseAndCoroutines(asynctest.TestCase):
            async def a_coroutine(self):
                return "I worked"

            async def test_that_a_coroutine_runs(self):
                self.assertIn("worked", await self.a_coroutine())

            async def test_inet_is_blocked(self):
                socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    """)
    result = testdir.runpytest("--verbose", "--disable-socket", "--allow-unix-socket")
    result.assert_outcomes(passed=1, skipped=0, failed=1)


@unix_sockets_only
def test_starlette(testdir):
    testdir.makepyfile("""
        from pytest_socket import disable_socket
        from starlette.responses import HTMLResponse
        from starlette.testclient import TestClient


        def pytest_runtest_setup():
            disable_socket()


        async def app(scope, receive, send):
            assert scope['type'] == 'http'
            response = HTMLResponse('<html><body>Hello, world!</body></html>')
            await response(scope, receive, send)


        def test_app():
            client = TestClient(app)
            response = client.get('/')
            assert response.status_code == 200
    """)
    result = testdir.runpytest("--verbose", "--disable-socket", "--allow-unix-socket")
    result.assert_outcomes(passed=1, skipped=0, failed=0)


@unix_sockets_only
def test_allow_unix_socket_connections(testdir):
    # Check that the --allow-unix-socket cli arg works for socket.connect
    testdir.makepyfile("""
        import pytest
        import socket
        import multiprocessing

        def test_pass_with_cli_arg():
            manager = multiprocessing.Manager()
            lst = manager.list([1, 2, 3])
    """)
    result = testdir.runpytest("--verbose", "--allow-hosts=1.2.3.4", "--allow-unix-socket")
    result.assert_outcomes(passed=1, skipped=0, failed=0)

    # Check that the allow_unix_socket mark works for socket.connect
    testdir.makepyfile("""
        import pytest
        import socket
        import multiprocessing

        @pytest.mark.allow_unix_socket
        def test_pass_with_pytest_mark():
            manager = multiprocessing.Manager()
            lst = manager.list([1, 2, 3])

        def test_fail_without_pytest_mark():
            manager = multiprocessing.Manager()
            lst = manager.list([1, 2, 3])
    """)
    result = testdir.runpytest("--verbose", "--allow-hosts=1.2.3.4")
    result.assert_outcomes(passed=1, skipped=0, failed=1)
    result.stdout.fnmatch_lines('*A test tried to use socket.socket.connect() with host*')


@unix_sockets_only
def test_unix_socket_connections_name_specified(testdir, tmp_path):

    unix_socket_file_path = tmp_path / "test_unix_socket.s"

    # Check that the --allow-hosts cli arg works for socket.connect of AF_UNIX socket
    testdir.makepyfile("""
        import pytest
        import socket

        def test_pass_with_host_allowed():
            test_socket_server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            test_socket_server.bind("{0}")
            test_socket_server.listen()

            test_socket_client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            test_socket_client.connect("{0}")

        def test_fail_with_bad_host():
            test_socket_client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            test_socket_client.connect("/tmp/fake_socket_name.s")

    """.format(unix_socket_file_path))
    result = testdir.runpytest("--verbose", "--allow-hosts={0}".format(unix_socket_file_path))
    result.assert_outcomes(passed=1, skipped=0, failed=1)
    result.stdout.fnmatch_lines('*A test tried to use socket.socket.connect() with host "/tmp/fake_socket_name.s"*')
