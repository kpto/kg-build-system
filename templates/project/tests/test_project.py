"""The project compiles, and the conformance fixture builds end to end."""

from __future__ import annotations

import json

import pytest

from kg_build_system import execute

from project.build import compile_project, create_project_blueprint


def _fixture_present() -> bool:
    declaration = create_project_blueprint().graph_declaration
    return declaration is not None and declaration.name == "fixture"


def test_the_project_compiles() -> None:
    assert create_project_blueprint() is not None
    assert compile_project() is not None


def test_the_conformance_fixture_builds(tmp_path) -> None:
    if not _fixture_present():
        pytest.skip("the conformance fixture has been replaced")

    report = execute(compile_project(), output_directory=tmp_path)

    assert report.published_artifacts
    records = [
        json.loads(line)
        for line in (tmp_path / "graph.jsonl").read_text().splitlines()
    ]
    assert len([row for row in records if row["kind"] == "node"]) == 5
    assert len([row for row in records if row["kind"] == "edge"]) == 3
