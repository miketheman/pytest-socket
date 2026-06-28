"""Tests for the DNS-resolution guard added alongside --disable-socket."""


def test_dns_restored_between_tests(pytester):
    # teardown of a blocked test must restore getaddrinfo/gethostbyname so the
    # next test sees the real functions, not a stale guard from the prior test.
    pytester.makepyfile("""
        import pytest
        import socket

        @pytest.mark.disable_socket
        def test_blocked():
            socket.gethostbyname('localhost')

        @pytest.mark.enable_socket
        def test_works_after():
            socket.gethostbyname('localhost')
        """)
    result = pytester.runpytest("-p", "no:randomly")
    result.assert_outcomes(passed=1, failed=1)


def test_dns_unblocked_by_force_enable(pytester):
    pytester.makepyfile("""
        import socket

        def test_dns():
            socket.gethostbyname('localhost')
        """)
    result = pytester.runpytest("--disable-socket", "--force-enable-socket")
    result.assert_outcomes(passed=1)


def test_dns_unblocked_by_marker(pytester):
    pytester.makepyfile("""
        import pytest
        import socket

        @pytest.mark.enable_socket
        def test_dns():
            socket.gethostbyname('localhost')
        """)
    result = pytester.runpytest("--disable-socket")
    result.assert_outcomes(passed=1)


def test_allow_hosts_with_hostname_under_disable_socket(pytester, httpserver):
    # End-to-end: `--disable-socket --allow-hosts=<hostname>` must resolve the
    # hostname at setup and accept a connection to that name from a test.
    pytester.makepyfile(f"""
        import socket

        def test_connect_via_allowed_hostname():
            socket.socket().connect(('localhost', {httpserver.port}))
        """)
    result = pytester.runpytest("--disable-socket", "--allow-hosts=localhost")
    result.assert_outcomes(passed=1)


def test_error_messages_identify_the_blocked_function(pytester):
    # Each guarded entry point names itself in the error so a failing test
    # tells the developer which call was caught.
    pytester.makepyfile("""
        import socket

        def test_addrinfo():
            socket.getaddrinfo('localhost', 80)

        def test_hostbyname():
            socket.gethostbyname('localhost')

        def test_socket():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """)
    result = pytester.runpytest("--disable-socket", "-p", "no:randomly")
    result.assert_outcomes(failed=3)
    result.stdout.fnmatch_lines(
        [
            "*A test tried to use socket.getaddrinfo.*",
            "*A test tried to use socket.gethostbyname.*",
            "*A test tried to use socket.socket.*",
        ]
    )


def test_dns_unblocked_by_fixture(pytester):
    pytester.makepyfile("""
        import socket

        def test_dns(socket_enabled):
            socket.gethostbyname('localhost')
        """)
    result = pytester.runpytest("--disable-socket")
    result.assert_outcomes(passed=1)


def test_getaddrinfo_blocked_under_disable_socket(pytester):
    pytester.makepyfile("""
        import socket

        def test_dns():
            socket.getaddrinfo('localhost', 80)
        """)
    result = pytester.runpytest("--disable-socket")
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(
        "*SocketBlockedError: A test tried to use socket.getaddrinfo.*"
    )


def test_gethostbyname_blocked_under_disable_socket(pytester):
    pytester.makepyfile("""
        import socket

        def test_dns():
            socket.gethostbyname('localhost')
        """)
    result = pytester.runpytest("--disable-socket")
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(
        "*SocketBlockedError: A test tried to use socket.gethostbyname.*"
    )


def test_enable_socket_restores_dns_within_test():
    """enable_socket() restores the real getaddrinfo/gethostbyname that
    disable_socket() swapped out, observable within a single test.
    """
    import socket

    from pytest_socket import disable_socket, enable_socket

    disable_socket()
    enable_socket()
    # Both DNS entry points must be callable again, not the raising guards.
    socket.gethostbyname("localhost")
    socket.getaddrinfo("localhost", None)


def test_dns_restored_by_teardown_without_enable(pytester):
    # A disabled test's teardown must restore gethostbyname even when the next
    # test does not opt into enable_socket — relying solely on the teardown.
    pytester.makepyfile("""
        import pytest
        import socket
        from pytest_socket import SocketBlockedError

        @pytest.mark.disable_socket
        def test_blocked():
            with pytest.raises(SocketBlockedError):
                socket.gethostbyname('localhost')

        def test_after():
            socket.gethostbyname('localhost')
        """)
    result = pytester.runpytest("-p", "no:randomly")
    result.assert_outcomes(passed=2)
