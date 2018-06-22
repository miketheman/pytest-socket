# -*- coding: utf-8 -*-
import pytest

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

import inspect


localhost = '127.0.0.1'

connect_code_template = """
    import socket
    import pytest

    {3}
    def {2}():
        socket.socket().connect(('{0}', {1}))
"""

urlopen_code_template = """
    import pytest
    try:
        from urllib.request import urlopen
    except ImportError:
        from urllib2 import urlopen

    {3}
    def {2}():
        assert urlopen('http://{0}:{1}/').getcode() == 200
"""


def assert_host_blocked(result, host):
    result.stdout.fnmatch_lines('*A test tried to use socket.socket.connect() with host "{0}"*'.format(host))


@pytest.fixture
def assert_connect(httpserver, testdir):
    def assert_socket_connect(should_pass, **kwargs):
        # get the name of the calling function
        test_name = inspect.stack()[1][3]
        httpserver.serve_content('ok')
        test_url = urlparse(httpserver.url)

        mark = ''
        cli_arg = kwargs.get('cli_arg', None)
        code_template = kwargs.get('code_template', connect_code_template)
        mark_arg = kwargs.get('mark_arg', None)

        if mark_arg and isinstance(mark_arg, str):
            mark = '@pytest.mark.restrict_hosts("{0}")'.format(mark_arg)
        elif mark_arg and isinstance(mark_arg, list):
            mark = '@pytest.mark.restrict_hosts(["{0}"])'.format('","'.join(mark_arg))
        code = code_template.format(test_url.hostname, test_url.port, test_name, mark)
        testdir.makepyfile(code)

        if cli_arg:
            result = testdir.runpytest("--verbose", '--restrict-hosts={0}'.format(cli_arg))
        else:
            result = testdir.runpytest("--verbose")

        if should_pass:
            result.assert_outcomes(1, 0, 0)
        else:
            result.assert_outcomes(0, 0, 1)
            assert_host_blocked(result, test_url.hostname)
    return assert_socket_connect


def test_help_message(testdir):
    result = testdir.runpytest(
        '--help',
    )
    result.stdout.fnmatch_lines([
        'socket:',
        '*--restrict-hosts=ALLOWED_HOSTS_CSV',
        '*Only allow specified hosts through',
        '*socket.socket.connect((host, port)).'
    ])


def test_marker_help_message(testdir):
    result = testdir.runpytest(
        '--markers',
    )
    result.stdout.fnmatch_lines([
        '@pytest.mark.restrict_hosts([[]hosts[]]): Restrict socket connection to defined list of hosts',
    ])


def test_default_connect_enabled(assert_connect):
    assert_connect(True)


def test_single_cli_arg_connect_enabled(assert_connect):
    assert_connect(True, cli_arg=localhost)


def test_multiple_cli_arg_connect_enabled(assert_connect):
    assert_connect(True, cli_arg=localhost + ',1.2.3.4')


def test_single_mark_arg_connect_enabled(assert_connect):
    assert_connect(True, mark_arg=localhost)


def test_multiple_mark_arg_csv_connect_enabled(assert_connect):
    assert_connect(True, mark_arg=localhost + ',1.2.3.4')


def test_multiple_mark_arg_list_connect_enabled(assert_connect):
    assert_connect(True, mark_arg=[localhost, '1.2.3.4'])


def test_mark_cli_conflict_mark_wins_connect_enabled(assert_connect):
    assert_connect(True, mark_arg=[localhost], cli_arg='1.2.3.4')


def test_single_cli_arg_connect_disabled(assert_connect):
    assert_connect(False, cli_arg='1.2.3.4')


def test_multiple_cli_arg_connect_disabled(assert_connect):
    assert_connect(False, cli_arg='5.6.7.8,1.2.3.4')


def test_single_mark_arg_connect_disabled(assert_connect):
    assert_connect(False, mark_arg='1.2.3.4')


def test_multiple_mark_arg_csv_connect_disabled(assert_connect):
    assert_connect(False, mark_arg='5.6.7.8,1.2.3.4')


def test_multiple_mark_arg_list_connect_disabled(assert_connect):
    assert_connect(False, mark_arg=['5.6.7.8', '1.2.3.4'])


def test_mark_cli_conflict_mark_wins_connect_disabled(assert_connect):
    assert_connect(False, mark_arg=['1.2.3.4'], cli_arg=localhost)


def test_default_urllib_succeeds_by_default(assert_connect):
    assert_connect(True, code_template=urlopen_code_template)


def test_single_cli_arg_urlopen_enabled(assert_connect):
    assert_connect(True, cli_arg=localhost + ',1.2.3.4', code_template=urlopen_code_template)


def test_single_mark_arg_urlopen_enabled(assert_connect):
    assert_connect(True, mark_arg=[localhost, '1.2.3.4'], code_template=urlopen_code_template)


def test_global_restrict_via_config_fail(testdir):
    testdir.makepyfile("""
        import socket

        def test_global_restrict_via_config_fail():
            socket.socket().connect(('127.0.0.1', 80))
    """)
    testdir.makeini("""
        [pytest]
        addopts = --restrict-hosts=2.2.2.2
    """)
    result = testdir.runpytest("--verbose")
    result.assert_outcomes(0, 0, 1)
    assert_host_blocked(result, '127.0.0.1')


def test_global_restrict_via_config_pass(testdir, httpserver):
    httpserver.serve_content('ok')
    test_url = urlparse(httpserver.url)
    testdir.makepyfile("""
        import socket

        def test_global_restrict_via_config_pass():
            socket.socket().connect(('{0}', {1}))
    """.format(test_url.hostname, test_url.port))
    testdir.makeini("""
        [pytest]
        addopts = --restrict-hosts={0}
    """.format(test_url.hostname))
    result = testdir.runpytest("--verbose")
    result.assert_outcomes(1, 0, 0)


def test_test_isolation(testdir, httpserver):
    httpserver.serve_content('ok')
    test_url = urlparse(httpserver.url)
    testdir.makepyfile("""
        import pytest
        import socket

        @pytest.mark.restrict_hosts('{0}')
        def test_pass():
            socket.socket().connect(('{0}', {1}))

        @pytest.mark.restrict_hosts('2.2.2.2')
        def test_fail():
            socket.socket().connect(('{0}', {1}))

        def test_pass_2():
            socket.socket().connect(('{0}', {1}))
    """.format(test_url.hostname, test_url.port))
    result = testdir.runpytest("--verbose")
    result.assert_outcomes(2, 0, 1)
    assert_host_blocked(result, test_url.hostname)


def test_conflicting_cli_vs_marks(testdir, httpserver):
    httpserver.serve_content('ok')
    test_url = urlparse(httpserver.url)
    testdir.makepyfile("""
        import pytest
        import socket

        @pytest.mark.restrict_hosts('{0}')
        def test_pass():
            socket.socket().connect(('{0}', {1}))

        @pytest.mark.restrict_hosts('2.2.2.2')
        def test_fail():
            socket.socket().connect(('{0}', {1}))

        def test_fail_2():
            socket.socket().connect(('2.2.2.2', {1}))
    """.format(test_url.hostname, test_url.port))
    result = testdir.runpytest("--verbose", '--restrict-hosts=1.2.3.4')
    result.assert_outcomes(1, 0, 2)
    assert_host_blocked(result, '2.2.2.2')
    assert_host_blocked(result, test_url.hostname)
