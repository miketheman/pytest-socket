import collections
import inspect
import socket

import pytest

from pytest_socket import normalize_allowed_hosts

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
def assert_connect(httpserver, pytester):
    def assert_socket_connect(should_pass, **kwargs):
        # get the name of the calling function
        test_name = inspect.stack()[1][3]

        mark = ""
        host = kwargs.get("host", httpserver.host)
        cli_arg = kwargs.get("cli_arg", None)
        code_template = kwargs.get("code_template", connect_code_template)
        mark_arg = kwargs.get("mark_arg", None)

        if mark_arg:
            if isinstance(mark_arg, str):
                mark = f'@pytest.mark.allow_hosts("{mark_arg}")'
            elif isinstance(mark_arg, list):
                hosts = '","'.join(mark_arg)
                mark = f'@pytest.mark.allow_hosts(["{hosts}"])'
        code = code_template.format(host, httpserver.port, test_name, mark)
        pytester.makepyfile(code)

        if cli_arg:
            result = pytester.runpytest(f"--allow-hosts={cli_arg}")
        else:
            result = pytester.runpytest()

        if should_pass:
            result.assert_outcomes(passed=1)
        else:
            result.assert_outcomes(failed=1)
            assert_host_blocked(result, host)

        return result

    return assert_socket_connect


@pytest.fixture
def getaddrinfo_hosts(monkeypatch):
    hosts = []

    def _getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        hosts.append(host)
        v4 = (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("127.0.0.127", 0),
        )
        return [v4]

    monkeypatch.setattr(socket, "getaddrinfo", _getaddrinfo)
    return hosts


def test_help_message(pytester):
    result = pytester.runpytest(
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


def test_marker_help_message(pytester):
    result = pytester.runpytest(
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


def test_global_restrict_via_config_fail(pytester):
    pytester.makepyfile("""
        import socket

        def test_global_restrict_via_config_fail():
            socket.socket().connect(('127.0.0.1', 80))
        """)
    pytester.makeini("""
        [pytest]
        addopts = --allow-hosts=2.2.2.2
        """)
    result = pytester.runpytest()
    result.assert_outcomes(failed=1)
    assert_host_blocked(result, "127.0.0.1")


def test_global_restrict_via_config_pass(pytester, httpserver):
    pytester.makepyfile(f"""
        import socket

        def test_global_restrict_via_config_pass():
            socket.socket().connect(('{httpserver.host}', {httpserver.port}))
        """)
    pytester.makeini(f"""
        [pytest]
        addopts = --allow-hosts={httpserver.host}
        """)
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_test_isolation(pytester, httpserver):
    pytester.makepyfile(f"""
        import pytest
        import socket

        @pytest.mark.allow_hosts('{httpserver.host}')
        def test_pass():
            socket.socket().connect(('{httpserver.host}', {httpserver.port}))

        @pytest.mark.allow_hosts('2.2.2.2')
        def test_fail():
            socket.socket().connect(('{httpserver.host}', {httpserver.port}))

        def test_pass_2():
            socket.socket().connect(('{httpserver.host}', {httpserver.port}))
        """)
    result = pytester.runpytest()
    result.assert_outcomes(passed=2, failed=1)
    assert_host_blocked(result, httpserver.host)


def test_conflicting_cli_vs_marks(pytester, httpserver):
    pytester.makepyfile(f"""
        import pytest
        import socket

        @pytest.mark.allow_hosts('{httpserver.host}')
        def test_pass():
            socket.socket().connect(('{httpserver.host}', {httpserver.port}))

        @pytest.mark.allow_hosts('2.2.2.2')
        def test_fail():
            socket.socket().connect(('{httpserver.host}', {httpserver.port}))

        def test_fail_2():
            socket.socket().connect(('2.2.2.2', {httpserver.port}))
        """)
    result = pytester.runpytest("--allow-hosts=1.2.3.4")
    result.assert_outcomes(passed=1, failed=2)
    assert_host_blocked(result, "2.2.2.2")
    assert_host_blocked(result, httpserver.host)


def test_normalize_allowed_hosts(getaddrinfo_hosts):
    """normalize_allowed_hosts() produces a map of hosts to IP addresses."""
    assert normalize_allowed_hosts(["127.0.0.1", "localhost", "localhost", "::1"]) == {
        "::1": {"::1"},
        "127.0.0.1": {"127.0.0.1"},
        "localhost": {"127.0.0.127"},
    }

    assert getaddrinfo_hosts == ["localhost"]


def test_normalize_allowed_hosts_cache(getaddrinfo_hosts):
    """normalize_allowed_hosts() caches name resolutions when passed a cache"""
    cache = {}

    assert normalize_allowed_hosts(["localhost"], cache) == {
        "localhost": {"127.0.0.127"}
    }
    assert cache == {"localhost": {"127.0.0.127"}}
    assert getaddrinfo_hosts == ["localhost"]

    del getaddrinfo_hosts[:]

    assert normalize_allowed_hosts(["localhost", "localhost"], cache) == {
        "localhost": {"127.0.0.127"}
    }
    assert cache == {"localhost": {"127.0.0.127"}}
    assert getaddrinfo_hosts == []


def test_cidr_marker_permits_in_block_ip(pytester, httpserver):
    """A test marked with a CIDR can connect to any IP inside that block."""
    pytester.makepyfile(f"""
        import pytest
        import socket

        @pytest.mark.allow_hosts('127.0.0.0/8')
        def test_in_block():
            socket.socket().connect(('{httpserver.host}', {httpserver.port}))
        """)
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_cidr_marker_blocks_out_of_block_ip(pytester, httpserver):
    """A CIDR marker still blocks IPs outside the block."""
    pytester.makepyfile(f"""
        import pytest
        import socket

        @pytest.mark.allow_hosts('127.0.0.0/8')
        def test_out_of_block():
            socket.socket().connect(('2.2.2.2', {httpserver.port}))
        """)
    result = pytester.runpytest()
    result.assert_outcomes(failed=1)
    assert_host_blocked(result, "2.2.2.2")


def test_cidr_via_cli_flag(pytester, httpserver):
    """CIDR works the same when passed via --allow-hosts CSV."""
    pytester.makepyfile(f"""
        import socket

        def test_in_block():
            socket.socket().connect(('{httpserver.host}', {httpserver.port}))

        def test_out_of_block():
            socket.socket().connect(('2.2.2.2', {httpserver.port}))
        """)
    result = pytester.runpytest("--allow-hosts=127.0.0.0/8")
    result.assert_outcomes(passed=1, failed=1)
    assert_host_blocked(result, "2.2.2.2")


def test_mixed_cidr_ip_and_hostname_allowlist(pytester, httpserver):
    """CIDR and literal-IP entries coexist in one allowlist.

    Hostname coexistence is exercised by ``test_normalize_allowed_hosts`` and
    ``test_name_resolution_cached``; this test focuses on the new CIDR path
    sharing the allowlist with a literal IP (the live ``httpserver``) and
    confirms that an unrelated host is still blocked.
    """
    pytester.makepyfile(f"""
        import pytest
        import socket

        @pytest.mark.allow_hosts(['10.0.0.0/8', '{httpserver.host}'])
        def test_literal_ip_path():
            socket.socket().connect(('{httpserver.host}', {httpserver.port}))

        @pytest.mark.allow_hosts(['10.0.0.0/8', '{httpserver.host}'])
        def test_cidr_path_blocks_outsider():
            socket.socket().connect(('2.2.2.2', {httpserver.port}))
        """)
    result = pytester.runpytest()
    result.assert_outcomes(passed=1, failed=1)
    assert_host_blocked(result, "2.2.2.2")


def test_ipv6_cidr(pytester):
    """IPv6 CIDR allow-list permits in-block addresses and blocks others."""
    pytester.makepyfile("""
        import pytest
        import socket

        @pytest.mark.allow_hosts('::1/128')
        def test_in_block():
            # ::1 is in the /128 block — guard should permit; real connect
            # may still error at the OS level, but not as SocketConnectBlockedError.
            try:
                socket.socket(socket.AF_INET6).connect(('::1', 1))
            except OSError as exc:
                # Anything except SocketConnectBlockedError is fine here.
                import pytest_socket
                assert not isinstance(exc, pytest_socket.SocketConnectBlockedError)

        @pytest.mark.allow_hosts('::1/128')
        def test_out_of_block():
            socket.socket(socket.AF_INET6).connect(('2001:db8::1', 1))
        """)
    result = pytester.runpytest()
    result.assert_outcomes(passed=1, failed=1)
    assert_host_blocked(result, "2001:db8::1")


def test_hostname_arg_with_cidr_only_allowlist(pytester):
    """A connect call using a hostname (not an IP) under a CIDR-only allowlist
    raises SocketConnectBlockedError — not a ValueError from ipaddress.

    This is the failure mode that prevented merging the original CIDR PR (#185).
    """
    pytester.makepyfile("""
        import socket

        def test_hostname_connect():
            # 'example.invalid' will never resolve to an IP; the guard must
            # block it cleanly rather than crashing when it tries to parse
            # the hostname as an IP for CIDR membership.
            socket.socket().connect(('example.invalid', 80))
        """)
    result = pytester.runpytest("--allow-hosts=10.0.0.0/8")
    result.assert_outcomes(failed=1)
    assert_host_blocked(result, "example.invalid")


def test_cidr_appears_in_blocked_error_message(pytester):
    """The 'allowed:' hint in the blocked-connect message includes CIDR strings."""
    pytester.makepyfile("""
        import socket

        def test_blocked():
            socket.socket().connect(('2.2.2.2', 80))
        """)
    result = pytester.runpytest("--allow-hosts=10.0.0.0/8,192.168.0.0/16")
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines('*allowed: "10.0.0.0/8,192.168.0.0/16"*')


def test_malformed_cidr_does_not_crash(pytester):
    """A malformed CIDR entry is treated as a (non-resolving) host, not a crash."""
    pytester.makepyfile("""
        import socket

        def test_blocked():
            socket.socket().connect(('2.2.2.2', 80))
        """)
    result = pytester.runpytest("--allow-hosts=10.0.0.0/notanumber")
    result.assert_outcomes(failed=1)
    assert_host_blocked(result, "2.2.2.2")


def test_name_resolution_cached(pytester, getaddrinfo_hosts):
    """pytest-socket only resolves each allowed name once."""

    pytester.makepyfile("""
        import pytest
        import socket

        @pytest.mark.allow_hosts('name.internal')
        def test_1():
            ...

        @pytest.mark.allow_hosts(['name.internal', 'name.another'])
        def test_2():
            ...

        @pytest.mark.allow_hosts('name.internal')
        @pytest.mark.parametrize("i", ["3", "4", "5"])
        def test_456(i):
            ...
        """)

    hooks = pytester.inline_run("--allow-hosts=name.internal,name.internal")
    [result] = hooks.getcalls("pytest_sessionfinish")
    assert result.session.testsfailed == 0

    assert collections.Counter(getaddrinfo_hosts) == {
        "name.internal": 1,
        "name.another": 1,
    }
