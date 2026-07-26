from abc import ABC
from typing import Generic, TypeVar, overload

T = TypeVar("T")

class Specification(ABC):
    """A reusable declarative structural contract."""

class Declaration(Generic[T], ABC):
    """A typed declaration whose resolved value is T."""
