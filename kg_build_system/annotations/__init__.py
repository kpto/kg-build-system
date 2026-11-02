"""Author-facing annotation base and single-label annotation types.

Example:
    ```python
    from kg_build_system.annotations import Annotation, EdgeLabel, NodeLabel

    NodeLabel("Sensor")
    EdgeLabel("MEASURES")
    ```
"""
from __future__ import annotations

from .public import Annotation, EdgeLabel, NodeLabel

__all__ = ["Annotation", "EdgeLabel", "NodeLabel"]
