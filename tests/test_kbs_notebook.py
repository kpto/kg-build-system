from __future__ import annotations

import json
import sys
import threading

from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

import pytest

from kg_build_system.kgkit import (
    designs,
    evaluations,
    events,
    findings,
    ledger,
    project_commands,
    relations,
    revisions,
)
from kg_build_system.kgkit.cli import main
from kg_build_system.kgkit.config import DEFAULT_CONFIG, load_project, write_config_file
from kg_build_system.kgkit.console import _asset, make_handler
from kg_build_system.kgkit.snapshot import import_snapshot


def _project(root: Path):
    (root / "build").mkdir(parents=True)
    (root / "kgkit" / "eval").mkdir(parents=True)
    (root / "build" / "workflow_plan.json").write_text(
        json.dumps(
            {
                "format": "kg-viewer-snapshot",
                "version": 1,
                "name": "demo",
                "title": "Demo compilation",
                "workflow": {
                    "components": [],
                    "steps": [],
                    "connections": [],
                    "provenance": {},
                },
            }
        ),
        encoding="utf-8",
    )
    (root / "kgkit" / "eval" / "quick.json").write_text(
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
    project = load_project(root).ensure(write_config=True)
    write_config_file(project)
    return load_project(root)


def _facts(root: Path, payload: dict) -> None:
    script = root / "facts.py"
    script.write_text(
        "import json\n" + f"print(json.dumps({payload!r}))\n", encoding="utf-8"
    )
    project = load_project(root)
    project.config["commands"] = {"revision_facts": f"{sys.executable} {script}"}
    write_config_file(project)


def _adopted(root: Path, title: str = "First slice") -> dict:
    project = load_project(root)
    design = designs.propose(project, title=title, summary="The first change.")
    designs.set_state(project, design["id"], "adopted")
    return designs.read_design(load_project(root), design["id"]) or {}


def _finding(root: Path, observation: str = "A finding.") -> dict:
    return findings.add(
        load_project(root),
        layer="design",
        observation=observation,
        evidence="kgkit/eval/quick.json",
        decision="Change the model.",
        metric="audit passes",
    )


def _escalate(root: Path, designs_value: list[dict], revision: str = "abc123") -> None:
    _facts(
        root,
        {
            "ok": True,
            "revision": revision,
            "manifest": "m1",
            "counts": {"nodes": 3, "edges": 2},
            "designs": designs_value,
        },
    )


def test_init_creates_the_notebook_without_proposals(tmp_path: Path) -> None:
    project = load_project(tmp_path).ensure(write_config=True)
    assert (tmp_path / "kgkit" / "config.json").is_file()
    for name in ("revisions", "events", "findings", "designs", "evaluations"):
        assert (tmp_path / "kgkit" / "records" / name).is_dir()
    assert "proposals" not in DEFAULT_CONFIG
    assert not (tmp_path / ".kgkit").exists()
    assert not (tmp_path / "kgkit" / "records" / "relations.db").exists()


def test_finding_is_added_once_and_appends_one_event(tmp_path: Path) -> None:
    _project(tmp_path)
    finding = _finding(tmp_path)
    assert finding["id"] == "F-0001"
    assert finding["last_event"] == "evt-0001"
    chain = events.read_events(load_project(tmp_path))
    assert [event["kind"] for event in chain] == ["finding_added"]
    assert chain[0]["refs"] == [{"kind": "finding", "id": "F-0001"}]
    assert not hasattr(ledger, "update_state")
    assert ledger.validate_ledger(findings.findings_dir(load_project(tmp_path)))["rows"] == 1


def test_design_links_are_stored_once_and_reverse_is_derived(tmp_path: Path) -> None:
    _project(tmp_path)
    older = designs.propose(load_project(tmp_path), title="Older design")
    designs.set_state(load_project(tmp_path), older["id"], "adopted")
    newer = designs.propose(load_project(tmp_path), title="Newer design")
    designs.link(load_project(tmp_path), newer["id"], older["id"], "supersedes")
    designs.set_state(load_project(tmp_path), older["id"], "superseded", by=newer["id"])

    project = load_project(tmp_path)
    stored = designs.read_design(project, newer["id"]) or {}
    assert stored["design_links"] == [{"design_id": older["id"], "role": "supersedes"}]
    rows = {row["id"]: row for row in relations._change_design_rows(project, [])}
    assert rows[older["id"]]["superseded_by"] == [newer["id"]]
    assert rows[newer["id"]]["superseded_by"] == []


def test_superseding_requires_an_explicit_link(tmp_path: Path) -> None:
    _project(tmp_path)
    older = designs.propose(load_project(tmp_path), title="Older design")
    newer = designs.propose(load_project(tmp_path), title="Newer design")
    with pytest.raises(ValueError, match="does not link"):
        designs.set_state(load_project(tmp_path), older["id"], "superseded", by=newer["id"])


def test_revision_refuses_while_a_design_is_proposed(tmp_path: Path) -> None:
    _project(tmp_path)
    adopted = _adopted(tmp_path)
    designs.propose(load_project(tmp_path), title="Open question")
    _escalate(tmp_path, [{"design_id": adopted["id"], "role": "adopted"}])
    result = revisions.record_revision(load_project(tmp_path))
    assert result["ok"] is False
    assert "CD-0002 is proposed" in result["error"]
    assert not list((tmp_path / "kgkit" / "records" / "revisions").glob("*.json"))


def test_revision_refuses_without_an_adopted_design(tmp_path: Path) -> None:
    _project(tmp_path)
    design = designs.propose(load_project(tmp_path), title="Abandoned start")
    designs.set_state(load_project(tmp_path), design["id"], "abandoned")
    _escalate(tmp_path, [{"design_id": design["id"], "role": "abandoned"}])
    result = revisions.record_revision(load_project(tmp_path))
    assert result["ok"] is False
    assert "no adopted design" in result["error"]


def test_revision_links_every_resolved_design_and_creates_its_snapshot(
    tmp_path: Path,
) -> None:
    _project(tmp_path)
    finding = _finding(tmp_path)
    first = designs.propose(
        load_project(tmp_path), title="Site model", summary="The record model.", findings=[finding["id"]]
    )
    designs.set_state(load_project(tmp_path), first["id"], "adopted")
    second = designs.propose(load_project(tmp_path), title="Station signals")
    designs.set_state(load_project(tmp_path), second["id"], "adopted")
    older = designs.propose(load_project(tmp_path), title="First attempt")
    designs.link(load_project(tmp_path), first["id"], older["id"], "supersedes")
    designs.set_state(load_project(tmp_path), older["id"], "superseded", by=first["id"])
    dropped = designs.propose(load_project(tmp_path), title="Rejected idea")
    designs.set_state(load_project(tmp_path), dropped["id"], "abandoned")
    evaluation = evaluations.add(load_project(tmp_path), report="kgkit/eval/quick.json")
    _escalate(
        tmp_path,
        [
            {"design_id": first["id"], "role": "adopted"},
            {"design_id": second["id"], "role": "adopted"},
            {"design_id": older["id"], "role": "superseded"},
            {"design_id": dropped["id"], "role": "abandoned"},
        ],
    )
    result = revisions.record_revision(load_project(tmp_path), message="Site condition slice")
    assert result["ok"] is True, result
    record = json.loads(Path(result["path"]).read_text(encoding="utf-8"))
    assert record["designs"] == [
        {"design_id": first["id"], "role": "adopted"},
        {"design_id": second["id"], "role": "adopted"},
        {"design_id": older["id"], "role": "superseded"},
        {"design_id": dropped["id"], "role": "abandoned"},
    ]
    assert record["evaluations"] == [evaluation["id"]]
    assert record["evaluation"]["status"] == "passed"
    snapshot = Path(load_project(tmp_path).snapshots_dir) / record["snapshot"]["file"]
    assert snapshot.is_file()
    assert record["snapshot"]["source"].endswith("workflow_plan.json")

    payload = relations.graph(load_project(tmp_path))
    revision = next(row for row in payload["objects"] if row["id"] == "KG-abc123")
    assert revision["view_file"] == record["snapshot"]["file"]
    assert revision["event_id"] == record["event"] == Path(result["event"]).stem
    roles = {(link["id"], link["role"]) for link in revision["links"]}
    assert (first["id"], "adopted") in roles
    assert (older["id"], "superseded") in roles
    kinds = [event["type"] for event in payload["timeline"]]
    assert "revision_added" in kinds
    assert "snapshot_captured" not in kinds
    event = next(item for item in payload["timeline"] if item["type"] == "revision_added")
    refs = {(ref["kind"], ref["id"]) for ref in event["refs"]}
    assert ("revision", "KG-abc123") in refs
    assert ("change_design", first["id"]) in refs
    assert ("change_design", second["id"]) in refs
    assert ("evaluation", evaluation["id"]) in refs

    views = payload["views"]
    assert views[0]["kind"] == "current"
    assert views[0]["file"] == "current.snapshot.json"
    assert any(view.get("revision") == "KG-abc123" for view in views)


def test_revision_refuses_a_role_that_disagrees_with_the_notebook(
    tmp_path: Path,
) -> None:
    _project(tmp_path)
    design = _adopted(tmp_path)
    _escalate(tmp_path, [{"design_id": design["id"], "role": "superseded"}])
    result = revisions.record_revision(load_project(tmp_path))
    assert result["ok"] is False
    assert "names it superseded" in result["error"]


def test_a_linked_design_is_immutable(tmp_path: Path) -> None:
    _project(tmp_path)
    design = _adopted(tmp_path)
    _escalate(tmp_path, [{"design_id": design["id"], "role": "adopted"}])
    assert revisions.record_revision(load_project(tmp_path))["ok"] is True
    with pytest.raises(ValueError, match="linked to KG-abc123"):
        designs.set_state(load_project(tmp_path), design["id"], "abandoned")


def test_snapshot_import_keeps_the_current_compilation_and_no_snapshot_event(
    tmp_path: Path,
) -> None:
    _project(tmp_path)
    project = load_project(tmp_path)
    result = import_snapshot(project)
    assert Path(result["snapshot"]).is_file()
    assert Path(result["snapshot_history"]).is_file()
    assert Path(result["snapshot_history"]).name.endswith(".snapshot.json")
    payload = relations.graph(project)
    assert not [row for row in payload["objects"] if row["kind"] == "snapshot"]
    assert payload["views"][0]["file"] == "current.snapshot.json"


def test_console_assets_are_present_and_scoped() -> None:
    for name in ("index.html", "style.css", "app.js", "iteration-graph.js"):
        assert _asset(name) is not None
    assert _asset("../config.py") is None
    assert _asset("/etc/passwd") is None


def test_console_serves_the_current_view_and_a_revision_snapshot(tmp_path: Path) -> None:
    _project(tmp_path)
    design = _adopted(tmp_path)
    _escalate(tmp_path, [{"design_id": design["id"], "role": "adopted"}])
    assert revisions.record_revision(load_project(tmp_path))["ok"] is True
    project = load_project(tmp_path)
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        make_handler(project, "http://127.0.0.1:3000/?embed=1"),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        with urlopen(f"{base}/api/current-view") as response:
            current = json.load(response)
        assert current["format"] == "kg-viewer-snapshot"
        with urlopen(f"{base}/api/config") as response:
            config = json.load(response)
        assert config["viewerUrl"].endswith("embed=1")
        with urlopen(f"{base}/api/revision-view?revision=KG-abc123") as response:
            archived = json.load(response)
        assert archived["name"] == current["name"]
        with urlopen(f"{base}/api/relations") as response:
            payload = json.load(response)
        assert payload["views"][0]["kind"] == "current"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_sql_query_is_gone() -> None:
    assert not hasattr(relations, "query")


def test_configured_project_commands_are_parsed(tmp_path: Path) -> None:
    _project(tmp_path)
    script = tmp_path / "status.py"
    script.write_text(
        "import json\n"
        "print(json.dumps({'ok': True, 'revision': 'rev1', 'manifest': 'm1', "
        "'counts': {'nodes': 3}, 'blueprint': {'nodes': 3}}))\n",
        encoding="utf-8",
    )
    project = load_project(tmp_path)
    project.config["commands"] = {"status": f"{sys.executable} {script}"}
    write_config_file(project)
    result = project_commands.run(load_project(tmp_path), "status")
    assert result["ok"] is True
    assert result["blueprint"]["nodes"] == 3


def test_cli_designs_and_revisions_use_the_same_gate(tmp_path: Path, capsys) -> None:
    _project(tmp_path)
    assert main(["design", "new", "--root", str(tmp_path), "--title", "First slice"]) == 0
    assert main(["design", "adopt", "--root", str(tmp_path), "--id", "CD-0001"]) == 0
    _escalate(tmp_path, [{"design_id": "CD-0001", "role": "adopted"}])
    assert main(["revisions", "record", "--root", str(tmp_path), "--message", "Slice"]) == 0
    assert (tmp_path / "kgkit" / "records" / "revisions" / "abc123.json").is_file()
    assert main(["revisions", "list", "--root", str(tmp_path), "--json"]) == 0
    assert "abc123" in capsys.readouterr().out
