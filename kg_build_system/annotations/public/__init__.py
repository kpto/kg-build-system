"""Author-facing annotation base and single-label annotation types.

Example:
    ```python
    from kg_build_system.annotations import Annotation, EdgeLabel, NodeLabel

    NodeLabel("Sensor")
    EdgeLabel("MEASURES")
    ```
"""
from __future__ import annotations

from .labels import EdgeLabel, NodeLabel
from .models import Annotation

__all__ = ["Annotation", "EdgeLabel", "NodeLabel"]
