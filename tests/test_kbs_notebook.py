from __future__ import annotations

import json
import sys
import threading

import pytest

from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.request import urlopen

from kg_build_system.notebook import ledger, project_commands, relations, revisions
from kg_build_system.notebook.config import load_project, write_config_file
from kg_build_system.notebook.cli import main
from kg_build_system.notebook.console import make_handler
from kg_build_system.notebook.snapshot import import_snapshot


def _project(root: Path) -> Path:
    (root / "notebook" / "eval").mkdir(parents=True)
    (root / "data" / "snapshots").mkdir(parents=True)
    for name in ("events", "revisions", "findings", "proposals", "designs", "documents", "views"):
        (root / "notebook" / "records" / name).mkdir(parents=True)
    (root / "notebook" / "records" / "revisions" / "abc123.json").write_text(
        json.dumps(
            {
                "revision": "abc123",
                "recorded_at": "2026-11-16T10:00:00+00:00",
                "manifest": "deadbeefcafe",
                "counts": {"nodes": 3, "edges": 2},
                "evaluation": {"passed": 1, "suites": 1},
                "version": "1.0",
            }
        ),
        encoding="utf-8",
    )
    (root / "notebook" / "eval" / "design.json").write_text(
        json.dumps(
            {
                "modes": [
                    {
                        "name": "quick",
                        "report": "notebook/eval/quick.json",
                        "runs": ["audit"],
                        "note": "A quick check.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (root / "notebook" / "eval" / "quick.json").write_text(
        json.dumps(
            {
                "format": "kg-eval-report",
                "mode": "quick",
                "revision": {"blueprint_fingerprint": "abc123"},
                "summary": {"status": "passed", "passed": 1, "suites": 1},
                "suites": {
                    "audit": {
                        "status": "passed",
                        "metrics": {"node_count": 3, "edge_count": 2, "record_count": 5},
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    (root / "notebook" / "records" / "findings" / "F-0001.json").write_text(
        json.dumps(
            {
                "id": "F-0001",
                "opened": "2026-11-16T10:01:00+00:00",
                "layer": "design",
                "observation": "A finding.",
                "decision": "accepted",
                "metric": "m",
                "state": "accepted",
            }
        ),
        encoding="utf-8",
    )
    (root / "notebook" / "records" / "proposals" / "P-0002.json").write_text(
        json.dumps(
            {
                "id": "P-0002",
                "opened": "2026-11-16T10:02:00+00:00",
                "layer": "proposal",
                "subject": "node:disease",
                "observation": "Try this change.",
                "state": "proposed",
            }
        ),
        encoding="utf-8",
    )
    (root / "data" / "snapshots" / "current.snapshot.json").write_text(
        json.dumps(
            {
                "format": "kg-viewer-snapshot",
                "version": 1,
                "name": "demo",
                "title": "Demo snapshot",
                "blueprint": {
                    "graph": {"nodes": [], "edges": []},
                    "data": {"structs": [], "relations": [], "projections": []},
                    "assets": [],
                    "bindings": [],
                },
                "workflow": {
                    "components": [],
                    "steps": [],
                    "connections": [],
                    "provenance": None,
                },
            }
        ),
        encoding="utf-8",
    )
    return root


def test_init_creates_the_project_data_directory(tmp_path: Path) -> None:
    _project(tmp_path)
    project = load_project(tmp_path)
    project.ensure(write_config=True)
    assert (tmp_path / "notebook" / "config.json").is_file()
    assert (tmp_path / "notebook" / "records" / "revisions").is_dir()
    assert (tmp_path / "notebook" / "records" / "events").is_dir()
    assert not (tmp_path / ".notebook").exists()


def test_catalog_and_timeline_are_derived_from_project_artifacts(tmp_path: Path) -> None:
    _project(tmp_path)
    payload = relations.graph(load_project(tmp_path))
    ids = {row["id"] for row in payload["objects"]}
    assert {"KG-abc123", "ED-QUICK", "EV-QUICK", "ER-QUICK", "F-0001", "P-0002"} <= ids
    assert all(row["created"] for row in payload["objects"])
    assert any(row["type"] == "kg_edited" for row in payload["timeline"])
    assert any(row["type"] == "evaluation_run" for row in payload["timeline"])
    assert any(row["type"] == "design_proposed" for row in payload["timeline"])


def test_snapshot_import_attaches_the_view_to_the_revision(tmp_path: Path) -> None:
    _project(tmp_path)
    project = load_project(tmp_path)
    result = import_snapshot(
        project,
        source="data/snapshots/current.snapshot.json",
        revision="abc123",
    )
    assert Path(result["snapshot"]).is_file()
    assert Path(result["snapshot_history"]).is_file()
    assert Path(result["snapshot_history"]).name != result["snapshot_file"]
    payload = relations.graph(project)
    assert not [row for row in payload["objects"] if row["kind"] == "snapshot"]
    revision = next(row for row in payload["objects"] if row["id"] == "KG-abc123")
    assert revision["view_file"].endswith(".snapshot.json")
    assert not any(row["type"] == "snapshot_saved" for row in payload["timeline"])
    edited = next(row for row in payload["timeline"] if row["type"] == "kg_edited")
    assert edited["view_file"] == revision["view_file"]


def test_state_is_file_based_under_notebook(tmp_path: Path) -> None:
    _project(tmp_path)
    project = load_project(tmp_path)
    relations.graph(project)
    assert project.data_dir.name == "notebook"
    assert (project.data_dir / "records" / "revisions" / "abc123.json").is_file()
    assert not (project.data_dir / "relations.db").exists()


def test_console_serves_current_and_revision_views(tmp_path: Path) -> None:
    _project(tmp_path)
    project = load_project(tmp_path)
    import_snapshot(
        project,
        source="data/snapshots/current.snapshot.json",
        revision="abc123",
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(project))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        with urlopen(f"{base}/api/current-view") as response:
            current = json.load(response)
        assert current["format"] == "kg-viewer-snapshot"
        with urlopen(f"{base}/api/config") as response:
            config = json.load(response)
        assert config["viewerUrl"] == "/?embed=1"
        with urlopen(
            f"{base}/api/revision-view?revision=KG-abc123"
        ) as response:
            archived = json.load(response)
        assert archived["name"] == current["name"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_sql_query_is_gone() -> None:
    assert not hasattr(relations, "query")


def test_configured_project_commands_are_parsed(tmp_path: Path) -> None:
    _project(tmp_path)
    script = tmp_path / "facts.py"
    script.write_text(
        "import json\n"
        "print(json.dumps({'ok': True, 'revision': 'rev1', 'manifest': 'm1', "
        "'counts': {'nodes': 3}, 'blueprint': {'nodes': 3}}))\n",
        encoding="utf-8",
    )
    project = load_project(tmp_path).ensure()
    project.config["commands"] = {"status": f"{sys.executable} {script}"}
    write_config_file(project)
    result = project_commands.run(load_project(tmp_path), "status")
    assert result["ok"] is True
    assert result["blueprint"]["nodes"] == 3


def test_revision_record_uses_project_facts_and_the_report(tmp_path: Path) -> None:
    _project(tmp_path)
    script = tmp_path / "facts.py"
    script.write_text(
        "import json\n"
        "print(json.dumps({'ok': True, 'revision': 'rev1', 'manifest': 'm1', "
        "'counts': {'nodes': 3}, 'version': '1.0'}))\n",
        encoding="utf-8",
    )
    project = load_project(tmp_path).ensure()
    project.config["commands"] = {"revision_facts": f"{sys.executable} {script}"}
    write_config_file(project)
    result = revisions.record_revision(load_project(tmp_path))
    assert result["ok"] is True
    record = json.loads(Path(result["path"]).read_text(encoding="utf-8"))
    assert record["revision"] == "rev1"
    assert record["evaluation"]["status"] == "passed"


def test_ledger_accepts_and_updates_a_finding(tmp_path: Path) -> None:
    path = tmp_path / "findings.jsonl"
    row = {
        "id": "F-0001",
        "opened": "2026-11-16T10:00:00+00:00",
        "layer": "design",
        "observation": "The graph is stale.",
        "evidence": "data/build/graph.jsonl",
        "decision": "Rebuild it.",
        "metric": "audit passes",
        "state": "proposed",
    }
    assert ledger.append_finding(path, row)["status"] == "accepted"
    assert ledger.next_id(ledger.read_ledger(path)[0]) == "F-0002"
    updated = ledger.update_state(path, "F-0001", "accepted", note="Gate moved.")
    assert updated["status"] == "accepted"
    assert updated["row"]["decision"] == "Gate moved."


def test_propose_gets_a_proposal_id_and_decide_resolves_it(tmp_path: Path) -> None:
    root = tmp_path / "notebook"
    load_project(root).ensure(write_config=True)
    assert main(["propose", "--root", str(root), "--subject", "node:disease",
                 "--instruction", "Add a station-level signal."]) == 0
    path = root / "notebook" / "records" / "proposals" / "P-0001.json"
    assert path.is_file()
    assert main(["decide", "--root", str(root), "--id", "P-0001", "--accept"]) == 0
    row = json.loads(path.read_text(encoding="utf-8"))
    assert row["state"] == "accepted"
