"""The inline source fragment a declaration layer renders.

A layer owns the rendering of its own DTO. The fragment is the unit the
blueprint source service assembles; it is text plus the imports the text needs.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceFragment:
    """One inline piece of authoring source.

    Example:
        ```python
        from kg_build_system.declaration.foundations import SourceFragment

        fragment = SourceFragment("NodeLabel(\\"Sensor\\")")
        assert fragment.text == 'NodeLabel("Sensor")'
        ```
    """

    text: str
    imports: tuple[str, ...] = ()


__all__ = ["SourceFragment"]
