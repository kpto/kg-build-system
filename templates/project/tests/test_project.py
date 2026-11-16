"""The project compiles, and the conformance fixture builds end to end."""

from __future__ import annotations

import json

import pytest

from kg_build_system import compile, create_blueprint, execute

from project.manifest import blueprint as blueprint_declaration
from project.manifest import workflow as workflow_declaration


def create_project_blueprint():
    """Build the blueprint the manifest declares; the CLI does this by default."""
    return create_blueprint(
        namespace_path=blueprint_declaration.namespace_path,
        bindings=blueprint_declaration.bindings,
        languages=blueprint_declaration.languages,
    )


def compile_project():
    """Compile the workflow the manifest declares."""
    return compile(
        blueprint=create_project_blueprint(),
        planners=workflow_declaration.planners,
        toolchain=workflow_declaration.toolchain,
    )


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
