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
from kg_build_system.declaration.blueprint import create_blueprint
from kg_build_system.declaration.foundations.expressions.service.internal import (
    ArgumentSpec,
    OperationSpec,
    expression_dto,
    is_unit,
)
from kg_build_system.distribution import (
    CoreModule,
    FileModule,
    FileModuleConfiguration,
    register_module,
)
from kg_build_system.kernel import INT
from kg_build_system.pipeline.compile import compile_blueprint
from kg_build_system.pipeline.compile.service.internal.instruction.duckdb import (
    DuckDbInstructionEmitter,
    DuckDbSqlEmitter,
)


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


class CustomOperationTests(unittest.TestCase):
    def test_a_custom_operation_reaches_the_emitter_without_a_dispatcher_edit(
        self,
    ) -> None:
        emitter = DuckDbInstructionEmitter().with_operators(DoubleEmitter())
        expression = expression_dto(DOUBLE.apply(1).model)

        self.assertEqual(emitter.expression_sql(expression), "1 * 2")

    def test_an_unregistered_operation_is_refused(self) -> None:
        expression = expression_dto(DOUBLE.apply(1).model)

        with self.assertRaisesRegex(ValueError, "does not support"):
            DuckDbInstructionEmitter().expression_sql(expression)

    def test_compile_uses_the_supplied_emitter_for_core_sql(self) -> None:
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

            contract = compile_blueprint(
                blueprint,
                modules=(
                    register_module(CoreModule),
                    register_module(
                        FileModule, FileModuleConfiguration("out.jsonl"),
                    ),
                ),
                engine=emitter,
            )

        sql = "\n".join(
            inner["sql"]
            for contribution in contract.contributions
            for step in contribution.steps
            if isinstance(step.instruction.payload, dict)
            and isinstance(
                (inner := step.instruction.payload.get("instruction")), dict,
            )
            and isinstance((inner := inner.get("payload")), dict)
            and isinstance(inner.get("sql"), str)
        )
        self.assertIn("* 2", sql)


if __name__ == "__main__":
    unittest.main()
