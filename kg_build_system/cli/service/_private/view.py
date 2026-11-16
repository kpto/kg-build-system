"""Serve the bundled design viewer against one project artifact."""
from __future__ import annotations

import argparse
import gzip
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
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


def _viewer_source() -> Path | None:
    source = Path(__file__).resolve().parents[4] / "viewer"
    if (source / "next.config.ts").exists() and (source / "package.json").exists():
        return source
    return None


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


def _viewer_command(port: int, host: str) -> list[str] | None:
    """Return the source-viewer command, or ``None`` for the static viewer."""
    npm = shutil.which("npm")
    source = _viewer_source()
    if npm is None or source is None:
        return None
    if not (source / "node_modules" / ".bin" / "next").exists():
        return None
    return [
        npm, "run", "dev", "--", "--port", str(port), "--hostname", host,
    ]


def _viewer_environment(discovery: Path) -> dict[str, str]:
    environment = dict(os.environ)
    environment["KBS_DISCOVERY"] = str(discovery.resolve())
    environment["NEXT_TELEMETRY_DISABLED"] = "1"
    return environment


def _wait_for_viewer(
    host: str,
    port: int,
    *,
    process: subprocess.Popen[Any] | None = None,
    timeout: float = 90.0,
) -> bool:
    display = "127.0.0.1" if host in {"0.0.0.0", "::", "[::]"} else host
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            return False
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(0.25)
            if probe.connect_ex((display, port)) == 0:
                return True
        time.sleep(0.2)
    return False


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
    parser.add_argument(
        "--embed",
        action="store_true",
        help=(
            "serve the empty viewer for an embedding host; the host opens a "
            "snapshot over the message bridge"
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


def _serve_static_viewer(
    arguments: argparse.Namespace,
    snapshot: bytes,
    snapshot_type: str,
) -> int:
    assets = _assets()
    server = ViewerServer((arguments.host, arguments.port), ViewerHandler)
    server.assets = assets
    server.snapshot_bytes = snapshot
    server.snapshot_type = snapshot_type
    url = f"{_api_url(arguments.host, server.server_port)}/"
    print(f"Serving {url}")
    print("Press Ctrl+C to stop.", flush=True)
    if not arguments.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def _serve_source_viewer(
    arguments: argparse.Namespace,
    source: Path,
    command: list[str],
    snapshot: bytes,
    snapshot_type: str,
) -> int:
    snapshot_server = ViewerServer((arguments.host, 0), ViewerHandler)
    snapshot_server.assets = source
    snapshot_server.snapshot_bytes = snapshot
    snapshot_server.snapshot_type = snapshot_type
    snapshot_thread = threading.Thread(
        target=snapshot_server.serve_forever,
        daemon=True,
    )
    snapshot_thread.start()
    api = _api_url(arguments.host, snapshot_server.server_port)
    viewer_url = f"{_api_url(arguments.host, arguments.port)}/"
    discovery = _discovery_path()
    child: subprocess.Popen[Any] | None = None
    try:
        _write_discovery(discovery, api)
        environment = _viewer_environment(discovery)
        print(f"Snapshot API {api}", flush=True)
        print(f"Starting viewer {viewer_url}", flush=True)
        child = subprocess.Popen(
            command,
            cwd=source,
            env=environment,
        )
        if not _wait_for_viewer(
            arguments.host,
            arguments.port,
            process=child,
        ):
            raise RuntimeError(
                "the viewer did not start; run `npm run dev` in viewer/ to see "
                "the error"
            )
        print(f"Viewer {viewer_url}", flush=True)
        print(f"Discovery {discovery}", flush=True)
        print("Press Ctrl+C to stop.", flush=True)
        if not arguments.no_open:
            webbrowser.open(viewer_url)
        child.wait()
    except KeyboardInterrupt:
        pass
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        _remove_discovery(discovery)
        snapshot_server.shutdown()
        snapshot_server.server_close()
        snapshot_thread.join(timeout=5)
    return 0


def _serve_embedded_source_viewer(
    arguments: argparse.Namespace,
    source: Path,
    command: list[str],
) -> int:
    viewer_url = f"{_api_url(arguments.host, arguments.port)}/?embed=1"
    environment = dict(os.environ)
    environment["NEXT_TELEMETRY_DISABLED"] = "1"
    # Keep the embedded viewer independent of any project discovery file. The
    # host supplies the snapshot; the viewer never calls /snapshot in this mode.
    environment["INIT_CWD"] = str(source)
    child: subprocess.Popen[Any] | None = None
    try:
        print(f"Starting embedded viewer {viewer_url}", flush=True)
        child = subprocess.Popen(command, cwd=source, env=environment)
        if not _wait_for_viewer(
            arguments.host,
            arguments.port,
            process=child,
        ):
            raise RuntimeError(
                "the viewer did not start; run `npm run dev` in viewer/ to see "
                "the error"
            )
        print(f"Embedded viewer {viewer_url}", flush=True)
        print("The host sends {type: 'open', snapshot} to the iframe.", flush=True)
        print("Press Ctrl+C to stop.", flush=True)
        child.wait()
    except KeyboardInterrupt:
        pass
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
    return 0


def _serve_embedded_static_viewer(arguments: argparse.Namespace) -> int:
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
        source = _viewer_source()
        command = _viewer_command(arguments.port, arguments.host) if source else None
        if source is not None and command is not None:
            return _serve_embedded_source_viewer(arguments, source, command)
        return _serve_embedded_static_viewer(arguments)
    snapshot, snapshot_type = _snapshot(arguments.snapshot, arguments.title)
    source = _viewer_source()
    command = _viewer_command(arguments.port, arguments.host) if source else None
    if source is not None and command is not None:
        return _serve_source_viewer(
            arguments,
            source,
            command,
            snapshot,
            snapshot_type,
        )
    return _serve_static_viewer(arguments, snapshot, snapshot_type)

__all__ = ["add_view_command"]
