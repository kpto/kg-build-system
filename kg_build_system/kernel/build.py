"""The frozen build: one named IR part per language."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Generic, TypeVar


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class BuildIR:
    parts: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "parts", MappingProxyType(dict(self.parts)))

    def part(self, name: str) -> Any:
        try:
            return self.parts[name]
        except KeyError as error:
            raise KeyError(f"build has no language part {name!r}") from error

    def part_as(self, name: str, expected: type[T]) -> T:
        value = self.part(name)
        if not isinstance(value, expected):
            raise TypeError(
                f"build part {name!r} is {type(value).__name__}, "
                f"expected {expected.__name__}"
            )
        return value

    def __contains__(self, name: str) -> bool:
        return name in self.parts


@dataclass(frozen=True, slots=True)
class Build:
    """A built IR plus the modules that will consume it."""

    ir: BuildIR

    def part(self, name: str) -> Any:
        return self.ir.part(name)


__all__ = ["Build", "BuildIR"]
