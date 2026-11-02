"""Language protocol: authoring declarations to one named IR part."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol


class Namespace(Protocol):
    """The authoring objects one build may collect declarations from."""

    def values(self) -> Sequence[object]: ...


class LanguageContext(Protocol):
    """The already-lowered parts a language may read."""

    def part(self, name: str) -> Any: ...


class Language(Protocol):
    name: str
    requires: tuple[str, ...]

    def collect(self, namespace: Namespace) -> Sequence[object]: ...

    def lower(
        self, declarations: Sequence[object], context: LanguageContext,
    ) -> Any: ...

    def validate(self, ir: Any) -> None: ...

    def encode(self, ir: Any) -> Any: ...

    def decode(self, value: Any) -> Any: ...


__all__ = ["Language", "LanguageContext", "Namespace"]
