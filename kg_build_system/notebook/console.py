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

from . import relations
from .config import Project

ASSETS = Path(__file__).with_name("console")
DEFAULT_VIEWER_URL = "http://127.0.0.1:3000/?embed=1"


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, separators=(",", ":"), default=str).encode("utf-8")


def _asset(name: str) -> Path | None:
    candidate = (ASSETS / name).resolve()
    assets = ASSETS.resolve()
    if assets not in candidate.parents and candidate != assets:
        return None
    return candidate if candidate.is_file() else None


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


def make_handler(project: Project, viewer_url: str) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "kbs-console/0.1"

        def do_GET(self) -> None:  # noqa: N802 - stdlib hook
            parsed = urlparse(self.path)
            path = parsed.path
            if path == "/api/relations":
                self._send_json(relations.graph(project))
                return
            if path == "/api/config":
                self._send_json(
                    {
                        "viewerUrl": viewer_url,
                        "project": project.name,
                        "dataDir": str(project.data_dir),
                    }
                )
                return
            if path == "/api/current-view":
                current = _current(project, "current.snapshot.json")
                if current is None:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                self._send_file(current, "application/json; charset=utf-8")
                return
            if path == "/api/graph-subject":
                query = parse_qs(parsed.query)
                value = unquote(query.get("key", [""])[0])
                self._send_json(_subject_payload(project, value))
                return
            if path == "/api/revision-view":
                query = parse_qs(parsed.query)
                revision = unquote(query.get("revision", [""])[0])
                view = _revision_view(project, revision)
                if view is None:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                self._send_file(view, "application/json; charset=utf-8")
                return
            name = "index.html" if path in {"/", ""} else path.lstrip("/")
            asset = _asset(name)
            if asset is None:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            content_type = mimetypes.guess_type(asset.name)[0] or "application/octet-stream"
            self._send_file(asset, content_type)

        def _send_file(self, path: Path, content_type: str) -> None:
            body = path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, value: Any) -> None:
            body = _json_bytes(value)
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            print(f"{self.address_string()} {format % args}")

    return Handler


def serve(
    project: Project,
    *,
    host: str = "127.0.0.1",
    port: int = 8787,
    viewer_url: str = DEFAULT_VIEWER_URL,
) -> None:
    project.ensure()
    relations.graph(project)
    server = ThreadingHTTPServer((host, port), make_handler(project, viewer_url))
    print(f"kbs console: http://{host}:{port}/", flush=True)
    print(f"Project: {project.root}", flush=True)
    print(f"Notebook: {project.data_dir}", flush=True)
    print(f"Design viewer: {viewer_url}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


__all__ = ["ASSETS", "DEFAULT_VIEWER_URL", "make_handler", "serve"]
