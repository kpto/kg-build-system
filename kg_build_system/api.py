"""Composition root for knowledge-graph builds.

The canonical flow creates a blueprint, compiles it into a workflow plan and
executes that plan:

```python
plan = compile(planners=(FilePlanner(FileConfiguration("graph.jsonl")),))
report = execute(plan, output_directory=Path("build"))
```

An advanced caller can create and inspect the blueprint explicitly:

```python
blueprint = create_blueprint(namespace_path=ROOT)
plan = compile(blueprint=blueprint)
```
"""
from __future__ import annotations

import inspect
import json
from collections.abc import Iterable, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from .distribution import (
    BindingLanguage,
    BlueprintLinker,
    ConflictReportExecutor,
    DataLanguage,
    DuckDbExecutor,
    DuckDbResourceProvider,
    ExpressionsLanguage,
    FileExecutor,
    MetaGraphExecutor,
    Neo4jExecutor,
    PythonExecutor,
    RuntimeResources,
    TopologyLanguage,
    core_planners,
)
from .distribution.interpreter import GraphBlueprint, create_blueprint as _create_blueprint
from .distribution.languages.binding import Binding
from .distribution.languages.data import BoundSource
from .distribution.model.public.runtime import BuildRuntime
from .frontend import Monitor, resolve_monitor
from .kernel import (
    RuntimeConfiguration,
    StepExecutor,
    Toolchain,
    WorkflowPlan,
    WorkflowReport,
    WorkflowRuntime,
)
from .kernel.service.internal.report_codec import workflow_report_to_document
from .kernel.service.internal.workflow_codec import workflow_plan_to_document

DEFAULT_LANGUAGES = (
    ExpressionsLanguage(), DataLanguage(), TopologyLanguage(), BindingLanguage(),
)
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

    A caller-supplied core planner is not duplicated: the five default core
    planners are added only when no planner reports ``component_id == "core"``.

    Example:
    ```python
    from kg_build_system import default_toolchain
    from kg_build_system.distribution.modules.file import (
        FileConfiguration, FilePlanner,
    )

    toolchain = default_toolchain(
        planners=(FilePlanner(FileConfiguration("graph.jsonl")),),
    )
    ```
    """
    configured: tuple[Any, ...] = tuple(planners)
    if not any(planner.component_id == "core" for planner in configured):
        configured = (*core_planners(engine=engine), *configured)
    return Toolchain(
        languages=DEFAULT_LANGUAGES,
        linker=BlueprintLinker(),
        planners=configured,
        executors=tuple(executors or DEFAULT_EXECUTORS),
        runtime=WorkflowRuntime(
            providers=(RuntimeResources(), DuckDbResourceProvider()),
        ),
    )


DEFAULT_TOOLCHAIN = default_toolchain()


def _calling_namespace_path() -> Path:
    package_root = Path(__file__).resolve().parent
    frame = inspect.currentframe()
    try:
        frame = frame.f_back if frame is not None else None
        while frame is not None:
            filename = frame.f_code.co_filename
            if not filename.startswith("<"):
                path = Path(filename).resolve()
                if not path.is_relative_to(package_root):
                    return path.parent
            frame = frame.f_back
        raise RuntimeError("cannot determine the calling file")
    finally:
        del frame


def create_blueprint(
    *,
    namespace_path: str | Path | None = None,
    bindings: Iterable[Binding] = (),
    sources: Sequence[BoundSource] = (),
    languages: Sequence[Any] | None = None,
) -> GraphBlueprint:
    """Create the semantic blueprint for one declaration namespace.

    Example:
        ```python
        from pathlib import Path
        from kg_build_system import create_blueprint

        blueprint = create_blueprint(namespace_path=Path("my_project"))
        ```
    """
    binding_values = tuple(bindings)
    if binding_values or sources:
        if namespace_path is not None:
            raise ValueError(
                "namespace_path cannot be combined with bindings or sources"
            )
        return _create_blueprint(
            bindings=binding_values, sources=sources, languages=languages,
        )
    if namespace_path is None:
        namespace_path = _calling_namespace_path()
    return _create_blueprint(namespace_path=namespace_path, languages=languages)


def compile(
    *,
    blueprint: GraphBlueprint | None = None,
    namespace_path: str | Path | None = None,
    bindings: Iterable[Binding] | None = None,
    sources: Sequence[BoundSource] | None = None,
    planners: Sequence[Any] = (),
    toolchain: Toolchain[GraphBlueprint] | None = None,
    engine: Any = None,
) -> WorkflowPlan:
    """Compile a graph blueprint into a workflow plan.

    This is the canonical shortcut: it creates the blueprint when one is not
    supplied, then compiles it with the default toolchain or the supplied one.

    Example:
        ```python
        from kg_build_system import compile
        from kg_build_system.distribution import (
            FileConfiguration, FilePlanner,
        )

        plan = compile(
            planners=(FilePlanner(FileConfiguration("graph.jsonl")),),
        )
        ```
    """
    if blueprint is not None:
        if namespace_path is not None or bindings is not None or sources is not None:
            raise ValueError(
                "blueprint cannot be combined with namespace_path, bindings, or sources"
            )
        prepared = blueprint
    else:
        prepared = create_blueprint(
            namespace_path=namespace_path,
            bindings=() if bindings is None else bindings,
            sources=() if sources is None else sources,
        )
    if toolchain is None:
        selected: Toolchain[GraphBlueprint] = default_toolchain(
            planners=planners, engine=engine,
        )
    else:
        selected = (
            toolchain
            if not planners
            else toolchain.with_planners((*toolchain.planners, *planners))
        )
    return selected.compile(prepared)


def execute(
    plan: WorkflowPlan,
    *,
    output_directory: str | Path,
    runtime: BuildRuntime | None = None,
    toolchain: Toolchain[GraphBlueprint] | None = None,
    monitor: Monitor | bool | None = None,
) -> WorkflowReport:
    """Execute a workflow plan and return its report.

    The output directory is an execution argument, not a build setting: the
    supplied ``BuildRuntime`` states credentials, component overrides and engine
    settings, while ``output_directory`` states where this run writes.
    ``monitor`` is a frontend listener: ``None`` and ``False`` present nothing,
    ``True`` selects a ``ConsoleMonitor`` and a monitor is used as supplied.

    Example:
        ```python
        from pathlib import Path

        from kg_build_system import execute

        report = execute(plan, output_directory=Path("build"))
        ```
    """
    selected = toolchain if toolchain is not None else DEFAULT_TOOLCHAIN
    destination = Path(output_directory)
    destination.mkdir(parents=True, exist_ok=True)
    settings = runtime if runtime is not None else BuildRuntime()
    settings = replace(settings, output_directory=destination)
    configuration: RuntimeConfiguration = settings.to_configuration()
    (destination / "workflow_plan.json").write_text(
        json.dumps(
            workflow_plan_to_document(plan),
            indent=2,
            sort_keys=True,
            default=str,
        ),
        encoding="utf-8",
    )
    selected_monitor = resolve_monitor(monitor)
    listeners = () if selected_monitor is None else (selected_monitor,)
    report = selected.execute(
        plan,
        output_directory=destination,
        configuration=configuration,
        listeners=listeners,
    )
    (destination / "build_report.json").write_text(
        json.dumps(
            workflow_report_to_document(report),
            indent=2,
            sort_keys=True,
            default=lambda value: (
                value.model_dump(mode="json")
                if hasattr(value, "model_dump") else str(value)
            ),
        ),
        encoding="utf-8",
    )
    return report


__all__ = [
    "DEFAULT_EXECUTORS",
    "DEFAULT_LANGUAGES",
    "DEFAULT_TOOLCHAIN",
    "GraphBlueprint",
    "compile",
    "create_blueprint",
    "default_toolchain",
    "execute",
]
