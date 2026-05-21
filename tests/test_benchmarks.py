"""
Performance benchmarks for pytest-socket.

These benchmarks track the performance of the core utility functions
used by the plugin to resolve, validate, and partition host allow-lists.
"""

from __future__ import annotations

import pytest

from pytest_socket import (
    _partition_allowed,
    disable_socket,
    enable_socket,
    host_from_address,
    host_from_connect_args,
    is_ipaddress,
    normalize_allowed_hosts,
)

# ---------------------------------------------------------------------------
# is_ipaddress
# ---------------------------------------------------------------------------


def test_bench_is_ipaddress_valid_ipv4(benchmark):
    benchmark(is_ipaddress, "192.168.1.1")


def test_bench_is_ipaddress_valid_ipv6(benchmark):
    benchmark(is_ipaddress, "::1")


def test_bench_is_ipaddress_invalid(benchmark):
    benchmark(is_ipaddress, "not-an-ip")


# ---------------------------------------------------------------------------
# host_from_address / host_from_connect_args
# ---------------------------------------------------------------------------


def test_bench_host_from_address(benchmark):
    benchmark(host_from_address, ("127.0.0.1", 80))


def test_bench_host_from_connect_args(benchmark):
    benchmark(host_from_connect_args, (("10.0.0.1", 443),))


def test_bench_host_from_connect_args_unix(benchmark):
    """Benchmark with a non-tuple address (e.g. Unix socket path)."""
    benchmark(host_from_connect_args, ("/var/run/app.sock",))


# ---------------------------------------------------------------------------
# _partition_allowed
# ---------------------------------------------------------------------------


def test_bench_partition_allowed_hosts_only(benchmark):
    hosts = ["127.0.0.1", "10.0.0.1", "::1", "localhost"]
    benchmark(_partition_allowed, hosts)


def test_bench_partition_allowed_mixed(benchmark):
    hosts = [
        "127.0.0.1",
        "10.0.0.0/8",
        "::1",
        "192.168.0.0/16",
        "localhost",
        "172.16.0.0/12",
    ]
    benchmark(_partition_allowed, hosts)


def test_bench_partition_allowed_large(benchmark):
    hosts = [f"10.0.{i}.0/24" for i in range(50)] + [
        f"192.168.1.{i}" for i in range(50)
    ]
    benchmark(_partition_allowed, hosts)


# ---------------------------------------------------------------------------
# normalize_allowed_hosts
# ---------------------------------------------------------------------------


def test_bench_normalize_allowed_hosts_ips(benchmark):
    hosts = ["127.0.0.1", "10.0.0.1", "192.168.1.1"]
    benchmark(normalize_allowed_hosts, hosts)


def test_bench_normalize_allowed_hosts_with_cache(benchmark):
    cache: dict[str, set[str]] = {}
    hosts = ["127.0.0.1", "10.0.0.1"]
    benchmark(normalize_allowed_hosts, hosts, cache)


# ---------------------------------------------------------------------------
# disable_socket / enable_socket cycle
# ---------------------------------------------------------------------------


def _disable_enable_cycle():
    disable_socket(allow_unix_socket=False)
    enable_socket()


def test_bench_disable_enable_socket(benchmark):
    benchmark(_disable_enable_cycle)
    # Ensure socket is restored after benchmark
    enable_socket()
