# -*- coding: utf-8 -*-
import pytest


def assert_socket_blocked(result):
    result.stdout.fnmatch_lines("""
        *RuntimeError: A test tried to use socket.socket.*
    """)


def test_global_disable(testdir):
    testdir.makepyfile("""
        import pytest
        import pytest_socket
        import socket

        @pytest.fixture(autouse=True)
        def disable_socket_for_all():
            pytest_socket.disable_socket()

        def test_socket():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    """)
    result = testdir.runpytest("--verbose")
    result.assert_outcomes(0, 0, 1)
    assert_socket_blocked(result)


def test_enable_socket_marker(testdir):
    testdir.makepyfile("""
        import pytest
        import pytest_socket
        import socket
        
        @pytest.fixture(autouse=True)
        def disable_socket_for_all():
            pytest_socket.disable_socket()
        
        @pytest.mark.enable_socket
        def test_socket():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    """)
    result = testdir.runpytest("--verbose")
    result.assert_outcomes(0, 0, 1)
    assert_socket_blocked(result)


def test_urllib_succeeds_by_default(testdir):
    testdir.makepyfile("""
        try:
            from urllib.request import urlopen
        except ImportError:
            from urllib2 import urlopen
        
        def test_disable_socket_urllib():
            assert urlopen('https://httpbin.org/get').getcode() == 200
    """)
    result = testdir.runpytest("--verbose")
    result.assert_outcomes(0, 0, 1)
    assert_socket_blocked(result)


def test_enabled_urllib_succeeds(testdir):
    testdir.makepyfile("""
        import pytest
        import pytest_socket
        try:
            from urllib.request import urlopen
        except ImportError:
            from urllib2 import urlopen

        @pytest.fixture(autouse=True)
        def disable_socket_for_all():
            pytest_socket.disable_socket()

        @pytest.mark.enable_socket
        def test_disable_socket_urllib():
            assert urlopen('https://httpbin.org/get').getcode() == 200
    """)
    result = testdir.runpytest("--verbose")
    result.assert_outcomes(0, 0, 1)
    assert_socket_blocked(result)


def test_disabled_urllib_fails(testdir):
    testdir.makepyfile("""
        import pytest
        try:
            from urllib.request import urlopen
        except ImportError:
            from urllib2 import urlopen

        @pytest.mark.disable_socket
        def test_disable_socket_urllib():
            assert urlopen('https://httpbin.org/get').getcode() == 200
    """)
    result = testdir.runpytest("--verbose")
    result.assert_outcomes(0, 0, 1)
    assert_socket_blocked(result)


def test_double_enable_does_nothing(testdir):
    testdir.makepyfile("""
        import pytest_socket
        def test_enabled():
            pytest_socket.enable_socket()
            pytest_socket.enable_socket()
    """)
    result = testdir.runpytest("--verbose")
    result.assert_outcomes(1, 0, 0)
    with pytest.raises(Exception):
        assert_socket_blocked(result)


def test_socket_enabled_fixture(testdir, socket_enabled):
    testdir.makepyfile("""
        import socket
        def test_socket_enabled(socket_enabled):
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    """)
    result = testdir.runpytest("--verbose")
    result.assert_outcomes(1, 0, 0)
    with pytest.raises(Exception):
        assert_socket_blocked(result)


def test_mix_and_match(testdir, socket_enabled):
    testdir.makepyfile("""
        import pytest
        import pytest_socket
        import socket
        
        @pytest.fixture(autouse=True)
        def disable_socket_for_all():
            pytest_socket.disable_socket()

        def test_socket1():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        def test_socket_enabled(socket_enabled):
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        def test_socket2():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    """)
    result = testdir.runpytest("--verbose")
    result.assert_outcomes(1, 0, 2)
