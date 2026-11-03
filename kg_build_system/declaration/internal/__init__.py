"""Framework-internal values shared by declaration languages.

``SourceFragment`` is the value every language returns from ``render``;
``rendering`` contains the source forms shared by more than one language.
"""
from __future__ import annotations

from .source import SourceFragment

__all__ = ["SourceFragment"]
