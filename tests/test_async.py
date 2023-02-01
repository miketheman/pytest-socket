from conftest import unix_sockets_only
from test_socket import assert_socket_blocked


@unix_sockets_only
def test_asynctest(testdir):
    testdir.makepyfile(
        """
        import socket
        import asynctest


        class AnExampleWithTestCaseAndCoroutines(asynctest.TestCase):
            async def a_coroutine(self):
                return "I worked"

            async def test_that_a_coroutine_runs(self):
                self.assertIn("worked", await self.a_coroutine())

            async def test_inet_is_blocked(self):
                socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """
    )
    result = testdir.runpytest("--disable-socket", "--allow-unix-socket")
    result.assert_outcomes(passed=1, skipped=0, failed=1)


@unix_sockets_only
def test_starlette(testdir):
    testdir.makepyfile(
        """
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
        """
    )
    result = testdir.runpytest("--disable-socket", "--allow-unix-socket")
    result.assert_outcomes(passed=1, skipped=0, failed=0)


@unix_sockets_only
def test_httpx_fails(testdir):
    testdir.makepyfile(
        """
        import pytest
        import httpx


        @pytest.fixture(autouse=True)
        def anyio_backend():
            return "asyncio"

        async def test_httpx():
            async with httpx.AsyncClient() as client:
                await client.get("http://www.example.com/")
        """
    )
    result = testdir.runpytest("--disable-socket", "--allow-unix-socket")
    assert_socket_blocked(result)
