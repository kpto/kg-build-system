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

from .distribution import (
    AssetLanguage,
    BindingLanguage,
    BlueprintLinker,
    ConflictReportExecutor,
    DataLanguage,
    DuckDbExecutor,
    DuckDbResourceProvider,
    DuckDbSourcePlanner,
    DuckDbSqlEmitter,
    ExpressionsLanguage,
    FileExecutor,
    GraphLanguage,
    MetaGraphExecutor,
    Neo4jExecutor,
    PythonExecutor,
    RuntimeResources,
    TopologyLanguage,
    core_planners,
)
from .distribution.interpreter import GraphBlueprint, create_blueprint as _create_blueprint
from .distribution.interpreter.service.internal.codec import blueprint_to_document
from .distribution.languages.binding import Binding
from .distribution.model.public.runtime import BuildRuntime
from .frontend import Monitor, resolve_monitor
from .kernel import (
    JsonValue,
    Language,
    Planner,
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
    ExpressionsLanguage(), AssetLanguage(), DataLanguage(), TopologyLanguage(),
    BindingLanguage(), GraphLanguage(),
)
DEFAULT_EXECUTORS = (
    DuckDbExecutor(),
    PythonExecutor(),
    ConflictReportExecutor(),
    FileExecutor(),
    MetaGraphExecutor(),
    Neo4jExecutor(),
)


def default_languages(
    *, expressions: ExpressionsLanguage | Language | None = None,
) -> tuple[Language, ...]:
    """Return the default language set, optionally replacing expressions.

    A project that declares its own operations supplies an
    ``ExpressionsLanguage`` with that operation set. Every other default
    language is unchanged.

    Example:
    ```python
    from kg_build_system import default_languages
    from kg_build_system.distribution import ExpressionsLanguage

    language = ExpressionsLanguage(operations=(custom_spec,))
    languages = default_languages(expressions=language)
    ```
    """
    if expressions is None:
        return DEFAULT_LANGUAGES
    if any(language.name == "expressions" for language in DEFAULT_LANGUAGES):
        return tuple(
            expressions if language.name == "expressions" else language
            for language in DEFAULT_LANGUAGES
        )
    return (*DEFAULT_LANGUAGES, expressions)


def default_toolchain(
    *,
    planners: Sequence[Planner[GraphBlueprint]] = (),
    executors: Sequence[StepExecutor] | None = None,
    engine: DuckDbSqlEmitter | None = None,
    languages: Sequence[Language] | None = None,
) -> Toolchain[GraphBlueprint]:
    """Return a graph toolchain with the supplied planners and executors added.

    The generic DuckDB source planner is added before the core planners, and a
    caller-supplied core planner is not duplicated: the four default core
    planners are added only when no planner reports ``component_id == "core"``.
    ``languages`` replaces the default language set; it never merges with it.

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
    configured: tuple[Planner[GraphBlueprint], ...] = tuple(planners)
    selected_engine = engine if engine is not None else DuckDbSqlEmitter()
    selected_languages = (
        DEFAULT_LANGUAGES if languages is None else tuple(languages)
    )
    sources: tuple[Planner[GraphBlueprint], ...] = (
        ()
        if any(planner.component_id == "duckdb" for planner in configured)
        else (DuckDbSourcePlanner(),)
    )
    if not any(planner.component_id == "core" for planner in configured):
        configured = (
            *sources, *core_planners(engine=selected_engine), *configured,
        )
    elif sources:
        configured = (*sources, *configured)
    return Toolchain(
        languages=selected_languages,
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
    languages: Sequence[Language] | None = None,
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
    if binding_values:
        if namespace_path is not None:
            raise ValueError(
                "namespace_path cannot be combined with bindings"
            )
        return _create_blueprint(
            bindings=binding_values, languages=languages,
        )
    if namespace_path is None:
        namespace_path = _calling_namespace_path()
    return _create_blueprint(namespace_path=namespace_path, languages=languages)


def compile(
    *,
    blueprint: GraphBlueprint | None = None,
    namespace_path: str | Path | None = None,
    bindings: Iterable[Binding] | None = None,
    planners: Sequence[Planner[GraphBlueprint]] = (),
    toolchain: Toolchain[GraphBlueprint] | None = None,
    engine: DuckDbSqlEmitter | None = None,
) -> WorkflowPlan:
    """Compile a graph blueprint into a workflow plan.

    This is the canonical shortcut: it creates the blueprint when one is not
    supplied, then compiles it with the default toolchain or the supplied one.
    The returned plan records the source blueprint document under
    ``plan.provenance["blueprint"]``, so the plan can be read without a second
    artifact.

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
        if namespace_path is not None or bindings is not None:
            raise ValueError(
                "blueprint cannot be combined with namespace_path or bindings"
            )
        prepared = blueprint
    else:
        prepared = create_blueprint(
            namespace_path=namespace_path,
            bindings=() if bindings is None else bindings,
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
    plan = selected.compile(prepared)
    existing = plan.provenance
    provenance: dict[str, JsonValue] = dict(existing) if isinstance(existing, dict) else (
        {} if existing is None else {"plan": existing}
    )
    provenance["blueprint"] = blueprint_to_document(prepared)
    return replace(plan, provenance=provenance)


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
    "default_languages",
    "default_toolchain",
    "execute",
]
