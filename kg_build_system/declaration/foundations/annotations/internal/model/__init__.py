"""The annotation package has no separate in-memory model.

An annotation is either its author-declared dataclass or its portable
``AnnotationDTO``; the payload helpers in ``_private`` bridge the two.
"""
from __future__ import annotations

__all__: list[str] = []
