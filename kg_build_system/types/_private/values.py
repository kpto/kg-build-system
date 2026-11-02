"""Value helpers over the logical type vocabulary."""
from __future__ import annotations

import datetime
import uuid
from typing import TypeGuard

from ..public.models import Date, Time, Timestamp, UnitTypeName, Uuid


def canonical_value_text(value: Date | Time | Timestamp | Uuid) -> str:
    """Return the canonical text form of a date, time, timestamp or UUID."""
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    raise TypeError(f"{type(value).__qualname__} has no canonical text form")


def is_canonical_unit_name(name: str) -> TypeGuard[UnitTypeName]:
    """Return whether ``name`` is one of the canonical unit type names."""
    return name in {
        "bool", "int", "float", "str", "date", "time", "timestamp", "uuid",
    }


__all__ = ["canonical_value_text", "is_canonical_unit_name"]
