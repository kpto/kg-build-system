"""Portable annotations attached to declarations."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class Annotation:
    """Base for a portable annotation with a namespace and an annotation id.

    A concrete annotation declares both as class variables and adds the fields
    that travel with it.

    Example:
        ```python
        from dataclasses import dataclass
        from kg_build_system.annotations import Annotation

        @dataclass(frozen=True)
        class Owner(Annotation):
            namespace = "example"
            annotation_id = "owner"

            name: str
        ```
    """

    namespace: ClassVar[str]
    annotation_id: ClassVar[str]


def annotation_tuple(values: Sequence[Annotation]) -> tuple[Annotation, ...]:
    """Return the values as a tuple, rejecting anything that is not an annotation.

    Example:
        ```python
        from kg_build_system.annotations import NodeLabel
        from kg_build_system.annotations.interfaces import annotation_tuple

        annotation_tuple([NodeLabel("Sensor")])
        ```
    """
    result = tuple(values)
    if any(not isinstance(value, Annotation) for value in result):
        raise TypeError("annotations must contain only Annotation values")
    return result


__all__ = ["Annotation", "annotation_tuple"]
