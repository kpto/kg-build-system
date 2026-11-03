"""Value helpers over the logical type vocabulary.

Private implementation behind ``kernel.internal.types.canonical_value_text``.
Not an import surface for another package.
"""
from __future__ import annotations

import datetime
import uuid

from ...public.types import (
    Date, Time, Timestamp, Uuid,
)


def canonical_value_text(value: Date | Time | Timestamp | Uuid) -> str:
    """Return the canonical text form of a date, time, timestamp or UUID."""
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    raise TypeError(f"{type(value).__qualname__} has no canonical text form")


__all__ = ["canonical_value_text"]
