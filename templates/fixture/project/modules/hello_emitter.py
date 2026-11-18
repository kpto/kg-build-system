"""Emit the project's ``hello`` operation as DuckDB SQL."""

from __future__ import annotations

from collections.abc import Sequence

from sqlglot import exp

from kg_build_system.distribution.modules.duckdb import (
    EmissionContext,
    Operand,
)


class HelloEmitter:
    """Prefix a present string with ``hello ``."""

    operator = "hello"

    def emit(
        self,
        expression: object,
        operands: Sequence[Operand],
        context: EmissionContext,
    ):
        del expression, context
        if len(operands) != 1:
            raise ValueError("hello requires one argument")
        return exp.Anonymous(
            this="concat",
            expressions=[
                exp.Literal.string("hello "),
                operands[0].sql(),
            ],
        )


__all__ = ["HelloEmitter"]
