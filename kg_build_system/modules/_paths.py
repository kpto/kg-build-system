"""Compatibility shim for the shared relative-path validator."""
from __future__ import annotations

from ._private._paths import validate_relative_path

__all__ = ["validate_relative_path"]
