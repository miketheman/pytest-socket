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
