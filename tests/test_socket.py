# -*- coding: utf-8 -*-
import pytest

from pytest_socket import enable_socket
from socket import gethostbyname

real_http_ip_host = gethostbyname('httpbin.org')
real_http_ip_url = 'http://{0}/get'.format(real_http_ip_host)

real_http_hostname_host = 'httpbin.org'
real_http_hostname_url = 'http://{0}/get'.format(real_http_hostname_host)


@pytest.fixture(autouse=True)
def reenable_socket():
    # The tests can leave the socket disabled in the global scope.
    # Fix that by automatically re-enabling it after each test
    yield
    enable_socket()


def assert_socket_blocked(result):
    result.stdout.fnmatch_lines("""
        *A test tried to use socket.socket.connect() with host*
    """)


def test_socket_enabled_by_default(testdir):
    testdir.makepyfile("""
        import socket

        def test_socket():
            socket.socket().connect(('{0}', 80))
    """.format(real_http_hostname_host))
    result = testdir.runpytest("--verbose")
    result.assert_outcomes(1, 0, 0)
    with pytest.raises(BaseException):
        assert_socket_blocked(result)


def test_global_disable_via_fixture(testdir):
    testdir.makepyfile("""
        import pytest
        import pytest_socket
        import socket

        @pytest.fixture(autouse=True)
        def disable_socket_for_all():
            pytest_socket.disable_socket()

        def test_socket():
            socket.socket().connect(('{0}', 80))
    """.format(real_http_hostname_host))
    result = testdir.runpytest("--verbose")
    result.assert_outcomes(0, 0, 1)
    assert_socket_blocked(result)


def test_global_disable_via_cli_flag(testdir):
    testdir.makepyfile("""
        import socket

        def test_socket():
            socket.socket().connect(('{0}', 80))
    """.format(real_http_hostname_host))
    result = testdir.runpytest("--verbose", "--disable-socket")
    result.assert_outcomes(0, 0, 1)
    assert_socket_blocked(result)


def test_help_message(testdir):
    result = testdir.runpytest(
        '--help',
    )
    result.stdout.fnmatch_lines([
        'socket:',
        '*--disable-socket=[[]ALLOWED_HOSTS_CSV[]]',
        '*Intercept socket.socket.connect() to block network',
        '*calls (except those optionally specified as CSV',
        '*argument).'
    ])


def test_marker_help_message(testdir):
    result = testdir.runpytest(
        '--markers',
    )
    result.stdout.fnmatch_lines([
        '@pytest.mark.disable_socket([[]allowed_hosts[]]): Disable socket connections for a specific test ' +
        '(with optional allowed list of hosts)',
        '@pytest.mark.enable_socket(): Enable socket connections for a specific test'
    ])


def test_fixtures_help_message(testdir):
    result = testdir.runpytest(
        '--fixtures',
    )
    result.stdout.fnmatch_lines([
        'socket_disabled',
        '*disable socket.socket.connect() for duration of this test function',
        'socket_enabled',
        '*enable socket.socket.connect() for duration of this test function'
    ])


def test_global_disable_via_config(testdir):
    testdir.makepyfile("""
        import socket

        def test_socket():
            socket.socket().connect(('{0}', 80))
    """.format(real_http_hostname_host))
    testdir.makeini("""
        [pytest]
        addopts = --disable-socket
    """)
    result = testdir.runpytest("--verbose")
    result.assert_outcomes(0, 0, 1)
    assert_socket_blocked(result)


def test_disable_socket_marker(testdir):
    testdir.makepyfile("""
        import pytest
        import socket

        @pytest.mark.disable_socket
        def test_socket():
            socket.socket().connect(('{0}', 80))
    """.format(real_http_hostname_host))
    result = testdir.runpytest("--verbose")
    result.assert_outcomes(0, 0, 1)
    assert_socket_blocked(result)


def test_enable_socket_marker(testdir):
    testdir.makepyfile("""
        import pytest
        import socket

        @pytest.mark.enable_socket
        def test_socket():
            socket.socket().connect(('{0}', 80))
    """.format(real_http_hostname_host))
    result = testdir.runpytest("--verbose", "--disable-socket")
    result.assert_outcomes(0, 0, 1)
    assert_socket_blocked(result)


def test_urllib_succeeds_by_default(testdir):
    testdir.makepyfile("""
        try:
            from urllib.request import urlopen, Request
        except ImportError:
            from urllib2 import urlopen, Request

        def test_disable_socket_urllib_default_succeeds():
            assert urlopen('{0}').getcode() == 200
    """.format(real_http_hostname_url))
    result = testdir.runpytest("--verbose")
    result.assert_outcomes(1, 0, 0)


def test_enabled_urllib_succeeds(testdir):
    testdir.makepyfile("""
        import pytest
        import pytest_socket
        try:
            from urllib.request import urlopen, Request
        except ImportError:
            from urllib2 import urlopen, Request

        @pytest.mark.enable_socket
        def test_disable_socket_urllib_succeeds():
            assert urlopen('{0}').getcode() == 200
    """.format(real_http_hostname_url))
    result = testdir.runpytest("--verbose", "--disable-socket")
    result.assert_outcomes(0, 0, 1)
    assert_socket_blocked(result)


def test_disabled_urllib_fails(testdir):
    testdir.makepyfile("""
        import pytest
        try:
            from urllib.request import urlopen, Request
        except ImportError:
            from urllib2 import urlopen, Request

        @pytest.mark.disable_socket
        def test_disable_socket_urllib_fails():
            assert urlopen('{0}').getcode() == 200
    """.format(real_http_hostname_url))
    result = testdir.runpytest("--verbose")
    result.assert_outcomes(0, 0, 1)
    assert_socket_blocked(result)


def test_exception_urllib_fails(testdir):
    testdir.makepyfile("""
        import pytest
        try:
            from urllib.request import urlopen, Request
        except ImportError:
            from urllib2 import urlopen, Request

        @pytest.mark.disable_socket('{1}')
        def test_disable_socket_urllib():
            assert urlopen(Request('{0}', headers={{'Host': 'httpbin.org'}})).getcode() == 200
    """.format(real_http_ip_url, '1.1.1.1'))
    result = testdir.runpytest("--verbose")
    result.assert_outcomes(0, 0, 1)
    assert_socket_blocked(result)


def test_exception_urllib_passes(testdir):
    testdir.makepyfile("""
        import pytest
        try:
            from urllib.request import urlopen, Request
        except ImportError:
            from urllib2 import urlopen, Request

        @pytest.mark.disable_socket('{1}')
        def test_disable_socket_urllib():
            assert urlopen(Request('{0}', headers={{'Host': 'httpbin.org'}})).getcode() == 200
    """.format(real_http_ip_url, real_http_ip_host))
    result = testdir.runpytest("--verbose")
    result.assert_outcomes(1, 0, 0)


def test_exception_cli_passes(testdir):
    testdir.makepyfile("""
        import socket

        def test_socket():
            socket.socket().connect(('{0}', 80))
    """.format(real_http_ip_host))
    result = testdir.runpytest("--verbose", "--disable-socket={0}".format(real_http_ip_host))
    result.assert_outcomes(1, 0, 0)


def test_multiple_exception_cli_passes(testdir):
    testdir.makepyfile("""
        import socket

        def test_socket():
            socket.socket().connect(('{0}', 80))
    """.format(real_http_ip_host))
    result = testdir.runpytest("--verbose", "--disable-socket={0}".format(real_http_ip_host + ',1.1.1.1'))
    result.assert_outcomes(1, 0, 0)


def test_exception_cli_fails(testdir):
    testdir.makepyfile("""
        import socket

        def test_socket():
            socket.socket().connect(('{0}', 80))
    """.format(real_http_ip_host))
    result = testdir.runpytest("--verbose", "--disable-socket={0}".format('2.2.2.2'))
    result.assert_outcomes(0, 0, 1)
    assert_socket_blocked(result)


def test_multiple_exception_cli_fails(testdir):
    testdir.makepyfile("""
        import socket

        def test_socket():
            socket.socket().connect(('{0}', 80))
    """.format(real_http_ip_host))
    result = testdir.runpytest("--verbose", "--disable-socket={0}".format('2.2.2.2,1.1.1.1'))
    result.assert_outcomes(0, 0, 1)
    assert_socket_blocked(result)


def test_double_call_does_nothing(testdir):
    testdir.makepyfile("""
        import pytest
        import pytest_socket
        import socket

        def test_double_enabled():
            pytest_socket.enable_socket()
            pytest_socket.enable_socket()
            socket.socket().connect(('{0}', 80))

        def test_double_disabled():
            pytest_socket.disable_socket()
            pytest_socket.disable_socket()
            with pytest.raises(pytest_socket.SocketBlockedError):
                socket.socket().connect(('{0}', 80))

        def test_disable_enable():
            pytest_socket.disable_socket()
            pytest_socket.enable_socket()
            socket.socket().connect(('{0}', 80))
    """.format(real_http_hostname_host))
    result = testdir.runpytest("--verbose")
    result.assert_outcomes(3, 0, 0)
    with pytest.raises(BaseException):
        assert_socket_blocked(result)


def test_socket_enabled_fixture(testdir):
    testdir.makepyfile("""
        import socket
        def test_socket_enabled(socket_enabled):
            socket.socket().connect(('{0}', 80))
    """.format(real_http_hostname_host))
    result = testdir.runpytest("--verbose")
    result.assert_outcomes(1, 0, 0)
    with pytest.raises(BaseException):
        assert_socket_blocked(result)


def test_mix_and_match(testdir):
    testdir.makepyfile("""
        import socket

        def test_socket1():
            socket.socket().connect(('{0}', 80))
        def test_socket_enabled(socket_enabled):
            socket.socket().connect(('{0}', 80))
        def test_socket2():
            socket.socket().connect(('{0}', 80))
    """.format(real_http_hostname_host))
    result = testdir.runpytest("--verbose", "--disable-socket")
    result.assert_outcomes(1, 0, 2)
