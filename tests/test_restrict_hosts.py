import inspect

import pytest

localhost = "127.0.0.1"

connect_code_template = """
    import socket
    import pytest

    {3}
    def {2}():
        socket.socket().connect(('{0}', {1}))
"""

connect_unicode_code_template = """
    import socket
    import pytest

    {3}
    def {2}():
        socket.socket().connect((u'{0}', {1}))
"""

urlopen_code_template = """
    import pytest
    from urllib.request import urlopen

    {3}
    def {2}():
        assert urlopen('http://{0}:{1}/').getcode() == 200
"""

urlopen_hostname_code_template = """
    import pytest
    from urllib.request import urlopen

    {3}
    def {2}():
        # Skip {{1}} as we expect {{0}} to be the full hostname with or without port
        assert urlopen('http://{0}').getcode() == 200
"""


def assert_host_blocked(result, host):
    result.stdout.fnmatch_lines(
        f'*A test tried to use socket.socket.connect() with host "{host}"*'
    )


@pytest.fixture
def assert_connect(httpbin, testdir):
    def assert_socket_connect(should_pass, **kwargs):
        # get the name of the calling function
        test_name = inspect.stack()[1][3]

        mark = ""
        host = kwargs.get("host", httpbin.host)
        cli_arg = kwargs.get("cli_arg", None)
        code_template = kwargs.get("code_template", connect_code_template)
        mark_arg = kwargs.get("mark_arg", None)

        if mark_arg:
            if isinstance(mark_arg, str):
                mark = f'@pytest.mark.allow_hosts("{mark_arg}")'
            elif isinstance(mark_arg, list):
                hosts = '","'.join(mark_arg)
                mark = f'@pytest.mark.allow_hosts(["{hosts}"])'
        code = code_template.format(host, httpbin.port, test_name, mark)
        testdir.makepyfile(code)

        if cli_arg:
            result = testdir.runpytest(f"--allow-hosts={cli_arg}")
        else:
            result = testdir.runpytest()

        if should_pass:
            result.assert_outcomes(1, 0, 0)
        else:
            result.assert_outcomes(0, 0, 1)
            assert_host_blocked(result, host)

        return result

    return assert_socket_connect


def test_help_message(testdir):
    result = testdir.runpytest(
        "--help",
    )
    result.stdout.fnmatch_lines(
        [
            "socket:",
            "*--allow-hosts=ALLOWED_HOSTS_CSV",
            "*Only allow specified hosts through",
            "*socket.socket.connect((host, port)).",
        ]
    )


def test_marker_help_message(testdir):
    result = testdir.runpytest(
        "--markers",
    )
    result.stdout.fnmatch_lines(
        [
            "@pytest.mark.allow_hosts([[]hosts[]]): "
            "Restrict socket connection to defined list of hosts",
        ]
    )


def test_default_connect_enabled(assert_connect):
    assert_connect(True)


def test_single_cli_arg_connect_enabled(assert_connect):
    assert_connect(True, cli_arg=localhost)


def test_single_cli_arg_connect_enabled_localhost_resolved(assert_connect):
    assert_connect(True, cli_arg="localhost")


def test_single_cli_arg_127_0_0_1_hostname_localhost_connect_disabled(assert_connect):
    assert_connect(False, cli_arg=localhost, host="localhost")


def test_single_cli_arg_localhost_hostname_localhost_connect_enabled(assert_connect):
    assert_connect(True, cli_arg="localhost", host="localhost")


def test_single_cli_arg_connect_disabled_hostname_resolved(assert_connect):
    result = assert_connect(
        False,
        cli_arg="localhost",
        host="1.2.3.4",
        code_template=urlopen_hostname_code_template,
    )
    result.stdout.fnmatch_lines(
        '*A test tried to use socket.socket.connect() with host "1.2.3.4" '
        '(allowed: "localhost (127.0.0.1,::1)")*'
    )


def test_single_cli_arg_connect_enabled_hostname_unresolvable(assert_connect):
    assert_connect(False, cli_arg="unresolvable")


def test_single_cli_arg_connect_unicode_enabled(assert_connect):
    assert_connect(True, cli_arg=localhost, code_template=connect_unicode_code_template)


def test_multiple_cli_arg_connect_enabled(assert_connect):
    assert_connect(True, cli_arg=localhost + ",1.2.3.4")


def test_single_mark_arg_connect_enabled(assert_connect):
    assert_connect(True, mark_arg=localhost)


def test_multiple_mark_arg_csv_connect_enabled(assert_connect):
    assert_connect(True, mark_arg=localhost + ",1.2.3.4")


def test_multiple_mark_arg_list_connect_enabled(assert_connect):
    assert_connect(True, mark_arg=[localhost, "1.2.3.4"])


def test_mark_cli_conflict_mark_wins_connect_enabled(assert_connect):
    assert_connect(True, mark_arg=[localhost], cli_arg="1.2.3.4")


def test_single_cli_arg_connect_disabled(assert_connect):
    assert_connect(
        False, cli_arg="1.2.3.4", code_template=connect_unicode_code_template
    )


def test_multiple_cli_arg_connect_disabled(assert_connect):
    assert_connect(False, cli_arg="5.6.7.8,1.2.3.4")


def test_single_mark_arg_connect_disabled(assert_connect):
    assert_connect(False, mark_arg="1.2.3.4")


def test_multiple_mark_arg_csv_connect_disabled(assert_connect):
    assert_connect(False, mark_arg="5.6.7.8,1.2.3.4")


def test_multiple_mark_arg_list_connect_disabled(assert_connect):
    assert_connect(False, mark_arg=["5.6.7.8", "1.2.3.4"])


def test_mark_cli_conflict_mark_wins_connect_disabled(assert_connect):
    assert_connect(False, mark_arg=["1.2.3.4"], cli_arg=localhost)


def test_default_urlopen_succeeds_by_default(assert_connect):
    assert_connect(True, code_template=urlopen_code_template)


def test_single_cli_arg_urlopen_enabled(assert_connect):
    assert_connect(
        True, cli_arg=localhost + ",1.2.3.4", code_template=urlopen_code_template
    )


def test_single_mark_arg_urlopen_enabled(assert_connect):
    assert_connect(
        True, mark_arg=[localhost, "1.2.3.4"], code_template=urlopen_code_template
    )


def test_global_restrict_via_config_fail(testdir):
    testdir.makepyfile(
        """
        import socket

        def test_global_restrict_via_config_fail():
            socket.socket().connect(('127.0.0.1', 80))
        """
    )
    testdir.makeini(
        """
        [pytest]
        addopts = --allow-hosts=2.2.2.2
        """
    )
    result = testdir.runpytest()
    result.assert_outcomes(0, 0, 1)
    assert_host_blocked(result, "127.0.0.1")


def test_global_restrict_via_config_pass(testdir, httpbin):
    testdir.makepyfile(
        f"""
        import socket

        def test_global_restrict_via_config_pass():
            socket.socket().connect(('{httpbin.host}', {httpbin.port}))
        """
    )
    testdir.makeini(
        f"""
        [pytest]
        addopts = --allow-hosts={httpbin.host}
        """
    )
    result = testdir.runpytest()
    result.assert_outcomes(1, 0, 0)


def test_test_isolation(testdir, httpbin):
    testdir.makepyfile(
        f"""
        import pytest
        import socket

        @pytest.mark.allow_hosts('{httpbin.host}')
        def test_pass():
            socket.socket().connect(('{httpbin.host}', {httpbin.port}))

        @pytest.mark.allow_hosts('2.2.2.2')
        def test_fail():
            socket.socket().connect(('{httpbin.host}', {httpbin.port}))

        def test_pass_2():
            socket.socket().connect(('{httpbin.host}', {httpbin.port}))
        """
    )
    result = testdir.runpytest()
    result.assert_outcomes(2, 0, 1)
    assert_host_blocked(result, httpbin.host)


def test_conflicting_cli_vs_marks(testdir, httpbin):
    testdir.makepyfile(
        f"""
        import pytest
        import socket

        @pytest.mark.allow_hosts('{httpbin.host}')
        def test_pass():
            socket.socket().connect(('{httpbin.host}', {httpbin.port}))

        @pytest.mark.allow_hosts('2.2.2.2')
        def test_fail():
            socket.socket().connect(('{httpbin.host}', {httpbin.port}))

        def test_fail_2():
            socket.socket().connect(('2.2.2.2', {httpbin.port}))
        """
    )
    result = testdir.runpytest("--allow-hosts=1.2.3.4")
    result.assert_outcomes(1, 0, 2)
    assert_host_blocked(result, "2.2.2.2")
    assert_host_blocked(result, httpbin.host)
