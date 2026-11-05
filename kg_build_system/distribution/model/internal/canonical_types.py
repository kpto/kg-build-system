"""Canonical type names shared by the distribution model and its engines.

The kernel owns the canonical unit names. The distribution adds the two container
shapes it composes into SQL types: an ordered collection and a nested record.
"""
from __future__ import annotations

from typing import Final, Literal

from kg_build_system.kernel.model.public.types import UnitTypeName

#: The canonical name of the ordered-collection shape. Lowercase like a canonical
#: unit name; a container composes its SQL type from its item type.
ARRAY_CANONICAL: Final = "array"

#: The canonical name of the nested-record shape, composed from its members.
STRUCT_CANONICAL: Final = "struct"

type CanonicalTypeName = UnitTypeName | Literal["array", "struct"]

__all__ = ["ARRAY_CANONICAL", "CanonicalTypeName", "STRUCT_CANONICAL"]
