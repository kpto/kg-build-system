"""Portable annotations."""
from __future__ import annotations

from .labels import EdgeLabel, NodeLabel
from .models import Annotation

__all__ = ["Annotation", "EdgeLabel", "NodeLabel"]
