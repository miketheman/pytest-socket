"""Test module to express odd combinations of configurations."""


def test_parametrize_with_socket_enabled_and_allow_hosts(testdir, httpbin):
    """This is a complex test that demonstrates the use of `parametrize`,
    `enable_socket` fixture, allow_hosts CLI flag.

    TODO: This test makes real http calls. httpbin only provides a single IP.
    Is there a better way to express multiple **working** IPs?

    From: https://github.com/miketheman/pytest-socket/issues/56
    """
    testdir.makepyfile(
        f"""
        import pytest
        import requests


        @pytest.mark.parametrize(
            "url",
            [
                "https://google.com",
                "https://amazon.com",
                "https://microsoft.com",
            ],
        )
        def test_domain(url, socket_enabled):
            requests.get(url)

        def test_localhost_works():
            requests.get("{httpbin.url}/")

        def test_remote_not_allowed_fails():
            requests.get("http://172.1.1.1/")
        """
    )
    testdir.makeini(
        f"""
        [pytest]
        addopts = --disable-socket --allow-hosts={httpbin.host}
        """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=4, failed=1)
    result.stdout.fnmatch_lines(
        "*SocketConnectBlockedError: A test tried to use socket.socket.connect() with host*"
    )
