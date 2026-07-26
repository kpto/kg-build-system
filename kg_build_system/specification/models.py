"""Shared structural declaration models."""
from abc import ABC
from typing import ClassVar, Generic, TypeVar

T = TypeVar("T")

class Specification(ABC):
    """A reusable declarative structural contract."""
    _projection_fields: ClassVar[dict[str, object]] = {}

class Declaration(Generic[T], ABC):
    """A typed declaration whose resolved value is T."""
