from __future__ import annotations

import http.client
import json
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

import pytest

from kg_build_system.cli.service._private.dev.env import load_dev_config
from kg_build_system.cli.service._private.dev.proxy import (
    Route,
    make_proxy_server,
    route_for,
)
from kg_build_system.cli.service._private.dev.service import _bind
from kg_build_system.cli.service._private.dev.session import DevSession


def test_dev_env_reads_only_the_two_commands(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text(
        "OTHER=ignored\n"
        'KBS_DEV_VIEWER="node scripts/dev-server.mjs viewer/design"\n'
        "KBS_DEV_CONSOLE=node scripts/dev-server.mjs viewer/console\n",
        encoding="utf-8",
    )
    config = load_dev_config(env)
    assert config.cwd == tmp_path
    assert config.command("viewer") == "node scripts/dev-server.mjs viewer/design"
    assert config.command("console") == "node scripts/dev-server.mjs viewer/console"


def test_dev_env_requires_a_command(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("KBS_DEV_VIEWER=viewer\n", encoding="utf-8")
    config = load_dev_config(env)
    with pytest.raises(ValueError, match="KBS_DEV_CONSOLE"):
        config.command("console")


def test_route_for_uses_the_longest_prefix() -> None:
    routes = [
        Route("/", "127.0.0.1", 11, "http://127.0.0.1:11"),
        Route("/console", "127.0.0.1", 22, "http://127.0.0.1:22"),
    ]
    assert route_for(routes, "/").port == 11  # type: ignore[union-attr]
    assert route_for(routes, "/console/").port == 22  # type: ignore[union-attr]
    assert route_for(routes, "/console/_next/app.js").port == 22  # type: ignore[union-attr]
    assert route_for(routes, "/consolefoo").port == 11  # type: ignore[union-attr]


def test_proxy_routes_local_and_upstream(tmp_path: Path) -> None:
    class Upstream(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            body = f"upstream:{self.path}:{self.headers.get('Host')}".encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: object) -> None:
            pass

    upstream = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
    thread = threading.Thread(target=upstream.serve_forever, daemon=True)
    thread.start()
    server = make_proxy_server(
        "127.0.0.1",
        0,
        lambda path: (200, "text/plain", b"local") if path.startswith("/snapshot") else None,
        [Route("/", "127.0.0.1", upstream.server_port, f"http://127.0.0.1:{upstream.server_port}")],
    )
    proxy = threading.Thread(target=server.serve_forever, daemon=True)
    proxy.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        with urlopen(f"{base}/snapshot") as response:
            assert response.read() == b"local"
        with urlopen(f"{base}/page") as response:
            body = response.read().decode()
        assert body.startswith("upstream:/page:127.0.0.1:")
        assert f"127.0.0.1:{upstream.server_port}" in body
    finally:
        server.shutdown()
        server.server_close()
        upstream.shutdown()
        upstream.server_close()
        proxy.join(timeout=5)
        thread.join(timeout=5)


def _fake_server_script(tmp_path: Path, first_line: str) -> Path:
    path = tmp_path / "server.py"
    path.write_text(
        "import sys\n"
        "from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer\n"
        "class H(BaseHTTPRequestHandler):\n"
        "    def do_GET(self):\n"
        "        body=b'ok'\n"
        "        self.send_response(200)\n"
        "        self.send_header('Content-Length', str(len(body)))\n"
        "        self.end_headers()\n"
        "        self.wfile.write(body)\n"
        "    def log_message(self, *args): pass\n"
        "server=ThreadingHTTPServer(('127.0.0.1', 0), H)\n"
        f"print({first_line!r} if {first_line!r} != 'PORT' else server.server_port, flush=True)\n"
        "server.serve_forever()\n",
        encoding="utf-8",
    )
    return path


def test_session_reads_the_first_line_port_and_stops(tmp_path: Path) -> None:
    script = _fake_server_script(tmp_path, "PORT")
    session = DevSession()
    try:
        server = session.start(
            "viewer",
            f"{sys.executable} {script}",
            tmp_path,
            health_path="/",
        )
        assert 1 <= server.port <= 65535
    finally:
        session.stop()
    assert server.process.poll() is not None


def test_session_rejects_a_non_port_first_line(tmp_path: Path) -> None:
    script = _fake_server_script(tmp_path, "not-a-port")
    session = DevSession()
    with pytest.raises(RuntimeError, match="first line"):
        session.start(
            "viewer",
            f"{sys.executable} {script}",
            tmp_path,
            health_path="/",
        )
    session.stop()


def test_bind_tries_the_next_port(monkeypatch, tmp_path: Path) -> None:
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    probe.listen(1)
    busy = probe.getsockname()[1]
    from kg_build_system.cli.service._private.dev import service

    monkeypatch.setattr(service, "DEFAULT_PORT", busy)
    server = _bind("127.0.0.1", None, lambda path: None, [])
    try:
        assert server.server_port != busy
    finally:
        server.server_close()
        probe.close()
