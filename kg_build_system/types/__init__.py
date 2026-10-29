"""Author-facing logical type vocabulary.

Authors write the canonical unit constants, the representative Python classes,
and the ``Array``/``Struct`` markers in declarations. Normalization, the
internal ``Nullable`` marker, codecs and validation are the framework interface
in :mod:`kg_build_system.types.interfaces`; the compilation IR is
:mod:`kg_build_system.types.ir`.
"""
from __future__ import annotations

from .models import (
    BOOL,
    DATE,
    FLOAT,
    INT,
    STR,
    TIME,
    TIMESTAMP,
    UUID,
    Array,
    ArrayType,
    CustomDataType,
    Date,
    NullableType,
    Shape,
    Struct,
    Time,
    Timestamp,
    Uuid,
)

__all__ = [
    "BOOL",
    "DATE",
    "FLOAT",
    "INT",
    "STR",
    "TIME",
    "TIMESTAMP",
    "UUID",
    "Array",
    "ArrayType",
    "CustomDataType",
    "Date",
    "NullableType",
    "Shape",
    "Struct",
    "Time",
    "Timestamp",
    "Uuid",
]
