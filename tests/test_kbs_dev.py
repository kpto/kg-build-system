from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

from kg_build_system.notebook import console, dev
from kg_build_system.notebook.config import load_project


def test_dev_roles_are_one_file_per_role(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KBS_DEV_DIR", str(tmp_path / "dev"))
    assert dev.dev_dir() == tmp_path / "dev"
    dev.write_role("api", "http://127.0.0.1:1111/")
    dev.write_role("viewer", "http://127.0.0.1:2222")
    roles = dev.read_roles()
    assert roles["api"]["url"] == "http://127.0.0.1:1111"
    assert roles["viewer"]["url"] == "http://127.0.0.1:2222"
    assert (tmp_path / "dev" / "api.json").is_file()
    dev.remove_role("api")
    assert "api" not in dev.read_roles()
    assert "viewer" in dev.read_roles()
    dev.remove_role("viewer")
    assert dev.read_roles() == {}


def test_api_handler_serves_config_with_the_viewer_role(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("KBS_DEV_DIR", str(tmp_path / "dev"))
    dev.write_role("viewer", "http://127.0.0.1:2222")
    project = load_project(tmp_path / "project").ensure(write_config=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), console.make_api_handler(project))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        with urlopen(f"{base}/api/config") as response:
            config = json.load(response)
        assert config["viewerUrl"] == "http://127.0.0.1:2222/?embed=1"
        assert config["dataDir"] == str(project.data_dir)
        with urlopen(f"{base}/api/health") as response:
            health = json.load(response)
        assert health["app"] == "kbs-api"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_current_view_wraps_a_bare_workflow_plan(tmp_path: Path) -> None:
    project = load_project(tmp_path / "project").ensure(write_config=True)
    plan = {
        "components": [],
        "steps": [],
        "connections": [],
        "provenance": {},
    }
    (project.snapshots_dir / "current.snapshot.json").write_text(
        json.dumps(plan), encoding="utf-8"
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), console.make_api_handler(project))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urlopen(
            f"http://127.0.0.1:{server.server_port}/api/current-view"
        ) as response:
            snapshot = json.load(response)
        assert snapshot["format"] == "kg-viewer-snapshot"
        assert snapshot["workflow"] == plan
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_integrated_handler_serves_console_viewer_and_api(
    tmp_path: Path, monkeypatch
) -> None:
    viewer = tmp_path / "viewer"
    console_export = tmp_path / "console"
    viewer.mkdir()
    console_export.mkdir()
    (viewer / "index.html").write_text("viewer export", encoding="utf-8")
    (console_export / "index.html").write_text("console export", encoding="utf-8")
    monkeypatch.setattr(console, "VIEWER_DIST", tmp_path / "missing-viewer")
    monkeypatch.setattr(console, "VIEWER_SOURCE", viewer)
    monkeypatch.setattr(console, "CONSOLE_DIST", tmp_path / "missing-console")
    monkeypatch.setattr(console, "CONSOLE_SOURCE", console_export)
    project = load_project(tmp_path / "project").ensure(write_config=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), console.make_handler(project))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        with urlopen(f"{base}/") as response:
            assert response.read().decode() == "viewer export"
        with urlopen(f"{base}/console/") as response:
            assert response.read().decode() == "console export"
        with urlopen(f"{base}/console/api/config") as response:
            config = json.load(response)
        assert config["viewerUrl"] == "/?embed=1"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
