"""Author-facing annotation names.

Annotations are author-declared dataclasses; this package has no separate
annotation constructor service.
"""
from __future__ import annotations

from .model import Annotation, EdgeLabel, NodeLabel

__all__ = ["Annotation", "EdgeLabel", "NodeLabel"]
