"""Canonical document codec for expression DTOs."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ....model.internal.dto.blueprint_dto import ExpressionDTO


def expression_to_document(expression: ExpressionDTO) -> dict[str, Any]:
    """Encode one expression DTO as its canonical JSON-compatible document.

    Example:
        ```python
        from kg_build_system.declaration.foundations.expressions.model.internal import (
            LiteralExpressionDTO,
        )
        from kg_build_system.declaration.foundations.expressions.service.internal import (
            expression_to_document,
        )
        from kg_build_system.kernel.model.internal.types.dto import UnitTypeDTO

        node = LiteralExpressionDTO(logical_type=UnitTypeDTO("int"), value=1)
        assert expression_to_document(node)["kind"] == "literal"
        ```
    """
    from ..._private.dto_codec import expression_to_document as encode

    return encode(expression)


def expression_from_document(value: Mapping[str, Any]) -> ExpressionDTO:
    """Decode one expression DTO from its canonical document.

    Example:
        ```python
        from kg_build_system.declaration.foundations.expressions.service.internal import (
            expression_from_document,
        )

        node = expression_from_document({
            "kind": "literal",
            "value": 1,
            "logical_type": {"kind": "unit", "name": "int"},
        })
        assert node.logical_type.name == "int"
        ```
    """
    from ..._private.dto_codec import expression_from_document as decode

    return decode(value)


__all__ = ["expression_from_document", "expression_to_document"]
