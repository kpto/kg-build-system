"""Composition of DuckDB expression emitters, one module per operation.

Each operation module exports its emitter. Composition happens once, at import,
and rejects a duplicate operator name so two implementations cannot silently
shadow one another.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING

from .add import ADD
from .after_separator import AfterSeparator
from .and_ import AND
from .append import Append
from .array_at import ArrayAt
from .array_slice import ArraySlice
from .before_separator import BeforeSeparator
from .coalesce import Coalesce
from .concat import Concat
from .distinct import Distinct
from .drop_if import DropIf
from .drop_null import DropNull
from .drop_null_items import DropNullItems
from .equals import EQUALS
from .expand import Expand
from .join import ArrayJoin
from .not_ import Not
from .or_ import OR
from .replace import Replace
from .sort import Sort
from .struct_field import StructField
from .subtract import SUBTRACT
from .to_string import ToString
from .transform_items import TransformItems

if TYPE_CHECKING:
    from ..protocols import ExpressionEmitter

OPERATORS = (
    ADD,
    SUBTRACT,
    EQUALS,
    AND,
    OR,
    Not(),
    Concat(),
    Append(),
    Replace(),
    ToString(),
    BeforeSeparator(),
    AfterSeparator(),
    ArrayAt(),
    ArraySlice(),
    TransformItems(),
    DropNullItems(),
    Sort(),
    Distinct(),
    ArrayJoin(),
    StructField(),
    Expand(),
    DropNull(),
    DropIf(),
    Coalesce(),
)


def compose_operators(
    *groups: Iterable["ExpressionEmitter"],
) -> Mapping[str, "ExpressionEmitter"]:
    registry: dict[str, ExpressionEmitter] = {}
    for group in groups:
        for emitter in group:
            if not emitter.operator:
                raise ValueError("expression emitters require a non-empty operator")
            if emitter.operator in registry:
                raise ValueError(
                    f"duplicate expression operator {emitter.operator!r}"
                )
            registry[emitter.operator] = emitter
    return registry


DEFAULT_OPERATORS = compose_operators(OPERATORS)

__all__ = ["DEFAULT_OPERATORS", "OPERATORS", "compose_operators"]
