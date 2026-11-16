"""Serve the bundled design viewer against one project artifact."""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SNAPSHOT_CANDIDATES = (
    Path("build/workflow_plan.json"),
    Path("viewer.snapshot.json"),
    Path(".kbs/viewer.snapshot.json"),
)
DISCOVERY_FILE = Path(".kbs/viewer.json")


class ViewerServer(ThreadingHTTPServer):
    daemon_threads = True
    assets: Path
    snapshot_bytes: bytes
    snapshot_type: str
    embed: bool = False


class ViewerHandler(SimpleHTTPRequestHandler):
    server: ViewerServer

    def __init__(
        self,
        request: Any,
        client_address: Any,
        server: ViewerServer,
    ) -> None:
        super().__init__(
            request,
            client_address,
            server,
            directory=str(server.assets),
        )

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in {"/snapshot", "/api/snapshot"}:
            if self.server.embed:
                self.send_error(
                    404,
                    "snapshot is supplied by the embedding host",
                )
                return
            self.send_response(200)
            self.send_header("Content-Type", self.server.snapshot_type)
            self.send_header("Content-Length", str(len(self.server.snapshot_bytes)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(self.server.snapshot_bytes)
            return
        if path == "/":
            self.path = "/index.html"
        super().do_GET()

    def log_message(self, format: str, *args: Any) -> None:
        return


def _discovery_path(root: Path | None = None) -> Path:
    return (root or Path.cwd()) / DISCOVERY_FILE


def _api_url(host: str, port: int) -> str:
    display = "127.0.0.1" if host in {"0.0.0.0", "::", "[::]"} else host
    if ":" in display and not display.startswith("["):
        display = f"[{display}]"
    return f"http://{display}:{port}"


def _write_discovery(path: Path, api: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"api": api}), encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def _remove_discovery(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return


def add_view_command(commands: argparse._SubParsersAction[Any]) -> None:
    parser = commands.add_parser(
        "view",
        help="serve the design viewer for a workflow plan or snapshot",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=None,
        help=(
            "workflow plan, blueprint or viewer snapshot; defaults to "
            "build/workflow_plan.json"
        ),
    )
    parser.add_argument("--title", default=None, help="display title for a bare plan")
    parser.add_argument("--host", default="127.0.0.1", help="bind address")
    parser.add_argument("--port", type=int, default=8001, help="port to serve on")
    parser.add_argument("--no-open", action="store_true", help="do not open a browser")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dev",
        action="store_true",
        help=(
            "publish the snapshot API in .kbs/viewer.json so a separately "
            "started Next dev sidecar can discover it; the file is removed on exit"
        ),
    )
    mode.add_argument(
        "--embed",
        action="store_true",
        help=(
            "serve the empty viewer for an embedding host; no snapshot is read, "
            "/snapshot returns 404, and the host opens a snapshot over the "
            "message bridge"
        ),
    )
    parser.set_defaults(command_handler=run_view)


def _assets() -> Path:
    packaged = files("kg_build_system").joinpath("viewer_dist")
    if packaged.is_dir():
        return Path(str(packaged))
    source = Path(__file__).resolve().parents[4] / "viewer" / "out"
    if (source / "index.html").exists():
        return source
    raise ValueError(
        "the viewer assets are not available; install a wheel with viewer_dist "
        "or build viewer/out with `npm run build:static`"
    )


def _snapshot(path: Path | None, title: str | None) -> tuple[bytes, str]:
    selected = path
    if selected is None:
        selected = next(
            (candidate for candidate in SNAPSHOT_CANDIDATES if candidate.exists()),
            None,
        )
    if selected is None:
        raise ValueError(
            "no snapshot found; pass --snapshot or create build/workflow_plan.json"
        )
    if not selected.is_file():
        raise ValueError(f"snapshot does not exist: {selected}")

    raw = selected.read_bytes()
    if raw[:2] == b"\x1f\x8b":
        try:
            raw = gzip.decompress(raw)
        except OSError as error:
            raise ValueError(f"invalid gzip snapshot: {selected}") from error
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError(f"snapshot is not JSON: {selected}") from error

    if isinstance(document, dict) and "format" not in document:
        if {"components", "steps", "connections"} <= document.keys():
            name = title or Path.cwd().name
            document = {
                "format": "kg-viewer-snapshot",
                "version": 1,
                "name": name,
                "title": name,
                "workflow": document,
            }
        elif {"graph", "data", "assets", "bindings"} <= document.keys():
            name = title or Path.cwd().name
            document = {
                "format": "kg-viewer-snapshot",
                "version": 1,
                "name": name,
                "title": name,
                "blueprint": document,
            }
    return (
        json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode(),
        "application/json",
    )


def _serve_embedded_viewer(arguments: argparse.Namespace) -> int:
    assets = _assets()
    server = ViewerServer((arguments.host, arguments.port), ViewerHandler)
    server.assets = assets
    server.snapshot_bytes = b""
    server.snapshot_type = "application/json"
    server.embed = True
    url = f"{_api_url(arguments.host, server.server_port)}/?embed=1"
    print(f"Serving embedded viewer {url}")
    print("The host sends {type: 'open', snapshot} to the iframe.", flush=True)
    print("Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def run_view(arguments: argparse.Namespace) -> int:
    if arguments.embed:
        return _serve_embedded_viewer(arguments)
    assets = _assets()
    snapshot, snapshot_type = _snapshot(arguments.snapshot, arguments.title)
    server = ViewerServer((arguments.host, arguments.port), ViewerHandler)
    server.assets = assets
    server.snapshot_bytes = snapshot
    server.snapshot_type = snapshot_type
    api = _api_url(arguments.host, server.server_port)
    url = f"{api}/"
    discovery = _discovery_path()
    previous_discovery: tuple[bytes, int] | None = None
    if arguments.dev and discovery.exists():
        try:
            previous_discovery = (
                discovery.read_bytes(),
                discovery.stat().st_mode,
            )
        except OSError:
            previous_discovery = None
    wrote_discovery = False
    if arguments.dev:
        try:
            _write_discovery(discovery, api)
            wrote_discovery = True
        except OSError as error:
            print(
                f"warning: could not write viewer discovery file {discovery}: {error}",
                file=sys.stderr,
            )
    print(f"Serving {url}")
    if wrote_discovery:
        print(f"Discovery {discovery}")
    print("Press Ctrl+C to stop.")
    if not arguments.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if wrote_discovery:
            if previous_discovery is None:
                _remove_discovery(discovery)
            else:
                try:
                    discovery.write_bytes(previous_discovery[0])
                    os.chmod(discovery, previous_discovery[1] & 0o777)
                except OSError as error:
                    print(
                        f"warning: could not restore viewer discovery file "
                        f"{discovery}: {error}",
                        file=sys.stderr,
                    )
    return 0


__all__ = ["add_view_command"]
