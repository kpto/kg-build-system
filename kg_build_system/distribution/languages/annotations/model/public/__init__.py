"""The annotation authoring model."""
from __future__ import annotations

from .base import Annotation
from .labels import EdgeLabel, NodeLabel

__all__ = ["Annotation", "EdgeLabel", "NodeLabel"]
