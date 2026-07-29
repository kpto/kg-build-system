"""Shared structural declaration models."""
from abc import ABC
from typing import ClassVar, Generic, TypeVar, overload

T = TypeVar("T")
E = TypeVar("E")

class Specification(ABC):
    """A reusable declarative structural contract."""
    _projection_fields: ClassVar[dict[str, object]] = {}

class Declaration(Generic[T], ABC):
    """A typed declaration whose resolved value is T."""

    @property
    def element(self: "Declaration[list[E]]") -> E:
        """Typed authoring view of a collection element; implemented by field paths."""
        raise AttributeError("element is available only on resolved collection field paths")
