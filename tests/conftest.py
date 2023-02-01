import socket

import pytest

pytest_plugins = "pytester"


unix_sockets_only = pytest.mark.skipif(
    not hasattr(socket, "AF_UNIX"),
    reason="Skip any platform that does not support AF_UNIX",
)
