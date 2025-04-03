"""Verify that pytest-socket works in Python subprocess.

These tests are based off test_socket.py and test_restrict_hosts.py
"""

import inspect
import json
import os
import textwrap
from importlib.metadata import Distribution
from typing import List, Optional, Union

import pytest

from conftest import unix_sockets_only
from tests.common import assert_host_blocked, assert_socket_blocked


def is_pytest_socket_editably_installed() -> bool:
    pytest_socket_package = Distribution.from_name("pytest_socket")
    direct_url = json.loads(pytest_socket_package.read_text("direct_url.json"))
    editable = direct_url.get("dir_info", {}).get("editable", False)
    if editable and "CI" in os.environ:
        raise RuntimeError("CI should be testing against a normal install")

    return editable


pytestmark = pytest.mark.skipif(
    is_pytest_socket_editably_installed(),
    reason=".pth files don't work under an editable install",
)


localhost = "127.0.0.1"

# These templates are only used by the AllowHosts tests.
connect_code_template = """
    {3}
    def {2}():
        run("import socket; socket.socket().connect(('{0}', {1}))")
"""
urlopen_code_template = """
    {3}
    def {2}():
        run(multiline_code('''
            from urllib.request import urlopen
            assert urlopen('http://{0}:{1}/').getcode() == 200
        '''))
"""
urlopen_hostname_code_template = """
    {3}
    def {2}():
        # Skip {{1}} as we expect {{0}} to be the full hostname with or without port
        run(multiline_code('''
            from urllib.request import urlopen
            assert urlopen('http://{0}').getcode() == 200
        '''))
"""


def make_test_file(testdir, code):
    template = textwrap.dedent(
        """
        import textwrap
        import subprocess
        import sys
        import pytest

        def run(code):
            subprocess.run([sys.executable, '-c', code], check=True)

        def multiline_code(code):
            return textwrap.dedent(code)

        SOCKET_CODE = 'import socket; socket.socket(socket.AF_INET, socket.SOCK_STREAM)'
        UNIX_SOCKET_CODE = multiline_code('''
            import socket
            socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        ''')
        URLLIB_CODE = multiline_code('''
            try:
                from urllib.request import urlopen
            except ImportError:
                from urllib2 import urlopen
            urlopen('https://httpstat.us/200').getcode() == 200
        ''')

        {0}
        """
    )
    code = textwrap.dedent(code)
    testdir.makepyfile(template.format(code))


@pytest.fixture
def assert_connect(httpbin, testdir):
    def assert_socket_connect(
        should_pass: bool,
        *,
        host: str = httpbin.host,
        cli_arg: Optional[str] = None,
        mark_arg: Optional[Union[str, List[str]]] = None,
        code_template: str = connect_code_template,
    ):
        # get the name of the calling function
        test_name = inspect.stack()[1][3]
        mark = ""

        if mark_arg:
            if isinstance(mark_arg, str):
                mark = f'@pytest.mark.allow_hosts("{mark_arg}")'
            elif isinstance(mark_arg, list):
                hosts = '","'.join(mark_arg)
                mark = f'@pytest.mark.allow_hosts(["{hosts}"])'
        code = code_template.format(host, httpbin.port, test_name, mark)
        make_test_file(testdir, code)

        if cli_arg:
            result = testdir.runpytest(f"--allow-hosts={cli_arg}")
        else:
            result = testdir.runpytest()

        if should_pass:
            result.assert_outcomes(passed=1, skipped=0, failed=0)
        else:
            result.assert_outcomes(passed=0, skipped=0, failed=1)
            assert_host_blocked(result, host)

        return result

    return assert_socket_connect


def test_disable_socket_fixture(testdir):
    make_test_file(
        testdir,
        """
        def test_socket(socket_disabled):
            run(SOCKET_CODE)
        """,
    )
    result = testdir.runpytest()
    assert_socket_blocked(result)


def test_disable_socket_marker(testdir):
    make_test_file(
        testdir,
        """
        @pytest.mark.disable_socket
        def test_socket():
            run(SOCKET_CODE)
        """,
    )
    result = testdir.runpytest()
    assert_socket_blocked(result)


def test_enable_socket_fixture(testdir):
    make_test_file(
        testdir,
        """
        def test_socket(socket_enabled):
            run(SOCKET_CODE)
        """,
    )
    result = testdir.runpytest("--disable-socket")
    result.assert_outcomes(passed=1, skipped=0, failed=0)
    with pytest.raises(BaseException):
        assert_socket_blocked(result)


def test_enable_socket_marker(testdir):
    make_test_file(
        testdir,
        """
        @pytest.mark.enable_socket
        def test_socket():
            run(SOCKET_CODE)
        """,
    )
    result = testdir.runpytest("--disable-socket")
    result.assert_outcomes(passed=1, skipped=0, failed=0)
    with pytest.raises(BaseException):
        assert_socket_blocked(result)


@pytest.mark.parametrize("mode", ["default", "enabled"])
def test_urllib_succeeds(testdir, mode: str):
    fixture = "socket_enabled" if mode == "enabled" else ""
    make_test_file(
        testdir,
        f"""
        def test_socket_urllib({fixture}):
            run(URLLIB_CODE)
        """,
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=1, skipped=0, failed=0)
    with pytest.raises(BaseException):
        assert_socket_blocked(result)


def test_disabled_urllib_fails(testdir):
    make_test_file(
        testdir,
        """
        @pytest.mark.disable_socket
        def test_disable_socket_urllib():
            run(URLLIB_CODE)
        """,
    )
    result = testdir.runpytest()
    assert_socket_blocked(result)


def test_mix_and_match(testdir, socket_enabled):
    make_test_file(
        testdir,
        """
        def test_socket1():
            run(SOCKET_CODE)
        def test_socket_enabled(socket_enabled):
            run(SOCKET_CODE)
        def test_socket2():
            run(SOCKET_CODE)
        """,
    )
    result = testdir.runpytest("--disable-socket")
    result.assert_outcomes(passed=1, skipped=0, failed=2)


def test_socket_subclass_is_still_blocked(testdir):
    make_test_file(
        testdir,
        """
        code = multiline_code('''
            import socket
            class MySocket(socket.socket):
                pass
            MySocket(socket.AF_INET, socket.SOCK_STREAM)
        ''')

        @pytest.mark.disable_socket
        def test_subclass_is_still_blocked():
            run(code)
        """,
    )
    result = testdir.runpytest()
    assert_socket_blocked(result)


@unix_sockets_only
@pytest.mark.parametrize("state", ["blocked", "allowed"])
def test_unix_domain_sockets_with_disable_socket(testdir, state: str):
    make_test_file(
        testdir,
        """
        def test_inet():
            run(SOCKET_CODE)
        def test_unix_socket():
            run(UNIX_SOCKET_CODE)
        """,
    )
    if state == "allowed":
        result = testdir.runpytest("--disable-socket", "--allow-unix-socket")
        result.assert_outcomes(passed=1, skipped=0, failed=1)
    else:
        result = testdir.runpytest("--disable-socket")
        result.assert_outcomes(passed=0, skipped=0, failed=2)


class TestAllowHosts:
    def test_single_cli_arg_connect_enabled(self, assert_connect):
        assert_connect(True, cli_arg=localhost)

    def test_single_cli_arg_connect_enabled_localhost_resolved(self, assert_connect):
        assert_connect(True, cli_arg="localhost")

    def test_single_cli_arg_127_0_0_1_hostname_localhost_connect_disabled(
        self, assert_connect
    ):
        assert_connect(False, cli_arg=localhost, host="localhost")

    def test_single_cli_arg_localhost_hostname_localhost_connect_enabled(
        self, assert_connect
    ):
        assert_connect(True, cli_arg="localhost", host="localhost")

    def test_single_cli_arg_connect_disabled_hostname_resolved(self, assert_connect):
        result = assert_connect(
            False,
            cli_arg="localhost",
            host="1.2.3.4",
            code_template=urlopen_hostname_code_template,
        )
        result.stdout.fnmatch_lines(
            '*A test tried to use socket.socket.connect() with host "1.2.3.4" '
            '(allowed: "localhost (127.0.0.1*'
        )

    def test_single_cli_arg_connect_enabled_hostname_unresolvable(self, assert_connect):
        assert_connect(False, cli_arg="unresolvable")

    def test_multiple_cli_arg_connect_enabled(self, assert_connect):
        assert_connect(True, cli_arg=localhost + ",1.2.3.4")

    def test_single_mark_arg_connect_enabled(self, assert_connect):
        assert_connect(True, mark_arg=localhost)

    def test_multiple_mark_arg_csv_connect_enabled(self, assert_connect):
        assert_connect(True, mark_arg=localhost + ",1.2.3.4")

    def test_multiple_mark_arg_list_connect_enabled(self, assert_connect):
        assert_connect(True, mark_arg=[localhost, "1.2.3.4"])

    def test_mark_cli_conflict_mark_wins_connect_enabled(self, assert_connect):
        assert_connect(True, mark_arg=[localhost], cli_arg="1.2.3.4")

    def test_single_cli_arg_connect_disabled(self, assert_connect):
        assert_connect(False, cli_arg="1.2.3.4")

    def test_multiple_cli_arg_connect_disabled(self, assert_connect):
        assert_connect(False, cli_arg="5.6.7.8,1.2.3.4")

    def test_single_mark_arg_connect_disabled(self, assert_connect):
        assert_connect(False, mark_arg="1.2.3.4")

    def test_multiple_mark_arg_csv_connect_disabled(self, assert_connect):
        assert_connect(False, mark_arg="5.6.7.8,1.2.3.4")

    def test_multiple_mark_arg_list_connect_disabled(self, assert_connect):
        assert_connect(False, mark_arg=["5.6.7.8", "1.2.3.4"])

    def test_mark_cli_conflict_mark_wins_connect_disabled(self, assert_connect):
        assert_connect(False, mark_arg=["1.2.3.4"], cli_arg=localhost)

    def test_default_urlopen_succeeds_by_default(self, assert_connect):
        assert_connect(True, code_template=urlopen_code_template)

    def test_single_cli_arg_urlopen_enabled(self, assert_connect):
        assert_connect(
            True, cli_arg=localhost + ",1.2.3.4", code_template=urlopen_code_template
        )

    def test_single_mark_arg_urlopen_enabled(self, assert_connect):
        assert_connect(
            True, mark_arg=[localhost, "1.2.3.4"], code_template=urlopen_code_template
        )
