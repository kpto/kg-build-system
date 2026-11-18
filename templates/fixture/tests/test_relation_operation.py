"""The project's relation operation counts every fixture item."""

from __future__ import annotations

import json
from pathlib import Path

from kg_build_system import (
    Contract,
    Definition,
    DerivedRelation,
    DerivedRelationOptions,
    Limitation,
    Meaning,
    Node,
    NodeValues,
    Omitted,
    PropertySlot,
    Purpose,
    STR,
    compile,
    computed_field,
    create_blueprint,
    default_toolchain,
    execute,
    node_binding,
    property,
    value_expression,
)
from kg_build_system.distribution.interpreter import GraphBlueprint
from kg_build_system.distribution import (
    DuckDbInstructionEmitter,
    DuckDbSqlEmitter,
    FileConfiguration,
    FilePlanner,
)

from kg_build_system.kernel import Toolchain

from project.modules.count_rows import CountRowsEmitter, count_rows
from project.relation.source.items import Items


class CountNode(Node):
    count: PropertySlot[int] = property(meaning=Omitted)


counted = count_rows(Items.row_source())


class ItemCount(DerivedRelation(counted)):
    options = DerivedRelationOptions(
        name="item_count",
        contract=Contract(
            definition=Definition(
                grain="one row in total",
                identity=("count",),
            ),
            meaning=Meaning(
                purpose=Purpose(
                    "Count the fixture items in one row.",
                    limitations=(
                        Limitation(
                            "A conformance fixture; replace it with the project's count."
                        ),
                    ),
                ),
            ),
        ),
    )

    count = computed_field(
        counted.shape.count,
        meaning=Omitted,
    )


item_count_binding = node_binding(
    target=CountNode,
    rows=ItemCount.row_source(),
    bind=lambda row: NodeValues(
        build_key=value_expression("all-items"),
        properties=CountNode(count=row.count),
    ),
    meaning=Meaning(
        purpose=Purpose("Fulfil the item-count record from the global count."),
    ),
)


def _project() -> tuple[GraphBlueprint, Toolchain[GraphBlueprint]]:
    blueprint = create_blueprint(bindings=(item_count_binding,))
    engine = DuckDbSqlEmitter(
        instruction_emitter=(
            DuckDbInstructionEmitter().with_row_sources(CountRowsEmitter())
        ),
    )
    planners = (FilePlanner(FileConfiguration("graph.jsonl")),)
    return blueprint, default_toolchain(engine=engine, planners=planners)


def test_the_relation_operation_runs(tmp_path: Path) -> None:
    blueprint, toolchain = _project()
    plan = compile(blueprint=blueprint, toolchain=toolchain)
    execute(plan, output_directory=tmp_path)

    records = [
        json.loads(line)
        for line in (tmp_path / "graph.jsonl").read_text().splitlines()
    ]
    counts = [
        record for record in records
        if record["kind"] == "node" and record["type"] == "count"
    ]

    assert len(counts) == 1
    assert counts[0]["count"] == 2
