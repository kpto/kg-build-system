from __future__ import annotations

import unittest

from sqlglot import exp

from kg_build_system.engines.interfaces import (
    DEFAULT_LOWERING,
    lower_expression_sql,
)
from kg_build_system.expressions.ir import LiteralExpressionIR, OperationExpressionIR
from kg_build_system.types.interfaces import INT


class Double:
    """A custom operator added without editing the lowering dispatcher."""

    operator = "double"

    def lower(self, expression, operands, context):
        return exp.Mul(
            this=operands[0].sql(),
            expression=exp.Literal.number(2),
        )


def _double_literal(value: int) -> OperationExpressionIR:
    return OperationExpressionIR(
        logical_type=INT,
        operator="double",
        arguments=(LiteralExpressionIR(value=value, logical_type=INT),),
    )


class OperatorExtensionTests(unittest.TestCase):
    def test_a_custom_operator_is_rendered_by_its_own_registration(self) -> None:
        lowering = DEFAULT_LOWERING.with_operators(Double())
        self.assertEqual(
            lower_expression_sql(_double_literal(3), lowering=lowering),
            "3 * 2",
        )

    def test_the_default_registry_is_not_modified(self) -> None:
        DEFAULT_LOWERING.with_operators(Double())
        with self.assertRaisesRegex(ValueError, "does not support expression operator"):
            lower_expression_sql(_double_literal(3))

    def test_a_duplicate_operator_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate expression operator"):
            DEFAULT_LOWERING.with_operators(Double(), Double())


if __name__ == "__main__":
    unittest.main()
