from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sqlglot import exp

from kg_build_system import (
    DataSourceConfig,
    Field,
    InputFormat,
    Node,
    NodeValues,
    PropertySlot,
    Table,
    TableOptions,
    bind_source,
    field,
    node_binding,
    property,
)
from kg_build_system.distribution.modules.duckdb import (
    DuckDbInstructionEmitter,
    DuckDbSqlEmitter,
)
from kg_build_system.distribution.interpreter import create_blueprint
from kg_build_system.distribution.languages.expressions.service.internal import (
    ArgumentSpec,
    OperationSpec,
    is_unit,
)
from kg_build_system.distribution.modules.core import core_planners
from kg_build_system.kernel import INT, PlanContext


DOUBLE = OperationSpec(
    name="double",
    arity=1,
    arguments=(ArgumentSpec(accepts=is_unit("int")),),
    result_type=INT,
)


class DoubleEmitter:
    operator = "double"

    def emit(self, expression, operands, context):
        return exp.Mul(
            this=operands[0].sql(), expression=exp.Literal.number(2),
        )


class DoubleRow(Table):
    options = TableOptions(name="double_row")
    id: Field[int] = field(name="id")


class DoubleNode(Node):
    value: PropertySlot[int] = property()


class CoreCustomEmitterTests(unittest.TestCase):
    def test_core_planner_uses_the_supplied_instruction_emitter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            csv = Path(directory) / "rows.csv"
            csv.write_text("id\n2\n", encoding="utf-8")
            binding = node_binding(
                target=DoubleNode,
                rows=DoubleRow.row_source(),
                bind=lambda row: NodeValues(
                    build_key=row.id,
                    properties=DoubleNode(value=DOUBLE.apply(row.id)),
                ),
            )
            source = bind_source(
                target=DoubleRow,
                config=DataSourceConfig(str(csv), format=InputFormat.CSV),
            )
            blueprint = create_blueprint(
                bindings=(binding,), sources=(source,),
            )
            emitter = DuckDbSqlEmitter(
                instruction_emitter=(
                    DuckDbInstructionEmitter().with_operators(DoubleEmitter())
                ),
            )

            context = PlanContext()
            steps = tuple(
                step
                for planner in core_planners(engine=emitter)
                for step in planner.plan(blueprint, context)
            )

        sql = "\n".join(
            step.instruction.payload["sql"]
            for step in steps
            if isinstance(step.instruction.payload, dict)
            and isinstance(step.instruction.payload.get("sql"), str)
        )
        self.assertIn("* 2", sql)


if __name__ == "__main__":
    unittest.main()
