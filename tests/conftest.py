import socket
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

pytest_plugins = "pytester"


unix_sockets_only = pytest.mark.skipif(
    not hasattr(socket, "AF_UNIX"),
    reason="Skip any platform that does not support AF_UNIX",
)


class _SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args) -> None:
        pass  # suppress request logging during tests


@dataclass
class _ServerInfo:
    host: str
    port: int

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


@pytest.fixture(scope="session")
def httpserver() -> _ServerInfo:
    """A lightweight local HTTP server for testing socket connections."""
    server = HTTPServer(("127.0.0.1", 0), _SimpleHandler)
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    yield _ServerInfo(host=host, port=port)
    server.shutdown()
