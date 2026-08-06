"""Portable, serialisable declaration annotations."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, ClassVar


@dataclass(frozen=True)
class Annotation:
    """Base class for semantic metadata attached to declarations.

    Subclasses are dataclasses whose fields become the serialised arguments.
    Namespaces are descriptive and portable: any installed module may inspect
    and interpret any annotation it recognises.
    """

    namespace: ClassVar[str]
    annotation_id: ClassVar[str]

    def serialise(self) -> tuple[str, str, dict[str, Any]]:
        namespace = getattr(type(self), "namespace", None)
        annotation_id = getattr(type(self), "annotation_id", None)
        if not isinstance(namespace, str) or not namespace:
            raise TypeError("Annotation subclasses must define a non-empty namespace")
        if not isinstance(annotation_id, str) or not annotation_id:
            raise TypeError("Annotation subclasses must define a non-empty annotation_id")
        return namespace, annotation_id, asdict(self)


def annotation_tuple(values: tuple[Annotation, ...] | list[Annotation] = ()) -> tuple[Annotation, ...]:
    result = tuple(values)
    if not all(isinstance(value, Annotation) for value in result):
        raise TypeError("annotations must contain Annotation instances")
    return result
