import ipaddress
import itertools
import socket
import typing
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field

import pytest
import typing_extensions

_true_socket = socket.socket
_true_connect = socket.socket.connect


class SocketBlockedError(RuntimeError):
    def __init__(self, *_args: typing.Any, **_kwargs: typing.Any):
        super().__init__("A test tried to use socket.socket.")


class SocketConnectBlockedError(RuntimeError):
    def __init__(
        self,
        allowed: typing.List[str],
        host: typing.Union[str, None],
        *_args: typing.Any,
        **_kwargs: typing.Any,
    ):
        allowed_str = ",".join(allowed)
        super().__init__(
            "A test tried to use socket.socket.connect() "
            f'with host "{host}" (allowed: "{allowed_str}").'
        )


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("socket")
    group.addoption(
        "--disable-socket",
        action="store_true",
        dest="disable_socket",
        help="Disable socket.socket by default to block network calls.",
    )
    group.addoption(
        "--force-enable-socket",
        action="store_true",
        dest="force_enable_socket",
        help="Force enable socket.socket network calls (override --disable-socket).",
    )
    group.addoption(
        "--allow-hosts",
        dest="allow_hosts",
        metavar="ALLOWED_HOSTS_CSV",
        help="Only allow specified hosts through socket.socket.connect((host, port)).",
    )
    group.addoption(
        "--allow-unix-socket",
        action="store_true",
        dest="allow_unix_socket",
        help="Allow calls if they are to Unix domain sockets",
    )


@pytest.fixture
def socket_disabled(pytestconfig: pytest.Config) -> Iterator[None]:
    """disable socket.socket for duration of this test function"""
    socket_config = pytestconfig.stash[_STASH_KEY]
    disable_socket(allow_unix_socket=socket_config.allow_unix_socket)
    yield


@pytest.fixture
def socket_enabledpy(pytestconfig: pytest.Config) -> Iterator[None]:
    """enable socket.socket for duration of this test function"""
    enable_socket()
    yield


@dataclass
class _PytestSocketConfig:
    socket_disabled: bool
    socket_force_enabled: bool
    allow_unix_socket: bool
    allow_hosts: typing.Union[str, typing.List[str], None]
    resolution_cache: typing.Dict[str, typing.Set[str]] = field(default_factory=dict)


_STASH_KEY = pytest.StashKey[_PytestSocketConfig]()


def _is_unix_socket(family: int) -> bool:
    try:
        is_unix_socket = family == socket.AF_UNIX
    except AttributeError:
        # AF_UNIX not supported on Windows https://bugs.python.org/issue33408
        is_unix_socket = False
    return is_unix_socket


def disable_socket(allow_unix_socket: bool = False) -> None:
    """disable socket.socket to disable the Internet. useful in testing."""

    class GuardedSocket(socket.socket):
        """socket guard to disable socket creation (from pytest-socket)"""

        def __new__(
            cls,
            family: typing.Union[socket.AddressFamily, int] = -1,
            type: typing.Union[socket.SocketKind, int] = -1,
            proto: int = -1,
            fileno: typing.Union[int, None] = None,
        ) -> typing_extensions.Self:
            if _is_unix_socket(family) and allow_unix_socket:
                return super().__new__(
                    cls, family, type, proto, fileno  # type: ignore[call-arg]
                )

            raise SocketBlockedError()

    socket.socket = GuardedSocket  # type: ignore[misc]


def enable_socket() -> None:
    """re-enable socket.socket to enable the Internet. useful in testing."""
    socket.socket = _true_socket  # type: ignore[misc]


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

    # Store the global configs in the `pytest.Config` object.
    config.stash[_STASH_KEY] = _PytestSocketConfig(
        socket_force_enabled=config.getoption("--force-enable-socket"),
        socket_disabled=config.getoption("--disable-socket"),
        allow_unix_socket=config.getoption("--allow-unix-socket"),
        allow_hosts=config.getoption("--allow-hosts"),
    )


def pytest_runtest_setup(item: pytest.Item) -> None:
    """During each test item's setup phase,
    choose the behavior based on the configurations supplied.

    This is the bulk of the logic for the plugin.
    As the logic can be extensive, this method is allowed complexity.
    It may be refactored in the future to be more readable.

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
        disable_socket(socket_config.allow_unix_socket)
        return

    # Resolve `allow_hosts` behaviors.
    hosts = _resolve_allow_hosts(item)

    # Finally, check the global config and disable socket if needed.
    if socket_config.socket_disabled and not hosts:
        disable_socket(socket_config.allow_unix_socket)


def _resolve_allow_hosts(
    item: pytest.Item,
) -> typing.Union[str, typing.List[str], None]:
    """Resolve `allow_hosts` behaviors."""
    socket_config = item.config.stash[_STASH_KEY]

    mark_restrictions = item.get_closest_marker("allow_hosts")
    cli_restrictions = socket_config.allow_hosts
    hosts = None
    if mark_restrictions:
        hosts = mark_restrictions.args[0]
    elif cli_restrictions:
        hosts = cli_restrictions

    socket_allow_hosts(
        hosts,
        allow_unix_socket=socket_config.allow_unix_socket,
        resolution_cache=socket_config.resolution_cache,
    )
    return hosts


def pytest_runtest_teardown() -> None:
    _remove_restrictions()


def host_from_address(address: tuple[typing.Any, ...]) -> typing.Union[str, None]:
    host = address[0]
    if isinstance(host, str):
        return host
    return None


def host_from_connect_args(args: tuple[typing.Any, ...]) -> typing.Union[str, None]:
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


def resolve_hostnames(hostname: str) -> typing.Set[str]:
    try:
        return {
            addr_struct[0]  # type: ignore[misc]
            for *_, addr_struct in socket.getaddrinfo(hostname, None)
        }
    except socket.gaierror:
        return set()


def normalize_allowed_hosts(
    allowed_hosts: typing.List[str],
    resolution_cache: typing.Optional[typing.Dict[str, typing.Set[str]]] = None,
) -> typing.Dict[str, typing.Set[str]]:
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


def socket_allow_hosts(
    allowed: typing.Union[str, typing.List[str], None] = None,
    allow_unix_socket: bool = False,
    resolution_cache: typing.Optional[typing.Dict[str, typing.Set[str]]] = None,
) -> None:
    """disable socket.socket.connect() to disable the Internet. useful in testing."""
    if isinstance(allowed, str):
        allowed = allowed.split(",")

    if not isinstance(allowed, list):
        return

    allowed_ip_hosts_by_host = normalize_allowed_hosts(allowed, resolution_cache)
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
    )

    def guarded_connect(inst: socket.socket, *args: typing.Any) -> None:
        host = host_from_connect_args(args)
        if host in allowed_ip_hosts_and_hostnames or (
            _is_unix_socket(inst.family) and allow_unix_socket
        ):
            return _true_connect(inst, *args)

        raise SocketConnectBlockedError(allowed_list, host)

    socket.socket.connect = guarded_connect  # type: ignore[assignment,method-assign]


def _remove_restrictions() -> None:
    """restore socket.socket.* to allow access to the Internet. useful in testing."""
    socket.socket = _true_socket  # type: ignore[misc]
    socket.socket.connect = _true_connect  # type: ignore[method-assign]
