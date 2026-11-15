"""Semantics authoring model."""
from __future__ import annotations

from .units import (
    Claim, Limitation, Purpose, Semantics, require_declaration_semantics,
)

__all__ = [
    "Claim", "Limitation", "Purpose", "Semantics",
    "require_declaration_semantics",
]
