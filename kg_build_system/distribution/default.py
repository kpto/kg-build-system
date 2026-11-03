"""The default distribution toolchain: languages, linker, planners and executors.

The default toolchain is one distribution, not the kernel. A caller replaces any
part by passing a configured ``Toolchain`` to the public ``compile`` or
``execute`` shortcuts.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from kg_build_system.kernel import StepExecutor, Toolchain, WorkflowRuntime

from .executors.conflict_validation import ConflictReportExecutor
from .executors.duckdb import DuckDbExecutor, DuckDbResourceProvider
from .executors.file import FileExecutor
from .executors.meta_graph import MetaGraphExecutor
from .executors.neo4j import Neo4jExecutor
from .executors.python import PythonExecutor
from .interpreter.service.internal import BlueprintLinker
from .languages.binding.service.internal import BindingLanguage
from .languages.table.service.internal import TableLanguage
from .languages.topology.service.internal import TopologyLanguage
from .planners import CorePlanner

DEFAULT_LANGUAGES = (TableLanguage(), TopologyLanguage(), BindingLanguage())
DEFAULT_EXECUTORS = (
    DuckDbExecutor(),
    PythonExecutor(),
    ConflictReportExecutor(),
    FileExecutor(),
    MetaGraphExecutor(),
    Neo4jExecutor(),
)


def default_toolchain(
    *,
    planners: Sequence[Any] = (),
    executors: Sequence[StepExecutor] | None = None,
    engine: Any = None,
) -> Toolchain[Any]:
    """Return a graph toolchain with the supplied planners and executors added.

    A caller-supplied core planner is not duplicated: the core planner is added
    only when no planner reports ``component_id == "core"``.

    Example:
    ```python
    from kg_build_system.distribution import default_toolchain
    from kg_build_system.distribution.executors.file import (
        FileConfiguration, FilePlanner,
    )

    toolchain = default_toolchain(
        planners=(FilePlanner(FileConfiguration("graph.jsonl")),),
    )
    ```
    """
    configured: tuple[Any, ...] = tuple(planners)
    if not any(planner.component_id == "core" for planner in configured):
        configured = (CorePlanner(engine=engine), *configured)
    return Toolchain(
        languages=DEFAULT_LANGUAGES,
        linker=BlueprintLinker(),
        planners=configured,
        executors=tuple(executors or DEFAULT_EXECUTORS),
        resources=DuckDbResourceProvider(),
        runtime=WorkflowRuntime(),
    )


DEFAULT_TOOLCHAIN = default_toolchain()

__all__ = ["DEFAULT_EXECUTORS", "DEFAULT_LANGUAGES", "DEFAULT_TOOLCHAIN", "default_toolchain"]
