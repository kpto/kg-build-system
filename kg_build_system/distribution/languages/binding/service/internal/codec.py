"""Canonical document codec for the binding blueprint DTO."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ...model.internal.dto.blueprint_dto import BindingDTO


def binding_to_document(binding: BindingDTO) -> dict[str, Any]:
    """Encode one binding DTO as its canonical JSON-compatible object.

    Example:
        ```python
        from kg_build_system.distribution.languages.binding.model.internal.dto import (
            NodeBindingDTO, binding_to_document,
        )
        from kg_build_system.distribution.model.public.refs import NodeRef
        from kg_build_system.kernel import Key
        from kg_build_system.distribution.languages.expressions.model.internal import (
            LiteralExpressionDTO,
        )
        from kg_build_system.kernel.model.internal.types.dto import UnitTypeDTO

        key = LiteralExpressionDTO(logical_type=UnitTypeDTO("str"), value="site::")
        document = binding_to_document(NodeBindingDTO(NodeRef("topology", Key(("site",))), key))
        assert document["kind"] == "node"
        ```
    """
    from .._private.codec import binding_to_document as encode

    return encode(binding)


def binding_from_document(document: Mapping[str, Any]) -> BindingDTO:
    """Decode one binding DTO from its canonical JSON-compatible object.

    Example:
        ```python
        from kg_build_system.distribution.languages.binding.model.internal.dto import (
            binding_from_document,
        )

        document = {
            "kind": "node",
            "node": ["topology", "node", "site"],
            "identity": {
                "kind": "literal",
                "value": "site::",
                "logical_type": {"kind": "unit", "name": "str"},
            },
        }
        binding = binding_from_document(document)
        ```
    """
    from .._private.codec import binding_from_document as decode

    return decode(document)


def bindings_to_document(bindings: Sequence[BindingDTO]) -> list[dict[str, Any]]:
    """Encode a sequence of binding DTOs as canonical objects.

    Example:
        ```python
        from kg_build_system.distribution.languages.binding.model.internal.dto import (
            bindings_to_document,
        )

        assert bindings_to_document(()) == []
        ```
    """
    from .._private.codec import bindings_to_document as encode

    return encode(bindings)


def bindings_from_document(
    document: Sequence[Mapping[str, Any]],
) -> tuple[BindingDTO, ...]:
    """Decode a sequence of canonical binding objects.

    Example:
        ```python
        from kg_build_system.distribution.languages.binding.model.internal.dto import (
            bindings_from_document,
        )

        assert bindings_from_document(()) == ()
        ```
    """
    from .._private.codec import bindings_from_document as decode

    return decode(document)


__all__ = [
    "binding_from_document", "binding_to_document", "bindings_from_document",
    "bindings_to_document",
]
