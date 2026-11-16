"""Meaning authoring model."""
from __future__ import annotations

from .units import (
    Claim, Limitation, Meaning, Omitted, Purpose, is_omitted,
    require_declaration_meaning,
)

__all__ = [
    "Claim", "Limitation", "Meaning", "Omitted", "Purpose", "is_omitted",
    "require_declaration_meaning",
]
