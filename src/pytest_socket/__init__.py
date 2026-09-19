from __future__ import annotations

import ipaddress
import itertools
import socket
import warnings
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import pytest

_true_socket = socket.socket
_true_connect = socket.socket.connect
_true_getaddrinfo = socket.getaddrinfo
_true_gethostbyname = socket.gethostbyname

_IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network


class SocketBlockedError(RuntimeError):
    def __init__(
        self,
        msg: str = "A test tried to use socket.socket.",
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        warnings.warn(msg, stacklevel=2)
        super().__init__(msg)


class SocketConnectBlockedError(RuntimeError):
    def __init__(
        self,
        allowed: list[str],
        host: str | None,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        self._allowed = allowed
        self._host = host
        allowed_str = ",".join(allowed)
        msg = (
            "A test tried to use socket.socket.connect() "
            f'with host "{host}" (allowed: "{allowed_str}").'
        )
        warnings.warn(msg, stacklevel=2)
        super().__init__(msg)

    def __reduce__(self) -> tuple[Any, tuple[Any, ...]]:
        # Reconstruct from the original constructor args so the exception
        # survives pickling by multiprocessing test runners (e.g. pytest-xdist,
        # Django's `--parallel`). The default `BaseException.__reduce__` would
        # replay `self.args` (the formatted message) and miss `host`.
        return (self.__class__, (self._allowed, self._host))


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("socket")
    group.addoption(
        "--disable-socket",
        action="store_true",
        help="Disable socket.socket by default to block network calls.",
    )
    group.addoption(
        "--force-enable-socket",
        action="store_true",
        help="Force enable socket.socket network calls (override --disable-socket).",
    )
    group.addoption(
        "--allow-hosts",
        metavar="ALLOWED_HOSTS_CSV",
        help="Only allow specified hosts through socket.socket.connect((host, port)).",
    )
    group.addoption(
        "--allow-unix-socket",
        action="store_true",
        help="Allow calls if they are to Unix domain sockets",
    )


@pytest.fixture
def socket_disabled(pytestconfig: pytest.Config) -> Iterator[None]:
    """disable socket.socket for duration of this test function"""
    socket_config = pytestconfig.stash[_STASH_KEY]
    disable_socket(allow_unix_socket=socket_config.allow_unix_socket)
    yield


@pytest.fixture
def socket_enabled(pytestconfig: pytest.Config) -> Iterator[None]:
    """enable socket.socket for duration of this test function"""
    enable_socket()
    yield


@dataclass
class _PytestSocketConfig:
    socket_disabled: bool
    socket_force_enabled: bool
    allow_unix_socket: bool
    allow_hosts: str | list[str] | None
    resolution_cache: dict[str, set[str]] = field(default_factory=dict)


_STASH_KEY = pytest.StashKey[_PytestSocketConfig]()


def _is_unix_socket(family: int) -> bool:
    return hasattr(socket, "AF_UNIX") and family == socket.AF_UNIX


def _guarded_getaddrinfo(*_args: Any, **_kwargs: Any) -> Any:
    raise SocketBlockedError("A test tried to use socket.getaddrinfo.")


def _guarded_gethostbyname(*_args: Any, **_kwargs: Any) -> Any:
    raise SocketBlockedError("A test tried to use socket.gethostbyname.")


def disable_socket(allow_unix_socket: bool = False) -> None:
    """disable socket.socket to disable the Internet. useful in testing."""

    class GuardedSocket(socket.socket):
        """socket guard to disable socket creation (from pytest-socket)"""

        def __new__(
            cls,
            family: socket.AddressFamily | int = -1,
            type: socket.SocketKind | int = -1,
            proto: int = -1,
            fileno: int | None = None,
        ) -> GuardedSocket:
            if _is_unix_socket(family) and allow_unix_socket:
                return super().__new__(cls, family, type, proto, fileno)  # type: ignore[call-arg] # noqa E501

            raise SocketBlockedError()

    socket.socket = GuardedSocket  # type: ignore[misc]
    socket.getaddrinfo = _guarded_getaddrinfo
    socket.gethostbyname = _guarded_gethostbyname


def enable_socket() -> None:
    """re-enable socket.socket to enable the Internet. useful in testing."""
    _remove_restrictions()


def _config_from_namespace(namespace: Any) -> _PytestSocketConfig:
    """Build the plugin config from parsed CLI/ini options.

    Works with both `config.option` and the `known_args_namespace` that is
    available before `pytest_configure` (in `pytest_load_initial_conftests`).
    """
    return _PytestSocketConfig(
        socket_force_enabled=namespace.force_enable_socket,
        socket_disabled=namespace.disable_socket,
        allow_unix_socket=namespace.allow_unix_socket,
        allow_hosts=namespace.allow_hosts or None,
    )


def _apply_restrictions(
    socket_config: _PytestSocketConfig,
    *,
    hosts: str | list[str] | None,
    disable: bool,
) -> None:
    """Put the `socket` module into exactly one state.

    Always starts from the real socket, so the outcome never depends on what
    a previous test or phase left behind.
    """
    _remove_restrictions()
    if socket_config.socket_force_enabled:
        return
    socket_allow_hosts(
        hosts,
        allow_unix_socket=socket_config.allow_unix_socket,
        resolution_cache=socket_config.resolution_cache,
    )
    if disable and not hosts:
        disable_socket(socket_config.allow_unix_socket)


def _apply_baseline(socket_config: _PytestSocketConfig) -> None:
    """The state outside of any test: the restrictions given on the CLI.

    It holds from the initial conftest import until `pytest_unconfigure`,
    so collection, session-scoped fixtures and `pytest_sessionfinish` are
    guarded like a test without markers. Tests override it in their setup
    and hand it back in their teardown.
    """
    _apply_restrictions(
        socket_config,
        hosts=socket_config.allow_hosts,
        disable=socket_config.socket_disabled,
    )


@pytest.hookimpl(tryfirst=True)
def pytest_load_initial_conftests(early_config: pytest.Config) -> None:
    """Install the baseline before the initial conftests are imported."""
    socket_config = _config_from_namespace(early_config.known_args_namespace)
    early_config.stash[_STASH_KEY] = socket_config
    # A cleanup, not `pytest_unconfigure`: pytest skips that hook when
    # `pytest_configure` never ran (usage error, conftest import failure),
    # and the guards must not outlive the run in an in-process caller.
    early_config.add_cleanup(_remove_restrictions)
    _apply_baseline(socket_config)


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "disable_socket(): Disable socket connections for a specific test"
    )
    config.addinivalue_line(
        "markers", "enable_socket(): Enable socket connections for a specific test"
    )
    config.addinivalue_line(
        "markers",
        "allow_hosts([hosts]): Restrict socket connection to defined list of hosts",
    )

    # Store the global configs in the `pytest.Config` object. Rebuild them
    # from the final options: another plugin may have added arguments after
    # the early hook above read them, or the plugin may have been loaded too
    # late for that hook to fire at all.
    socket_config = _config_from_namespace(config.option)
    if _STASH_KEY in config.stash:
        socket_config.resolution_cache = config.stash[_STASH_KEY].resolution_cache
    else:
        config.add_cleanup(_remove_restrictions)
    config.stash[_STASH_KEY] = socket_config
    _apply_baseline(socket_config)


def pytest_runtest_setup(item: pytest.Item) -> None:
    """During each test item's setup phase,
    choose the behavior based on the configurations supplied.

    If the given item is not a function test (i.e a DoctestItem)
    or otherwise has no support for fixtures, skip it.
    """
    if not hasattr(item, "fixturenames"):
        return

    socket_config = item.config.stash[_STASH_KEY]

    # If test has the `enable_socket` marker, fixture or
    # it's forced from the CLI, we accept this as most explicit.
    if (
        "socket_enabled" in item.fixturenames
        or item.get_closest_marker("enable_socket")
        or socket_config.socket_force_enabled
    ):
        enable_socket()
        return

    # If the test has the `disable_socket` marker, it's explicitly disabled.
    if "socket_disabled" in item.fixturenames or item.get_closest_marker(
        "disable_socket"
    ):
        _apply_restrictions(socket_config, hosts=None, disable=True)
        return

    # A marker allow-list replaces the CLI one.
    mark_restrictions = item.get_closest_marker("allow_hosts")
    if mark_restrictions:
        _apply_restrictions(
            socket_config,
            hosts=mark_restrictions.args[0],
            disable=socket_config.socket_disabled,
        )

    # Otherwise the baseline, restored by the previous teardown, already
    # holds, on top of whatever earlier `pytest_runtest_setup` impls did.


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_teardown(item: pytest.Item) -> Iterator[None]:
    """Wrap pytest's own teardown hook (which runs fixture finalizers), so those
    run under the same restrictions as the test. Restore the baseline after,
    even when a finalizer raised: a plain `trylast` impl would be skipped then.
    """
    yield
    _apply_baseline(item.config.stash[_STASH_KEY])


def host_from_address(address: tuple[Any, ...]) -> str | None:
    host = address[0]
    if isinstance(host, str):
        return host
    return None


def host_from_connect_args(args: tuple[Any, ...]) -> str | None:
    address = args[0]

    if isinstance(address, tuple):
        return host_from_address(address)
    return None


def is_ipaddress(address: str) -> bool:
    """
    Determine if the address is a valid IPv4 or IPv6 address.
    """
    try:
        ipaddress.ip_address(address)
        return True
    except ValueError:
        return False


def resolve_hostnames(hostname: str) -> set[str]:
    try:
        return {
            addr_struct[0]  # type: ignore[misc]
            for *_, addr_struct in socket.getaddrinfo(hostname, None)
        }
    except socket.gaierror:
        return set()


def normalize_allowed_hosts(
    allowed_hosts: list[str],
    resolution_cache: dict[str, set[str]] | None = None,
) -> dict[str, set[str]]:
    """Map all items in `allowed_hosts` to IP addresses."""
    if resolution_cache is None:
        resolution_cache = {}
    ip_hosts = defaultdict(set)
    for host in allowed_hosts:
        host = host.strip()
        if is_ipaddress(host):
            ip_hosts[host].add(host)
            continue
        if host not in resolution_cache:
            resolution_cache[host] = resolve_hostnames(host)
        ip_hosts[host].update(resolution_cache[host])

    return ip_hosts


def _partition_allowed(
    allowed: list[str],
) -> tuple[list[str], list[_IPNetwork]]:
    """Split an allow-list into plain hosts and CIDR networks.

    Entries containing ``/`` are parsed as networks. Invalid CIDR entries
    fall through to the plain-host path so an existing test failure mode
    (block + meaningful error) is preserved.
    """
    plain_hosts: list[str] = []
    networks: list[_IPNetwork] = []
    for entry in allowed:
        candidate = entry.strip()
        if "/" in candidate:
            try:
                networks.append(ipaddress.ip_network(candidate, strict=False))
                continue
            except ValueError:
                pass
        plain_hosts.append(candidate)
    return plain_hosts, networks


def socket_allow_hosts(
    allowed: str | list[str] | None = None,
    allow_unix_socket: bool = False,
    resolution_cache: dict[str, set[str]] | None = None,
) -> None:
    """disable socket.socket.connect() to disable the Internet. useful in testing."""
    if isinstance(allowed, str):
        allowed = allowed.split(",")

    if not isinstance(allowed, list):
        return

    plain_hosts, networks = _partition_allowed(allowed)

    allowed_ip_hosts_by_host = normalize_allowed_hosts(plain_hosts, resolution_cache)
    allowed_ip_hosts_and_hostnames = set(
        itertools.chain(*allowed_ip_hosts_by_host.values())
    ) | set(allowed_ip_hosts_by_host.keys())
    allowed_list = sorted(
        [
            (
                host
                if len(normalized) == 1 and next(iter(normalized)) == host
                else f"{host} ({','.join(sorted(normalized))})"
            )
            for host, normalized in allowed_ip_hosts_by_host.items()
        ]
        + [str(net) for net in networks]
    )

    def guarded_connect(inst: socket.socket, *args: Any) -> None:
        host = host_from_connect_args(args)
        if host in allowed_ip_hosts_and_hostnames or (
            _is_unix_socket(inst.family) and allow_unix_socket
        ):
            return _true_connect(inst, *args)

        if host and networks and is_ipaddress(host):
            ip = ipaddress.ip_address(host)
            if any(ip in net for net in networks):
                return _true_connect(inst, *args)

        # Close the real socket before raising. The blocking error is a
        # RuntimeError, which bypasses callers' `except OSError` cleanup
        # (e.g. socket.create_connection), so the fd would otherwise leak.
        inst.close()
        raise SocketConnectBlockedError(allowed_list, host)

    socket.socket.connect = guarded_connect  # type: ignore[assignment,method-assign]


def _remove_restrictions() -> None:
    """restore socket.socket.* to allow access to the Internet. useful in testing."""
    socket.socket = _true_socket  # type: ignore[misc]
    socket.socket.connect = _true_connect  # type: ignore[method-assign]
    if socket.getaddrinfo is _guarded_getaddrinfo:
        socket.getaddrinfo = _true_getaddrinfo
    if socket.gethostbyname is _guarded_gethostbyname:
        socket.gethostbyname = _true_gethostbyname
