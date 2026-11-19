"""A standalone web console for one project's state directory."""

from __future__ import annotations

import json
import mimetypes
from collections import defaultdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from . import dev, relations
from .config import Project

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
VIEWER_DIST = PACKAGE_ROOT / "viewer_dist"
CONSOLE_DIST = PACKAGE_ROOT / "console_dist"
VIEWER_SOURCE = REPO_ROOT / "viewer" / "design" / "out"
CONSOLE_SOURCE = REPO_ROOT / "viewer" / "console" / "out"
VIEWER_URL = "/?embed=1"


def _asset_root(packaged: Path, source: Path) -> Path | None:
    for candidate in (packaged, source):
        if (candidate / "index.html").is_file():
            return candidate
    return None


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, separators=(",", ":"), default=str).encode("utf-8")


def _display_host(host: str) -> str:
    return "127.0.0.1" if host in {"0.0.0.0", "::", "[::]"} else host


def _viewer_bytes(path: Path, project: Project) -> bytes:
    """Wrap a bare workflow plan or blueprint as a viewer snapshot."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return path.read_bytes()
    if isinstance(value, dict) and "format" not in value:
        if {"components", "steps", "connections"} <= value.keys():
            value = {
                "format": "kg-viewer-snapshot",
                "version": 1,
                "name": project.name,
                "title": project.name,
                "workflow": value,
            }
        elif {"graph", "data", "assets", "bindings"} <= value.keys():
            value = {
                "format": "kg-viewer-snapshot",
                "version": 1,
                "name": project.name,
                "title": project.name,
                "blueprint": value,
            }
    return _json_bytes(value)


def _dev_viewer_url(project: Project) -> str:
    """The viewer URL a development console should embed."""

    entry = dev.read_role("viewer")
    url = str(entry.get("url") or "").strip()
    if url:
        return f"{url.rstrip('/')}/?embed=1"
    return ""


def _current(project: Project, name: str) -> Path | None:
    candidate = project.snapshots_dir / name
    return candidate if candidate.is_file() else None


def _revision_view(project: Project, revision: str) -> Path | None:
    """Resolve a revision to its captured viewer file, if one exists."""
    if not revision or Path(revision).name != revision:
        return None
    return relations.view_file_for(project, revision)


_GRAPH_CACHE: dict[str, dict[str, Any]] = {}


def _graph_index(project: Project) -> dict[str, Any] | None:
    """Read the standard build artifacts once and index them for lookup.

    The console is a reader of the project directory; it does not rebuild or
    mutate the graph. The index is cached until ``graph.jsonl`` changes.
    """

    graph_path = project.root / "data" / "build" / "graph.jsonl"
    if not graph_path.is_file():
        return None
    mtime = graph_path.stat().st_mtime
    cached = _GRAPH_CACHE.get(str(project.root))
    if cached is not None and cached.get("mtime") == mtime:
        return cached
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    for line in graph_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("kind") == "node":
            key = record.get("build_key")
            if key:
                nodes[key] = record
        elif record.get("kind") == "edge":
            edges.append(record)
    evidence: dict[str, dict[str, Any]] = {}
    evidence_path = project.root / "data" / "build" / "evidence.jsonl"
    if evidence_path.is_file():
        for line in evidence_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            key = record.get("build_key")
            if key:
                evidence[key] = record
    by_endpoint: dict[str, list[dict[str, Any]]] = defaultdict(list)
    edges_by_key: dict[str, dict[str, Any]] = {}
    for edge in edges:
        key = edge.get("build_key")
        if key:
            edges_by_key[key] = edge
        for endpoint in (edge.get("source_build_key"), edge.get("target_build_key")):
            if endpoint:
                by_endpoint[endpoint].append(edge)
    index = {
        "mtime": mtime,
        "nodes": nodes,
        "edges": edges,
        "edges_by_key": edges_by_key,
        "by_endpoint": by_endpoint,
        "evidence": evidence,
    }
    _GRAPH_CACHE[str(project.root)] = index
    return index


def _subject_payload(project: Project, key: str) -> dict[str, Any]:
    """Resolve one selected node or edge key to graph records."""

    index = _graph_index(project)
    if index is None:
        return {"ok": False, "error": "data/build/graph.jsonl is absent"}
    text = key.strip()
    if not text:
        return {"ok": False, "error": "empty key"}
    nodes = index["nodes"]
    evidence = index["evidence"]
    node = nodes.get(text)
    if node is not None:
        key = node.get("build_key")
        edge_payloads = []
        for edge in index["by_endpoint"].get(key, []):
            sidecar = evidence.get(edge.get("build_key"), {})
            source = edge.get("source_build_key")
            target = edge.get("target_build_key")
            edge_payloads.append(
                {
                    "build_key": edge.get("build_key"),
                    "type": edge.get("type"),
                    "source": source,
                    "target": target,
                    "source_label": nodes.get(source, {}).get("label") or nodes.get(source, {}).get("name"),
                    "target_label": nodes.get(target, {}).get("label") or nodes.get(target, {}).get("name"),
                    "evidence_total": sidecar.get("evidence_total", 0),
                    "evidence": (sidecar.get("evidence") or [])[:3],
                    "source_file": (sidecar.get("source") or {}).get("file"),
                }
            )
        return {"ok": True, "node": node, "edges": edge_payloads}
    edge = index["edges_by_key"].get(text)
    if edge is not None:
        sidecar = evidence.get(text, {})
        return {
            "ok": True,
            "node": None,
            "edge": {
                "build_key": edge.get("build_key"),
                "type": edge.get("type"),
                "source": edge.get("source_build_key"),
                "target": edge.get("target_build_key"),
                "source_label": nodes.get(edge.get("source_build_key"), {}).get("label"),
                "target_label": nodes.get(edge.get("target_build_key"), {}).get("label"),
                "evidence_total": sidecar.get("evidence_total", 0),
                "evidence": sidecar.get("evidence") or [],
                "source_file": (sidecar.get("source") or {}).get("file"),
            },
        }
    return {"ok": False, "error": "no subject matched"}


def _api_response(
    project: Project,
    parsed: Any,
    viewer_url: str,
) -> tuple[int, str, bytes] | None:
    """Resolve one API request; return ``(status, content type, body)``."""

    path = parsed.path
    if path in {"/api/relations", "/console/api/relations"}:
        return 200, "application/json; charset=utf-8", _json_bytes(relations.graph(project))
    if path in {"/api/config", "/console/api/config"}:
        return (
            200,
            "application/json; charset=utf-8",
            _json_bytes(
                {
                    "viewerUrl": viewer_url,
                    "project": project.name,
                    "dataDir": str(project.data_dir),
                }
            ),
        )
    if path in {"/api/current-view", "/console/api/current-view"}:
        current = _current(project, "current.snapshot.json")
        if current is None:
            return 404, "text/plain; charset=utf-8", b"no current snapshot"
        return 200, "application/json; charset=utf-8", _viewer_bytes(current, project)
    if path in {"/api/revision-view", "/console/api/revision-view"}:
        query = parse_qs(parsed.query)
        revision = unquote(query.get("revision", [""])[0])
        view = _revision_view(project, revision)
        if view is None:
            return 404, "text/plain; charset=utf-8", b"no revision view"
        return 200, "application/json; charset=utf-8", _viewer_bytes(view, project)
    if path in {"/api/graph-subject", "/console/api/graph-subject"}:
        query = parse_qs(parsed.query)
        value = unquote(query.get("key", [""])[0])
        return 200, "application/json; charset=utf-8", _json_bytes(_subject_payload(project, value))
    if path in {"/api/health", "/console/api/health"}:
        return 200, "application/json; charset=utf-8", _json_bytes(
            {"app": "kbs-api", "project": project.name}
        )
    return None


def make_handler(project: Project) -> type[BaseHTTPRequestHandler]:
    """Serve the integrated console, viewer and API on one origin."""

    viewer_root = _asset_root(VIEWER_DIST, VIEWER_SOURCE)
    console_root = _asset_root(CONSOLE_DIST, CONSOLE_SOURCE)

    class Handler(BaseHTTPRequestHandler):
        server_version = "kbs-console/0.1"

        def do_GET(self) -> None:  # noqa: N802 - stdlib hook
            parsed = urlparse(self.path)
            path = parsed.path
            response = _api_response(project, parsed, VIEWER_URL)
            if response is not None:
                self._send_response(response)
                return
            if path == "/console":
                self.send_response(HTTPStatus.MOVED_PERMANENTLY)
                self.send_header("Location", "/console/")
                self.end_headers()
                return
            if path == "/snapshot":
                current = _current(project, "current.snapshot.json")
                if current is None:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                self._send_bytes(_viewer_bytes(current, project), "application/json; charset=utf-8")
                return
            if path.startswith("/console/"):
                relative = path[len("/console/"):] or "index.html"
                root = console_root
            else:
                relative = "index.html" if path in {"/", ""} else path.lstrip("/")
                root = viewer_root
            asset = self._static(root, relative)
            if asset is None:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self._send_bytes(asset.read_bytes(), mimetypes.guess_type(asset.name)[0] or "application/octet-stream")

        def _send_response(self, response: tuple[int, str, bytes]) -> None:
            status, content_type, body = response
            if status != 200:
                self.send_error(status, body.decode("utf-8", "replace"))
                return
            self._send_bytes(body, content_type)

        @staticmethod
        def _static(root: Path | None, relative: str) -> Path | None:
            if root is None:
                return None
            base = root.resolve()
            candidate = (base / relative).resolve()
            if base not in candidate.parents and candidate != base:
                return None
            return candidate if candidate.is_file() else None

        def _send_bytes(self, body: bytes, content_type: str) -> None:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            print(f"{self.address_string()} {format % args}")

    return Handler


def make_api_handler(project: Project) -> type[BaseHTTPRequestHandler]:
    """API-only handler used by ``kbs console --api-only``."""

    class Handler(BaseHTTPRequestHandler):
        server_version = "kbs-api/0.1"

        def do_GET(self) -> None:  # noqa: N802 - stdlib hook
            parsed = urlparse(self.path)
            response = _api_response(project, parsed, _dev_viewer_url(project))
            if response is None:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            status, content_type, body = response
            if status != 200:
                self.send_error(status, body.decode("utf-8", "replace"))
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            print(f"{self.address_string()} {format % args}")

    return Handler


def serve_api(
    project: Project,
    *,
    host: str = "127.0.0.1",
    port: int = 0,
) -> None:
    """Serve only the notebook API and publish the ``api`` dev role."""

    project.ensure()
    server = ThreadingHTTPServer((host, port), make_api_handler(project))
    url = f"http://{_display_host(host)}:{server.server_port}"
    dev.write_role("api", url)
    print(f"kbs console API: {url}", flush=True)
    print(f"Project: {project.root}", flush=True)
    print(f"Notebook: {project.data_dir}", flush=True)
    previous = None
    try:
        import signal

        def stop(signum: int, frame: object) -> None:
            raise KeyboardInterrupt

        previous = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGTERM, stop)
    except (ImportError, OSError, ValueError):
        previous = None
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if previous is not None:
            try:
                import signal

                signal.signal(signal.SIGTERM, previous)
            except (OSError, ValueError):
                pass
        server.server_close()
        dev.remove_role("api")


def serve(
    project: Project,
    *,
    host: str = "127.0.0.1",
    port: int = 0,
) -> None:
    """Serve the console, the design viewer and the API on one origin."""

    project.ensure()
    if _asset_root(VIEWER_DIST, VIEWER_SOURCE) is None:
        raise ValueError(
            "design viewer assets are missing; viewer/ is the npm workspace root. "
            "From the repository run:\n"
            "  cd viewer && npm ci\n"
            "  npm run build:static --workspace design"
        )
    if _asset_root(CONSOLE_DIST, CONSOLE_SOURCE) is None:
        raise ValueError(
            "console assets are missing; viewer/ is the npm workspace root. "
            "From the repository run:\n"
            "  cd viewer && npm ci\n"
            "  npm run build:static --workspace console"
        )
    server = ThreadingHTTPServer((host, port), make_handler(project))
    display = _display_host(host)
    print(f"kbs console: http://{display}:{server.server_port}/console/", flush=True)
    print(f"Project: {project.root}", flush=True)
    print(f"Notebook: {project.data_dir}", flush=True)
    print(f"Design viewer: http://{display}:{server.server_port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


__all__ = [
    "CONSOLE_DIST",
    "VIEWER_DIST",
    "make_api_handler",
    "make_handler",
    "serve",
    "serve_api",
]
