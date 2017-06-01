# -*- coding: utf-8 -*-


def test_disabled_socket_fails(testdir):
    testdir.makepyfile("""
        import socket
        def test_socket():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    """)
    result = testdir.runpytest("--verbose")
    result.assert_outcomes(0, 0, 1)
    result.stdout.fnmatch_lines("""
        *RuntimeError: A test tried to use socket.socket without explicitly un-blocking it.*
    """)


def test_disabled_httplib_fails(testdir):
    testdir.makepyfile("""
        import httplib
        def test_httplib():
            httplib.HTTPConnection("scanme.nmap.org:80").request("GET", "/")
    """)
    result = testdir.runpytest("--verbose")
    result.assert_outcomes(0, 0, 1)
    result.stdout.fnmatch_lines("""
        *RuntimeError: A test tried to use socket.socket without explicitly un-blocking it.*
    """)


def test_enabling_while_enabled_does_nothing(testdir):
    testdir.makepyfile("""
        import pytest_socket
        def test_enabled():
            pytest_socket.enable_socket()
            pytest_socket.enable_socket()
    """)
    result = testdir.runpytest("--verbose")
    result.assert_outcomes(1, 0, 0)


def test_socket_enabled_fixture(testdir, socket_enabled):
    testdir.makepyfile("""
        import socket
        def test_socket_enabled(socket_enabled):
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    """)
    result = testdir.runpytest("--verbose")
    result.assert_outcomes(1, 0, 0)


def test_mix_and_match(testdir, socket_enabled):
    testdir.makepyfile("""
        import socket
        def test_socket1():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        def test_socket_enabled(socket_enabled):
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        def test_socket2():
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    """)
    result = testdir.runpytest("--verbose")
    result.assert_outcomes(1, 0, 2)
