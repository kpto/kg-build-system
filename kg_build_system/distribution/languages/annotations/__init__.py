"""Author-facing annotation base and single-label annotation types.

Example:
    ```python
    from kg_build_system.distribution.languages.annotations import (
        Annotation, EdgeLabel, NodeLabel,
    )

    NodeLabel("Sensor")
    EdgeLabel("MEASURES")
    ```
"""
from __future__ import annotations

from .model.public import Annotation, EdgeLabel, NodeLabel

__all__ = ["Annotation", "EdgeLabel", "NodeLabel"]
