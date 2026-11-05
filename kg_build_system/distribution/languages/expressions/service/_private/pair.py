"""Typed paired-record shapes for ``zip`` and their public extraction members."""
from __future__ import annotations

import json
from hashlib import sha256
from typing import Any, Final

from kg_build_system.kernel.model.public.types import LogicalType, StructType
from kg_build_system.kernel.service.internal.types import type_to_document
from ...model.internal.model import SelectedMember
from ...model.public.pair import Pair

PAIR_MODULE: Final = Pair.__module__


class _PairMember:
    """One ``left`` or ``right`` member of a generated pair record."""

    __slots__ = ("_declaration", "_name", "_logical_type")

    def __init__(
        self, name: str, logical_type: LogicalType, declaration: StructType,
    ) -> None:
        self._name = name
        self._logical_type = logical_type
        self._declaration = declaration

    def __get__(self, instance: Any, owner: type[Any] | None = None) -> Any:
        from ...model.public.selection import Selection

        return Selection(member=SelectedMember(
            self._name, self._logical_type, self._declaration,
        ))


#: Generated pair declarations by qualified name, so a round trip in this
#: process can resolve a pair type that a document names.
_PAIR_CLASSES: dict[str, type[Pair[Any, Any]]] = {}


def _digest(left: LogicalType, right: LogicalType) -> str:
    encoded = json.dumps(
        [type_to_document(type_to_dto(left)), type_to_document(type_to_dto(right))],
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()[:24]


def type_to_dto(logical_type: LogicalType) -> Any:
    """Convert one canonical type to its DTO without importing the kernel service."""
    from kg_build_system.kernel.service.internal.types import type_to_dto as convert

    return convert(logical_type)


def pair_type(left: LogicalType, right: LogicalType) -> StructType:
    """Return the declared paired-record type for two item types.

    The generated record is a ``Struct`` subclass with public ``left`` and
    ``right`` members, registered in the pair module so source generation and
    extraction can resolve it by module and qualified name.

    Example:
        ```python
        from kg_build_system.distribution.languages.expressions.service.internal import (
            pair_type,
        )
        from kg_build_system.kernel.model.public.types import INT, STR

        assert pair_type(STR, INT).qualname.startswith("Pair_")
        ```
    """
    qualname = f"Pair_{_digest(left, right)}"
    existing = _PAIR_CLASSES.get(qualname)
    if existing is not None:
        return StructType(PAIR_MODULE, qualname)
    declaration = StructType(PAIR_MODULE, qualname)
    namespace: dict[str, Any] = {
        "__module__": PAIR_MODULE,
        "__qualname__": qualname,
        "left": _PairMember("left", left, declaration),
        "right": _PairMember("right", right, declaration),
    }
    cls = type(qualname, (Pair,), namespace)
    _PAIR_CLASSES[qualname] = cls
    import sys

    module = sys.modules.get(PAIR_MODULE)
    if module is not None:
        setattr(module, qualname, cls)
    return declaration


def pair_declaration(qualname: str) -> type[Pair[Any, Any]] | None:
    """Return a generated pair declaration by name, when this process made one."""
    return _PAIR_CLASSES.get(qualname)


__all__ = ["PAIR_MODULE", "pair_declaration", "pair_type"]
