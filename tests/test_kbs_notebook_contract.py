from __future__ import annotations

import gzip
import json
from pathlib import Path
from types import SimpleNamespace

from kg_build_system.kgkit.contract import audit_graph, document_revision, validate_blueprint
from kg_build_system.kgkit.snapshot import write_snapshot_document


def _meaning(value: str = "stated") -> SimpleNamespace:
    return SimpleNamespace(omitted=None, purpose=value)


def _dropped(blueprint: dict) -> dict:
    errors = list(blueprint["errors"])
    assert blueprint["ok"] is False
    return {"errors": errors, "counts": blueprint["counts"]}


def test_document_revision_is_stable_and_short() -> None:
    first = document_revision({"b": 2, "a": 1})
    second = document_revision({"a": 1, "b": 2})
    assert first == second
    assert len(first) == 16
    assert first != document_revision({"a": 1, "b": 3})


def test_validate_blueprint_accepts_a_complete_blueprint() -> None:
    annotation = SimpleNamespace(id="class")
    node = SimpleNamespace(name="protein", meaning=_meaning(), properties=[], annotations=[annotation])
    edge = SimpleNamespace(
        name="associated_with",
        meaning=_meaning(),
        properties=[],
        annotations=[SimpleNamespace(id="predicate")],
    )
    asset = SimpleNamespace(name="targets", meaning=_meaning())
    relation = SimpleNamespace(
        name="target_disease",
        asset=SimpleNamespace(symbol=SimpleNamespace(key=SimpleNamespace(segments=("targets",)))),
    )
    blueprint = SimpleNamespace(
        graph_declaration=SimpleNamespace(meaning=_meaning()),
        graph=SimpleNamespace(nodes=[node], edges=[edge]),
        assets=SimpleNamespace(assets=[asset]),
        bindings=[SimpleNamespace(name="binding:edge:0", meaning=_meaning())],
        data=SimpleNamespace(source_relations=[relation], derived_relations=[]),
    )
    result = validate_blueprint(blueprint)
    assert result["ok"] is True
    assert result["errors"] == []
    assert result["counts"] == {
        "nodes": 1,
        "edges": 1,
        "properties": 0,
        "assets": 1,
        "bindings": 1,
    }


def test_validate_blueprint_reports_each_missing_semantic() -> None:
    node = SimpleNamespace(name="protein", meaning=None, properties=[], annotations=[])
    edge = SimpleNamespace(name="binds", meaning=None, properties=[], annotations=[])
    asset = SimpleNamespace(name="targets", meaning=None)
    binding = SimpleNamespace(name=None, meaning=None)
    relation = SimpleNamespace(
        name="target_disease",
        asset=SimpleNamespace(symbol=SimpleNamespace(key=SimpleNamespace(segments=("missing",)))),
    )
    blueprint = SimpleNamespace(
        graph_declaration=None,
        graph=SimpleNamespace(nodes=[node], edges=[edge]),
        assets=SimpleNamespace(assets=[asset]),
        bindings=[binding],
        data=SimpleNamespace(source_relations=[relation], derived_relations=[]),
    )
    result = _dropped(validate_blueprint(blueprint))
    joined = "\n".join(result["errors"])
    assert "no Graph" in joined
    assert "node protein has no meaning" in joined
    assert "node protein has no biolink class annotation" in joined
    assert "edge binds has no biolink predicate annotation" in joined
    assert "asset targets has no meaning" in joined
    assert "binding ? has no meaning" in joined
    assert "names unknown asset missing" in joined


def test_audit_graph_reports_integrity_and_coverage(tmp_path: Path) -> None:
    graph = tmp_path / "graph.jsonl"
    graph.write_text(
        "\n".join(
            json.dumps(record)
            for record in [
                {"kind": "node", "build_key": "A", "type": "protein"},
                {"kind": "node", "build_key": "A", "type": "protein"},
                {"kind": "node", "build_key": "", "type": "protein"},
                {"kind": "edge", "build_key": "E1", "source_build_key": "A", "target_build_key": "B"},
                {"kind": "edge", "build_key": "E2", "source_build_key": "A", "target_build_key": "A"},
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "evidence.jsonl").write_text(
        json.dumps({"build_key": "A"}) + "\n", encoding="utf-8"
    )
    result = audit_graph(tmp_path)
    assert result["status"] == "failed"
    assert result["nodes"] == 1
    assert result["edges"] == 2
    assert result["duplicates"] == 1
    assert result["null_keys"] == 1
    assert result["dangling_endpoints"] == 1
    assert result["evidence_coverage"] == round(1 / 3, 4)


def test_audit_graph_skips_without_a_graph(tmp_path: Path) -> None:
    assert audit_graph(tmp_path) == {"status": "skipped", "reason": f"no graph at {tmp_path / 'graph.jsonl'}"}


def test_write_snapshot_document_writes_current_gzip_and_archive(tmp_path: Path) -> None:
    result = write_snapshot_document(
        tmp_path,
        name="project-1",
        title="Project one",
        workflow={"steps": [], "provenance": {}},
        revision="abc123",
        stem="project",
    )
    current = tmp_path / "project.snapshot.json"
    assert Path(result["snapshot"]) == current
    document = json.loads(current.read_text(encoding="utf-8"))
    assert document["format"] == "kg-viewer-snapshot"
    assert document["version"] == 1
    assert document["name"] == "project-1"
    assert document["workflow"] == {"steps": [], "provenance": {}}
    assert gzip.decompress((tmp_path / "project.snapshot.json.gz").read_bytes()) == current.read_bytes()
    archive = Path(result["snapshot_history"])
    assert archive.parent == tmp_path
    assert archive.name.startswith("project-abc123-")
    assert archive.read_bytes() == current.read_bytes()
    assert result["revision"] == "abc123"
