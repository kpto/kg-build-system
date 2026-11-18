"""The project's hello expression works in both authoring forms and in a build."""

from __future__ import annotations

import json
from pathlib import Path

from kg_build_system import STR, compile, create_blueprint, execute, value_expression

from project.expression.hello import hello
from project.manifest import blueprint as blueprint_declaration
from project.manifest import workflow as workflow_declaration


def _compile_project():
    blueprint = create_blueprint(
        namespace_path=blueprint_declaration.namespace_path,
        bindings=blueprint_declaration.bindings,
        languages=blueprint_declaration.languages,
    )
    return compile(blueprint=blueprint, toolchain=workflow_declaration.toolchain)


def test_both_authoring_forms_build_the_same_expression() -> None:
    value = value_expression("world")

    handle = hello(value)
    method = value.custom_op(hello)

    assert handle.logical_type == STR
    assert method.logical_type == STR


def test_the_hello_operation_runs_in_the_project_build(tmp_path: Path) -> None:
    execute(_compile_project(), output_directory=tmp_path)

    records = [
        json.loads(line)
        for line in (tmp_path / "graph.jsonl").read_text().splitlines()
    ]
    items = [
        record for record in records
        if record["kind"] == "node" and record["type"] == "item"
    ]

    assert items
    for item in items:
        assert item["greeting"] == f"hello {item['label']}"
