"""A small HTTP/WebSocket reverse proxy for kbs dev mode."""

from __future__ import annotations

from dataclasses import dataclass
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import socket
import threading
from typing import Callable
from urllib.parse import urlsplit, urlunsplit

LocalData = Callable[[str], tuple[int, str, bytes] | None]

_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}


@dataclass(frozen=True)
class Route:
    prefix: str
    host: str
    port: int
    origin: str


def _matches(prefix: str, path: str) -> bool:
    if prefix == "/":
        return True
    return path == prefix or path.startswith(f"{prefix}/")


def route_for(routes: list[Route], path: str) -> Route | None:
    for route in sorted(routes, key=lambda item: len(item.prefix), reverse=True):
        if _matches(route.prefix, path):
            return route
    return None


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    local: LocalData
    routes: list[Route]


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server: _Server

    def log_message(self, format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        self._handle("GET")

    def do_HEAD(self) -> None:  # noqa: N802
        self._handle("HEAD")

    def do_POST(self) -> None:  # noqa: N802
        self._handle("POST")

    def do_PUT(self) -> None:  # noqa: N802
        self._handle("PUT")

    def do_PATCH(self) -> None:  # noqa: N802
        self._handle("PATCH")

    def do_DELETE(self) -> None:  # noqa: N802
        self._handle("DELETE")

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._handle("OPTIONS")

    def _handle(self, method: str) -> None:
        try:
            path = self.path
            local = self.server.local(path)
            if local is not None:
                self._send_local(method, *local)
                return
            route = route_for(self.server.routes, urlsplit(path).path)
            if route is None:
                self.send_error(404)
                return
            if self.headers.get("Upgrade", "").lower() == "websocket":
                self._websocket(route)
                return
            self._http(method, route)
        except (BrokenPipeError, ConnectionResetError):
            # A browser or health probe closed the connection first.
            self.close_connection = True

    def _send_local(
        self,
        method: str,
        status: int,
        content_type: str,
        body: bytes,
    ) -> None:
        self.send_response_only(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if method != "HEAD":
            self.wfile.write(body)

    def _upstream_headers(self, route: Route) -> list[tuple[str, str]]:
        headers: list[tuple[str, str]] = []
        original_origin = self.headers.get("Origin")
        original_referer = self.headers.get("Referer")
        for key, value in self.headers.items():
            lowered = key.lower()
            if lowered in _HOP or lowered in {
                "host",
                "origin",
                "referer",
                "content-length",
            } or lowered.startswith("sec-websocket-"):
                continue
            headers.append((key, value))
        headers.append(("Host", f"{route.host}:{route.port}"))
        if original_origin is not None:
            headers.append(("Origin", route.origin))
        if original_referer is not None:
            referer = urlsplit(original_referer)
            headers.append(
                (
                    "Referer",
                    urlunsplit((*urlsplit(route.origin)[:2], referer.path, referer.query, "")),
                )
            )
        forwarded = self.headers.get("X-Forwarded-For")
        client = self.client_address[0] if self.client_address else ""
        headers.append(
            ("X-Forwarded-For", f"{forwarded}, {client}" if forwarded else client)
        )
        headers.append(
            (
                "X-Forwarded-Host",
                self.headers.get("Host") or f"127.0.0.1:{self.server.server_port}",
            )
        )
        headers.append(("X-Forwarded-Proto", "http"))
        return headers

    def _request_body(self) -> bytes:
        if self.headers.get("Transfer-Encoding", "").lower() == "chunked":
            chunks: list[bytes] = []
            while True:
                line = self.rfile.readline().strip()
                size = int(line.split(b";", 1)[0] or b"0", 16)
                if size == 0:
                    self.rfile.readline()
                    return b"".join(chunks)
                chunks.append(self.rfile.read(size))
                self.rfile.read(2)
        length = int(self.headers.get("Content-Length") or "0")
        return self.rfile.read(length) if length else b""

    def _http(self, method: str, route: Route) -> None:
        body = self._request_body()
        connection = HTTPConnection(route.host, route.port, timeout=60)
        try:
            connection.putrequest(
                method,
                self.path,
                skip_host=True,
                skip_accept_encoding=True,
            )
            for key, value in self._upstream_headers(route):
                connection.putheader(key, value)
            if body:
                connection.putheader("Content-Length", str(len(body)))
            connection.endheaders(body or None)
            response = connection.getresponse()
            status = response.status
            reason = response.reason
            content_length = response.getheader("Content-Length")
            body_allowed = method != "HEAD" and status not in {204, 304}
            self.send_response_only(status, reason)
            location = response.getheader("Location")
            public = self.headers.get("Host") or f"127.0.0.1:{self.server.server_port}"
            for key, value in response.getheaders():
                lowered = key.lower()
                if lowered in _HOP or lowered in {"content-length", "location"}:
                    continue
                self.send_header(key, value)
            if location is not None:
                self.send_header("Location", self._public_location(location, route, public))
            if body_allowed and content_length is not None:
                self.send_header("Content-Length", content_length)
            elif body_allowed:
                self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            if body_allowed:
                if content_length is not None:
                    self._copy_body(response, chunked=False)
                else:
                    self._copy_body(response, chunked=True)
        finally:
            connection.close()

    def _public_location(self, location: str, route: Route, public: str) -> str:
        parsed = urlsplit(location)
        if not parsed.scheme or not parsed.netloc:
            return location
        upstream = f"{parsed.hostname}:{parsed.port or (443 if parsed.scheme == 'https' else 80)}"
        expected = f"{route.host}:{route.port}"
        if upstream not in {expected, f"127.0.0.1:{route.port}", f"localhost:{route.port}"}:
            return location
        return urlunsplit(("http", public, parsed.path, parsed.query, parsed.fragment))

    def _copy_body(self, response: object, *, chunked: bool) -> None:
        reader = getattr(response, "read")
        while True:
            data = reader(65536)
            if not data:
                break
            if chunked:
                self.wfile.write(f"{len(data):x}\r\n".encode() + data + b"\r\n")
            else:
                self.wfile.write(data)
        if chunked:
            self.wfile.write(b"0\r\n\r\n")
        self.wfile.flush()

    def _websocket(self, route: Route) -> None:
        upstream = socket.create_connection((route.host, route.port), timeout=10)
        lines = [f"GET {self.path} HTTP/1.1"]
        for key, value in self._upstream_headers(route):
            lines.append(f"{key}: {value}")
        # The HTTP Upgrade headers are hop-by-hop and were removed above.
        for key in ("Connection", "Upgrade", "Sec-WebSocket-Key", "Sec-WebSocket-Version", "Sec-WebSocket-Protocol", "Sec-WebSocket-Extensions"):
            value = self.headers.get(key)
            if value:
                lines.append(f"{key}: {value}")
        upstream.sendall(("\r\n".join(lines) + "\r\n\r\n").encode())
        header = b""
        while b"\r\n\r\n" not in header:
            data = upstream.recv(4096)
            if not data:
                upstream.close()
                return
            header += data
        self.connection.sendall(header)
        if not header.startswith(b"HTTP/1.1 101") and not header.startswith(b"HTTP/1.0 101"):
            upstream.close()
            self.close_connection = True
            return
        upstream.settimeout(None)
        self.connection.settimeout(None)

        def pump(source: socket.socket, target: socket.socket) -> None:
            try:
                while True:
                    data = source.recv(65536)
                    if not data:
                        break
                    target.sendall(data)
            except OSError:
                pass
            finally:
                try:
                    target.shutdown(socket.SHUT_WR)
                except OSError:
                    pass

        thread = threading.Thread(target=pump, args=(upstream, self.connection), daemon=True)
        thread.start()
        pump(self.connection, upstream)
        thread.join(timeout=5)
        upstream.close()
        self.close_connection = True


def make_proxy_server(
    host: str,
    port: int,
    local: LocalData,
    routes: list[Route],
) -> ThreadingHTTPServer:
    server = _Server((host, port), _Handler)
    server.local = local
    server.routes = routes
    return server
