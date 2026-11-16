"""Declarative composition values for a project manifest.

A manifest states what a project composes; it does not build or compile. The
values are frozen declarations, so importing a manifest has no side effects.
The command line finds them by type and runs the composition.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kg_build_system.distribution.languages.binding.model.public import (
        Binding,
    )
    from kg_build_system.kernel import Toolchain


@dataclass(frozen=True, slots=True)
class Blueprint:
    """The declaration namespace or explicit bindings one blueprint is built from.

    Supply exactly one of ``namespace_path`` and a non-empty ``bindings``
    sequence. ``languages`` replaces the default language set when supplied.

    Example:
        ```python
        from pathlib import Path

        from kg_build_system import Blueprint

        blueprint = Blueprint(namespace_path=Path("project"))
        ```
    """

    namespace_path: str | Path | None = None
    bindings: Iterable[Binding] = ()
    languages: Sequence[Any] | None = None

    def __post_init__(self) -> None:
        bindings = tuple(self.bindings)
        if self.namespace_path is not None and bindings:
            raise ValueError(
                "Blueprint accepts namespace_path or bindings, not both"
            )
        if self.namespace_path is None and not bindings:
            raise ValueError(
                "Blueprint requires namespace_path or at least one binding"
            )
        object.__setattr__(self, "bindings", bindings)


@dataclass(frozen=True, slots=True)
class Workflow:
    """One blueprint and the planners or toolchain that compile and run it.

    ``planners`` adds planners to the default toolchain. ``toolchain`` replaces
    the default toolchain outright, so it cannot be combined with ``planners``.
    ``output_directory`` is the default destination for ``kbs run``.

    Example:
        ```python
        from pathlib import Path

        from kg_build_system import Blueprint, Workflow
        from kg_build_system.distribution import (
            FileConfiguration, FilePlanner,
        )

        blueprint = Blueprint(namespace_path=Path("project"))
        workflow = Workflow(
            blueprint=blueprint,
            planners=(FilePlanner(FileConfiguration("graph.jsonl")),),
            output_directory=Path("build"),
        )
        ```
    """

    blueprint: Blueprint
    planners: Sequence[Any] = ()
    toolchain: Toolchain[Any] | None = None
    output_directory: str | Path | None = None

    def __post_init__(self) -> None:
        planners = tuple(self.planners)
        if self.toolchain is not None and planners:
            raise ValueError(
                "Workflow accepts planners or a toolchain, not both"
            )
        object.__setattr__(self, "planners", planners)


__all__ = ["Blueprint", "Workflow"]
