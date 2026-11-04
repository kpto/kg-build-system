"""Parse and encode role-typed blueprint references.

A reference document is ``[language, role, *key segments]``. The role token is
what makes the document self-describing: a topology document can name a node, an
edge or a property without the reader knowing which field it came from.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

ROLES = frozenset({
    "node", "edge", "relation", "field", "property", "source", "operation",
})


def role_types() -> dict[str, type[Any]]:
    """Return the role token to reference class map.

    Example:
        ```python
        from kg_build_system.distribution.model._private.refs import role_types

        assert role_types()["field"].role == "field"
        ```
    """
    from ..public.refs import (
        EdgeRef, FieldRef, NodeRef, OperationRef, PropertyRef, RelationRef,
        SourceRef,
    )

    return {
        "node": NodeRef,
        "edge": EdgeRef,
        "relation": RelationRef,
        "field": FieldRef,
        "property": PropertyRef,
        "source": SourceRef,
        "operation": OperationRef,
    }


def split_document(
    value: Sequence[str], *, role: str | None = None,
) -> tuple[str, tuple[str, ...]]:
    """Return the language and key segments of one reference document.

    Example:
        ```python
        from kg_build_system.distribution.model._private.refs import split_document

        assert split_document(["data", "field", "sites.site_name"]) == (
            "data", ("sites.site_name",),
        )
        ```
    """
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
        or not value
    ):
        raise ValueError("a reference document must be a non-empty array")
    language = value[0]
    if not isinstance(language, str) or not language:
        raise ValueError("a reference language must be a non-empty string")
    segments = tuple(value[1:])
    has_role = bool(segments) and segments[0] in ROLES
    if has_role:
        if role is not None and segments[0] != role:
            raise ValueError(
                f"reference role {segments[0]!r} is not {role!r}"
            )
        segments = segments[1:]
    if not segments:
        raise ValueError("a reference document requires a key")
    if any(not isinstance(item, str) or not item for item in segments):
        raise ValueError("reference key segments must be non-empty strings")
    return language, segments


def encode_ref(reference: Any) -> list[str]:
    """Encode one role-typed reference as its canonical document.

    Example:
        ```python
        from kg_build_system.distribution.model._private.refs import encode_ref

        document = encode_ref(reference)
        ```
    """
    return [
        reference.symbol.language,
        reference.role,
        *reference.symbol.key.segments,
    ]


def decode_ref(value: Any) -> Any:
    """Decode one reference document into its role type.

    Example:
        ```python
        from kg_build_system.distribution.model._private.refs import decode_ref

        reference = decode_ref(["data", "field", "sites.site_name"])
        ```
    """
    from kg_build_system.kernel import Key

    types = role_types()
    if not isinstance(value, Sequence) or isinstance(
        value, (str, bytes, bytearray),
    ):
        raise ValueError("a reference document must be an array")
    language, segments = split_document(value)
    role = value[1]
    if not isinstance(role, str) or role not in types:
        raise ValueError(f"unknown reference role {role!r}")
    return types[role](language, Key(segments))


__all__ = ["ROLES", "decode_ref", "encode_ref", "role_types", "split_document"]
