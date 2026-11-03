"""The frozen build: one named part per language.

A build is the kernel's boundary between transcription and compilation.
Languages transcribe declarations into named parts, the registry freezes those
parts into a ``Build``, and a module compiler reads them by name. A build
carries only frozen data: it has no language, module or engine attached.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, TypeVar


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Build:
    """An immutable mapping from language name to that language's transcribed part.

    The mapping is copied and wrapped in a read-only proxy. ``part`` fails with
    ``KeyError`` for an unknown name; ``part_as`` also checks the runtime type.

    Example:
    ```python
    from kg_build_system.kernel import Build

    build = Build({"data": ("table",)})
    assert build.part("data") == ("table",)
    assert "data" in build
    ```
    """

    parts: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "parts", MappingProxyType(dict(self.parts)))

    def part(self, name: str) -> Any:
        """Return the part named ``name`` or raise ``KeyError``.

        Example:
        ```python
        from kg_build_system.kernel import Build

        build = Build({"data": ("table",)})
        assert build.part("data") == ("table",)
        ```
        """
        try:
            return self.parts[name]
        except KeyError as error:
            raise KeyError(f"build has no language part {name!r}") from error

    def part_as(self, name: str, expected: type[T]) -> T:
        """Return a part and require it to be an instance of ``expected``.

        Example:
        ```python
        from kg_build_system.kernel import Build

        build = Build({"data": ("table",)})
        assert build.part_as("data", tuple) == ("table",)
        ```
        """
        value = self.part(name)
        if not isinstance(value, expected):
            raise TypeError(
                f"build part {name!r} is {type(value).__name__}, "
                f"expected {expected.__name__}"
            )
        return value

    def __contains__(self, name: str) -> bool:
        return name in self.parts


__all__ = ["Build"]
