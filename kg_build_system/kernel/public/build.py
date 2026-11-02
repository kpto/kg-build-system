"""The frozen build: one named IR part per language.

A build is the kernel's boundary between lowering and compilation. Languages
lower declarations into named parts, the registry freezes those parts into a
``BuildIR``, and a module compiler reads them by name. A build carries only
frozen data: it has no language, module or engine attached.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Generic, TypeVar


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class BuildIR:
    """An immutable mapping from language name to that language's lowered part.

    The mapping is copied and wrapped in a read-only proxy. ``part`` fails with
    ``KeyError`` for an unknown name; ``part_as`` also checks the runtime type.

    Example:
    ```python
    from kg_build_system.kernel import BuildIR

    build = BuildIR({"data": ("table",)})
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
        from kg_build_system.kernel import BuildIR

        build = BuildIR({"data": ("table",)})
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
        from kg_build_system.kernel import BuildIR

        build = BuildIR({"data": ("table",)})
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


@dataclass(frozen=True, slots=True)
class Build:
    """A frozen build together with the modules that will consume it.

    The value is a thin holder: ``part`` delegates to the wrapped ``BuildIR``.
    Composition of the parts belongs to ``Registry``; compilation belongs to the
    module compilers.

    Example:
    ```python
    from kg_build_system.kernel import Build, BuildIR

    build = Build(BuildIR({"data": ("table",)}))
    assert build.part("data") == ("table",)
    ```
    """

    ir: BuildIR

    def part(self, name: str) -> Any:
        """Return the part named ``name`` from the wrapped build.

        Example:
            ```python
            from kg_build_system.kernel import Build, BuildIR

            assert Build(BuildIR({"data": ()})).part("data") == ()
            ```
        """
        return self.ir.part(name)


__all__ = ["Build", "BuildIR"]
