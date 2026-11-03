from __future__ import annotations

import unittest

from sqlglot import exp

from kg_build_system.declaration.foundations.expressions.service.internal import (
    ArgumentSpec,
    OperationSpec,
    expression_dto,
    is_unit,
)
from kg_build_system.kernel import INT
from kg_build_system.pipeline.compile.service._private.instructions.duckdb import (
    DuckDbInstructionEmitter,
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


if __name__ == "__main__":
    unittest.main()
