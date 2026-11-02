"""Execute frozen workflow contracts through importable workflow modules.

Execution is decomposed into named stages: the build lays out its directories,
opens one engine session, imports and validates the module registry, derives a
schedule from the resolved connections, executes the schedule, classifies the
outcomes, and builds the report. A step handler receives its data context and
reads the runtime services from ``context.services``.
"""
from __future__ import annotations

import importlib
import json
import logging
from collections import defaultdict
from collections.abc import Iterator, Mapping, Sequence
from contextlib import ExitStack, contextmanager
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Literal, cast

from pydantic import JsonValue

from ..._frozen_json import thaw_json
from ...engines.internal import DuckDBRelationService, configure_framework_macros
from ...kernel import (
    Artifact,
    ContinuableInput,
    DisruptedExecutionContext,
    DisruptingInput,
    ExecutionContext,
    ExecutorFactoryContext,
    Failure,
    ModuleDefinition,
    Publication,
    PublishedArtifact,
    StepOutcome,
    StepStatus,
)
from .._private.identity import opening_identity, output_name, step_identity
from .ir import WorkflowContractIR
from .._private.mapping import workflow_from_ir
from .models import (
    DefinedStep,
    WorkflowDefinition,
)
from ..public.models import BuildRuntime, WorkflowReport
from .._private.monitor import (
    NullWorkflowMonitor,
    RichWorkflowMonitor,
    WorkflowExecutionMonitor,
)
from .services import (
    ExecutionServices,
    LocalTemporaryStorage,
    LocalWorkingStorage,
    MappingCredentialResolver,
    WorkflowLogger,
)


_LOGGER = logging.getLogger("kg_build_system.workflow.execution")
_LOGGER.addHandler(logging.NullHandler())
_DUCKDB_BUILD_DATABASE = "kg_build_memory"
_DUCKDB_BUILD_FILENAME = "kg_build.duckdb"
# A TIMESTAMPTZ is handed to Python as a datetime whose tzinfo is the session
# TimeZone rather than a property of the data, and that setting defaults to the
# machine's zone, so a build pins it instead of inheriting it.
PINNED_TIME_ZONE = "UTC"


class _MonitorLogger:
    """Logger that forwards one step's messages to the monitor."""

    def __init__(
        self, monitor: WorkflowExecutionMonitor, *,
        module_id: str | None = None, step_id: str | None = None,
    ) -> None:
        self._monitor = monitor
        self._module_id = module_id
        self._step_id = step_id

    def debug(self, message: str, *args: object) -> None:
        """Forward one debug message."""
        self._emit(logging.DEBUG, message, args)

    def info(self, message: str, *args: object) -> None:
        """Forward one informational message."""
        self._emit(logging.INFO, message, args)

    def warning(self, message: str, *args: object) -> None:
        """Forward one warning."""
        self._emit(logging.WARNING, message, args)

    def error(self, message: str, *args: object) -> None:
        """Forward one error."""
        self._emit(logging.ERROR, message, args)

    def _emit(
        self, level: int, message: str, args: tuple[object, ...],
    ) -> None:
        """Internal helper for emit."""
        rendered = message % args if args else message
        extra = {
            "workflow_module_id": self._module_id,
            "workflow_step_id": self._step_id,
        }
        _LOGGER.log(level, rendered, extra=extra)
        self._monitor.log(
            logging.getLevelName(level), rendered, step_id=self._step_id,
        )


def _resolve_monitor(
    monitor: WorkflowExecutionMonitor | bool | None,
) -> WorkflowExecutionMonitor:
    """Internal helper for resolve monitor."""
    if monitor is False:
        return NullWorkflowMonitor()
    if monitor is not None and monitor is not True:
        return monitor
    rich_monitor = RichWorkflowMonitor()
    if monitor is True or rich_monitor.console.is_terminal:
        return rich_monitor
    return NullWorkflowMonitor()


def _load_class(import_module: str, qualname: str) -> type[Any]:
    """Internal helper for load class."""
    value: Any = importlib.import_module(import_module)
    for part in qualname.split("."):
        value = getattr(value, part)
    return value


def _runtime_value_matches(value: Any, value_type: str) -> bool:
    """Internal helper for runtime value matches."""
    if value_type == "string":
        return isinstance(value, str)
    if value_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if value_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if value_type == "boolean":
        return isinstance(value, bool)
    if value_type == "json":
        try:
            json.dumps(value)
        except (TypeError, ValueError):
            return False
        return True
    return False


def _validate_runtime_configuration(
    module: ModuleDefinition, configuration: dict[str, Any],
) -> None:
    """Internal helper for validate runtime configuration."""
    fields = {field.key: field for field in module.runtime_fields}
    module_id = module.reference.module_id
    unknown = sorted(set(configuration) - set(fields))
    if unknown:
        raise ValueError(
            f"unknown runtime configuration for {module_id}: "
            + ", ".join(unknown)
        )
    missing = sorted(
        key for key, field in fields.items()
        if field.required and key not in configuration
    )
    if missing:
        raise ValueError(
            f"missing runtime configuration for {module_id}: "
            + ", ".join(missing)
        )
    invalid = sorted(
        key for key, value in configuration.items()
        if not _runtime_value_matches(value, fields[key].value_type)
    )
    if invalid:
        raise TypeError(
            f"invalid runtime configuration for {module_id}: "
            + ", ".join(invalid)
        )


@dataclass(frozen=True, slots=True)
class _Layout:
    """Directories one execution owns for its lifetime."""

    working_directory: Path
    temporary_directory: Path
    storage_directory: Path


@contextmanager
def _layout(runtime: BuildRuntime) -> Iterator[_Layout]:
    """Create the temporary roots, including the private DuckDB disk location."""
    with TemporaryDirectory(dir=runtime.temporary_directory) as temporary:
        temporary_directory = Path(temporary)
        if runtime.duckdb_storage == "disk":
            with TemporaryDirectory(
                prefix=".kg-build-duckdb-", dir=runtime.working_directory,
            ) as storage:
                yield _Layout(
                    runtime.working_directory,
                    temporary_directory,
                    Path(storage),
                )
        else:
            yield _Layout(
                runtime.working_directory,
                temporary_directory,
                temporary_directory,
            )


@dataclass(frozen=True, slots=True)
class _EngineSession:
    """The opened engine behind one build, with its effective settings."""

    relations: DuckDBRelationService
    time_zone: str
    memory_limit: str | None
    threads: int | None


def _open_duckdb(
    duckdb: Any, runtime: BuildRuntime, storage_directory: Path,
) -> Any:
    """Open the configured in-memory or working-directory database."""
    if runtime.duckdb_storage == "memory":
        return duckdb.connect()
    if runtime.duckdb_storage == "disk":
        return duckdb.connect(str(storage_directory / _DUCKDB_BUILD_FILENAME))
    raise ValueError("duckdb_storage must be 'memory' or 'disk'")


def _configure_duckdb(
    connection: Any, runtime: BuildRuntime, storage_directory: Path,
) -> None:
    """Configure resource limits and storage policy for one build."""
    if runtime.duckdb_threads is not None:
        if runtime.duckdb_threads < 1:
            raise ValueError("duckdb_threads must be at least one")
        connection.execute("SET threads = ?", [runtime.duckdb_threads])

    if runtime.duckdb_memory_limit is not None:
        if not isinstance(runtime.duckdb_memory_limit, str):
            raise TypeError("duckdb_memory_limit must be a string")
        if not runtime.duckdb_memory_limit.strip():
            raise ValueError("duckdb_memory_limit must be non-empty")
        connection.execute(
            "SET memory_limit = ?", [runtime.duckdb_memory_limit]
        )

    if not isinstance(runtime.duckdb_compression, bool):
        raise TypeError("duckdb_compression must be a boolean")

    connection.execute(
        "SET temp_directory = ?", [storage_directory.resolve().as_posix()]
    )
    if runtime.duckdb_storage == "memory":
        compression = " (COMPRESS)" if runtime.duckdb_compression else ""
        connection.execute(
            f"ATTACH ':memory:' AS {_DUCKDB_BUILD_DATABASE}{compression}"
        )
        connection.execute(f"USE {_DUCKDB_BUILD_DATABASE}")
    elif runtime.duckdb_storage == "disk":
        if not runtime.duckdb_compression:
            connection.execute("PRAGMA force_compression = 'uncompressed'")
    else:
        raise ValueError("duckdb_storage must be 'memory' or 'disk'")
    # After USE, so the macro lands in the database the build works in, and
    # before any relation is defined, which is when a lowered guard resolves.
    configure_framework_macros(connection)
    # Also before any view is created: every statement the build lowers, and
    # every temporal value it reads back, evaluates against this session state.
    connection.execute("SET TimeZone = ?", [PINNED_TIME_ZONE])


def _effective_duckdb_resources(connection: Any) -> tuple[str, int]:
    """Read DuckDB's normalized effective resource settings."""
    settings = dict(connection.execute(
        "SELECT name, value FROM duckdb_settings() "
        "WHERE name IN ('memory_limit', 'threads')"
    ).fetchall())
    return str(settings["memory_limit"]), int(settings["threads"])


def _effective_duckdb_time_zone(connection: Any) -> str:
    """Read the normalized session time zone the build ended up with."""
    return str(connection.execute(
        "SELECT current_setting('TimeZone')"
    ).fetchone()[0])


@contextmanager
def _engine_session(
    runtime: BuildRuntime, layout: _Layout,
) -> Iterator[_EngineSession]:
    """Open, configure and close the one relational engine a build uses."""
    try:
        import duckdb
    except ImportError as error:
        raise RuntimeError("DuckDB is required to execute builds") from error
    with ExitStack() as resources:
        connection = _open_duckdb(duckdb, runtime, layout.storage_directory)
        try:
            _configure_duckdb(connection, runtime, layout.storage_directory)
            time_zone = _effective_duckdb_time_zone(connection)
            memory_limit, threads = _effective_duckdb_resources(connection)
        except BaseException:
            connection.close()
            raise
        relations = DuckDBRelationService(
            connection,
            checkpoint_on_step=(
                runtime.duckdb_compression or runtime.duckdb_storage == "disk"
            ),
        )
        resources.callback(relations.close)
        yield _EngineSession(
            relations=relations,
            time_zone=time_zone,
            memory_limit=memory_limit,
            threads=threads,
        )


def _show_engine_settings(
    monitor: WorkflowExecutionMonitor,
    runtime: BuildRuntime,
    engine: _EngineSession,
) -> None:
    """Internal helper for show engine settings."""
    if isinstance(monitor, RichWorkflowMonitor):
        monitor.set_duckdb_settings(
            storage=runtime.duckdb_storage,
            compression=runtime.duckdb_compression,
            memory_limit=engine.memory_limit,
            threads=engine.threads,
        )


@dataclass(frozen=True, slots=True)
class _ModuleRegistry:
    """Importable executors and the data each contribution supplied."""

    definitions: Mapping[str, ModuleDefinition]
    variables: Mapping[str, Mapping[str, Any]]
    executors: Mapping[str, Any]


def _module_registry(
    workflow: WorkflowDefinition, runtime: BuildRuntime,
) -> _ModuleRegistry:
    """Import every module and validate its version and runtime configuration."""
    definitions: dict[str, ModuleDefinition] = {}
    variables: dict[str, Mapping[str, Any]] = {}
    executors: dict[str, Any] = {}
    for contribution in workflow.contributions:
        module = contribution.module
        reference = module.reference
        definitions[reference.module_id] = module
        variables[reference.module_id] = (
            dict(thaw_json(contribution.variables))
            if contribution.variables is not None else {}
        )
        cls = _load_class(reference.import_module, reference.class_qualname)
        if getattr(cls, "ID", None) != reference.module_id:
            raise RuntimeError(
                f"module import does not provide {reference.module_id!r}"
            )
        runtime_version = getattr(cls, "VERSION", None)
        if str(runtime_version) != reference.implementation_version:
            raise RuntimeError(
                f"module {reference.module_id!r} implementation version "
                f"{runtime_version!r} does not match compiled version "
                f"{reference.implementation_version!r}"
            )
        configuration = runtime.module_configuration.get(reference.module_id, {})
        _validate_runtime_configuration(module, configuration)
        factory_context = ExecutorFactoryContext(
            module, variables[reference.module_id], configuration,
        )
        executors[reference.module_id] = cls.create_executor(factory_context)
    return _ModuleRegistry(
        definitions=definitions,
        variables=variables,
        executors=executors,
    )


@dataclass(frozen=True, slots=True)
class _Schedule:
    """The static execution graph implied by the frozen connections."""

    steps: tuple[tuple[str, DefinedStep], ...]
    identity_of: Mapping[tuple[str, str], str]
    output_owner: Mapping[str, str]
    publication_ids: tuple[str, ...]
    publishing_steps: tuple[str, ...]
    incoming: Mapping[str, tuple[str, ...]]

    def identity(self, module_id: str, step: DefinedStep) -> str:
        """Return the whole-workflow identity of one step."""
        return self.identity_of[(module_id, step.name)]

    def sources(self, step_id: str, taken_name: str) -> tuple[str, ...]:
        """Return the output identities feeding one taken opening."""
        return self.incoming.get(opening_identity(step_id, taken_name), ())

    def is_ready(
        self, entry: tuple[str, DefinedStep], completed: set[str],
    ) -> bool:
        """Return whether every producer of a step has completed."""
        module_id, step = entry
        identity = self.identity(module_id, step)
        return all(
            self.output_owner[source] in completed
            for taken in step.inputs
            for source in self.sources(identity, taken.name)
        )


def _schedule(workflow: WorkflowDefinition) -> _Schedule:
    """Index the assembled workflow by generated identities."""
    steps = tuple(workflow.steps_by_module)
    identity_of = {
        (module_id, step.name): step_identity(module_id, step.name)
        for module_id, step in steps
    }
    output_owner = {
        opening_identity(identity_of[(module_id, step.name)], output_name(output)):
            identity_of[(module_id, step.name)]
        for module_id, step in steps for output in step.outputs
    }
    publication_ids = tuple(
        opening_identity(identity_of[(module_id, step.name)], output_name(output))
        for module_id, step in steps for output in step.outputs
        if isinstance(output, Publication)
    )
    publishing_steps = tuple(dict.fromkeys(
        identity_of[(module_id, step.name)]
        for module_id, step in steps
        if any(isinstance(output, Publication) for output in step.outputs)
    ))
    incoming: dict[str, list[str]] = defaultdict(list)
    for connection in workflow.connections:
        incoming[connection.input_id].append(connection.output_id)
    return _Schedule(
        steps=steps,
        identity_of=identity_of,
        output_owner=output_owner,
        publication_ids=publication_ids,
        publishing_steps=publishing_steps,
        incoming={key: tuple(value) for key, value in incoming.items()},
    )


@dataclass(slots=True)
class _ExecutionState:
    """Internal implementation of ExecutionState."""
    completed: set[str] = field(default_factory=set)
    artifacts: dict[str, Artifact] = field(default_factory=dict)
    outcomes_by_step: dict[str, StepOutcome] = field(default_factory=dict)
    active_failures_by_step: dict[str, set[Failure]] = field(
        default_factory=dict,
    )
    outcomes: list[StepOutcome] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class _StepRun:
    """Internal implementation of StepRun."""
    outcome: StepOutcome
    inherited_failures: frozenset[Failure]
    returned_artifacts: Mapping[str, Artifact]


def _step_services(
    services: ExecutionServices,
    monitor: WorkflowExecutionMonitor,
    module_id: str,
    identity: str,
) -> ExecutionServices:
    """Internal helper for step services."""
    return replace(
        services,
        logger=_MonitorLogger(
            monitor, module_id=module_id, step_id=identity,
        ),
    )


def _gather_inputs(
    step: DefinedStep,
    identity: str,
    schedule: _Schedule,
    state: _ExecutionState,
) -> tuple[
    dict[str, tuple[ContinuableInput | DisruptingInput, ...]],
    tuple[DisruptingInput, ...],
    frozenset[Failure],
]:
    """Classify every connected artifact by its producer's final status."""
    gathered: dict[str, list[ContinuableInput | DisruptingInput]] = defaultdict(list)
    disruptions: list[DisruptingInput] = []
    inherited_failures: set[Failure] = set()
    for taken in step.inputs:
        for output_id in schedule.sources(identity, taken.name):
            owner = schedule.output_owner[output_id]
            previous = state.outcomes_by_step[owner]
            inherited_failures.update(state.active_failures_by_step[owner])
            artifact = state.artifacts.get(output_id)
            if previous.status in {StepStatus.SUCCEEDED, StepStatus.WARNING}:
                gathered[taken.input_name].append(ContinuableInput(
                    output_id,
                    cast(
                        Literal[StepStatus.SUCCEEDED, StepStatus.WARNING],
                        previous.status,
                    ),
                    artifact,
                ))
            else:
                disruption = DisruptingInput(
                    output_id,
                    cast(
                        Literal[StepStatus.FAILED, StepStatus.SKIPPED],
                        previous.status,
                    ),
                    artifact,
                    previous.failure,
                )
                gathered[taken.input_name].append(disruption)
                disruptions.append(disruption)
    return (
        {name: tuple(values) for name, values in gathered.items()},
        tuple(disruptions),
        frozenset(inherited_failures),
    )


def _validate_outcome(
    outcome: StepOutcome,
    identity: str,
    module_id: str,
    step: DefinedStep,
) -> Mapping[str, Artifact]:
    """Check an outcome against what the schedule asked of this step."""
    if outcome.step_id != identity or outcome.module_id != module_id:
        raise RuntimeError(
            f"module returned an outcome for a different step: {identity}"
        )
    if outcome.status == StepStatus.FAILED and outcome.failure is None:
        raise RuntimeError(f"failed step {identity} did not provide a failure")
    declared = {output_name(output): output.type for output in step.outputs}
    returned = {
        artifact.output_name: artifact for artifact in outcome.artifacts
    }
    if not set(returned) <= set(declared):
        raise RuntimeError(
            f"step {identity} returned an artifact for an undeclared output"
        )
    if any(
        artifact.type != declared[name] for name, artifact in returned.items()
    ):
        raise RuntimeError(
            f"step {identity} returned an artifact type its output does not declare"
        )
    return returned


def _execute_step(
    module_id: str,
    step: DefinedStep,
    *,
    schedule: _Schedule,
    registry: _ModuleRegistry,
    state: _ExecutionState,
    services: ExecutionServices,
    runtime: BuildRuntime,
    monitor: WorkflowExecutionMonitor,
    engine: _EngineSession,
) -> _StepRun:
    """Run one ready step and return the outcome it produced."""
    identity = schedule.identity(module_id, step)
    detail = (
        f"Processing {len(step.inputs)} input(s) → "
        f"{len(step.outputs)} output(s)"
    )
    monitor.step_started(identity, detail)
    step_services = _step_services(services, monitor, module_id, identity)
    step_services.logger.info("Started: %s", detail)
    by_input, disruptions, inherited_failures = _gather_inputs(
        step, identity, schedule, state,
    )
    runtime_configuration = runtime.module_configuration.get(module_id, {})
    try:
        if disruptions:
            context = DisruptedExecutionContext(
                registry.definitions[module_id],
                step,
                module_id,
                identity,
                registry.variables[module_id],
                runtime_configuration,
                by_input,
                tuple(disruptions),
                step_services,
            )
            outcome = registry.executors[module_id].handle_disrupted(context)
        else:
            continuable_inputs = {
                name: tuple(
                    item for item in values if isinstance(item, ContinuableInput)
                )
                for name, values in by_input.items()
            }
            context = ExecutionContext(
                registry.definitions[module_id],
                step,
                module_id,
                identity,
                registry.variables[module_id],
                runtime_configuration,
                continuable_inputs,
                step_services,
            )
            outcome = registry.executors[module_id].handle(context)
        engine.relations.finish_step()
    except Exception as error:
        step_services.logger.error(
            "%s: %s", type(error).__name__, error,
        )
        outcome = StepOutcome(
            step_id=identity,
            module_id=module_id,
            status=StepStatus.FAILED,
            failure=Failure(
                str(error), module_id, identity, type(error).__name__,
            ),
        )
    returned = _validate_outcome(outcome, identity, module_id, step)
    return _StepRun(
        outcome=outcome,
        inherited_failures=inherited_failures,
        returned_artifacts=returned,
    )


def _record_step(
    entry: tuple[str, DefinedStep],
    run: _StepRun,
    state: _ExecutionState,
    pending: list[tuple[str, DefinedStep]],
) -> None:
    """Record one outcome, its artifacts and the failures it keeps active."""
    outcome = run.outcome
    state.artifacts.update({
        opening_identity(outcome.step_id, name): artifact
        for name, artifact in run.returned_artifacts.items()
    })
    state.outcomes_by_step[outcome.step_id] = outcome
    if outcome.status == StepStatus.FAILED and outcome.failure is not None:
        state.active_failures_by_step[outcome.step_id] = (
            set(run.inherited_failures) | {outcome.failure}
        )
    elif outcome.status == StepStatus.SKIPPED:
        state.active_failures_by_step[outcome.step_id] = set(
            run.inherited_failures
        )
    else:
        state.active_failures_by_step[outcome.step_id] = set()
    state.outcomes.append(outcome)
    state.completed.add(outcome.step_id)
    pending.remove(entry)


def _outcome_detail(outcome: StepOutcome) -> str:
    """Internal helper for outcome detail."""
    detail = f"{outcome.status.value}; {len(outcome.artifacts)} artifact(s)"
    if outcome.failure is not None:
        detail += f" — {outcome.failure.message}"
    return detail


def _log_outcome(
    logger: WorkflowLogger, outcome: StepOutcome, detail: str,
) -> None:
    """Internal helper for log outcome."""
    if outcome.status == StepStatus.FAILED:
        logger.error("Finished: %s", detail)
    elif outcome.status == StepStatus.WARNING:
        logger.warning("Finished: %s", detail)
    else:
        logger.info("Finished: %s", detail)


def _execute(
    schedule: _Schedule,
    registry: _ModuleRegistry,
    services: ExecutionServices,
    runtime: BuildRuntime,
    monitor: WorkflowExecutionMonitor,
    engine: _EngineSession,
) -> _ExecutionState:
    """Run every step in waves whose producers have all completed."""
    state = _ExecutionState()
    pending = list(schedule.steps)
    while pending:
        ready = [
            entry for entry in pending
            if schedule.is_ready(entry, state.completed)
        ]
        if not ready:
            raise RuntimeError("workflow has a dependency cycle")
        for entry in ready:
            module_id, step = entry
            run = _execute_step(
                module_id,
                step,
                schedule=schedule,
                registry=registry,
                state=state,
                services=services,
                runtime=runtime,
                monitor=monitor,
                engine=engine,
            )
            _record_step(entry, run, state, pending)
            detail = _outcome_detail(run.outcome)
            monitor.step_finished(run.outcome, detail)
            _log_outcome(
                _MonitorLogger(
                    monitor,
                    module_id=module_id,
                    step_id=run.outcome.step_id,
                ),
                run.outcome,
                detail,
            )
    return state


def _published_artifacts(
    schedule: _Schedule, state: _ExecutionState,
) -> tuple[PublishedArtifact, ...]:
    """Internal helper for published artifacts."""
    return tuple(
        PublishedArtifact(type=artifact.type, value=artifact.value)
        for artifact in (
            state.artifacts[output_id]
            for output_id in schedule.publication_ids
            if output_id in state.artifacts
        )
    )


def _classify_failures(
    schedule: _Schedule, state: _ExecutionState,
) -> tuple[tuple[Failure, ...], tuple[Failure, ...]]:
    """Split failures into those still active at a publisher and recovered ones."""
    unresolved_set = (
        set().union(*(
            state.active_failures_by_step[step_id]
            for step_id in schedule.publishing_steps
            if step_id in state.active_failures_by_step
        ))
        if schedule.publishing_steps else set()
    )
    all_failures = tuple(
        outcome.failure for outcome in state.outcomes
        if outcome.failure is not None
    )
    return (
        tuple(
            failure for failure in all_failures
            if failure not in unresolved_set
        ),
        tuple(
            failure for failure in all_failures
            if failure in unresolved_set
        ),
    )


def _classify(
    schedule: _Schedule, state: _ExecutionState,
) -> tuple[
    tuple[PublishedArtifact, ...],
    tuple[Failure, ...],
    tuple[Failure, ...],
]:
    """Split the finished execution into publications and the two failure sets."""
    recovered, unresolved = _classify_failures(schedule, state)
    return _published_artifacts(schedule, state), recovered, unresolved


def _report(
    contract: WorkflowContractIR,
    *,
    time_zone: str,
    published: tuple[PublishedArtifact, ...],
    recovered: tuple[Failure, ...],
    unresolved: tuple[Failure, ...],
) -> WorkflowReport:
    """Internal helper for report."""
    provenance: dict[str, JsonValue] = (
        dict(contract.provenance)
        if isinstance(contract.provenance, dict)
        else {"contract": contract.provenance}
    )
    provenance["workflow_fingerprint"] = contract.workflow_fingerprint
    provenance["duckdb"] = {"TimeZone": time_zone}
    return WorkflowReport(
        published_artifacts=published,
        recovered_failures=recovered,
        unresolved_failures=unresolved,
        provenance=provenance,
    )


def _services(
    runtime: BuildRuntime,
    layout: _Layout,
    engine: _EngineSession,
    monitor: WorkflowExecutionMonitor,
) -> ExecutionServices:
    """Internal helper for services."""
    return ExecutionServices(
        relations=engine.relations,
        output_storage=LocalWorkingStorage(runtime.output_directory),
        working_storage=LocalWorkingStorage(layout.working_directory),
        temporary_storage=LocalTemporaryStorage(layout.temporary_directory),
        credentials=MappingCredentialResolver(runtime.credentials),
        logger=_MonitorLogger(monitor),
    )


def _build(
    contract: WorkflowContractIR,
    runtime: BuildRuntime,
    monitor: WorkflowExecutionMonitor,
) -> WorkflowReport:
    """Run one frozen contract through its named stages."""
    workflow = workflow_from_ir(contract.workflow)
    with _layout(runtime) as layout:
        with _engine_session(runtime, layout) as engine:
            _show_engine_settings(monitor, runtime, engine)
            services = _services(runtime, layout, engine, monitor)
            registry = _module_registry(workflow, runtime)
            schedule = _schedule(workflow)
            state = _execute(
                schedule, registry, services, runtime, monitor, engine,
            )
            published, recovered, unresolved = _classify(schedule, state)
            return _report(
                contract,
                time_zone=engine.time_zone,
                published=published,
                recovered=recovered,
                unresolved=unresolved,
            )


def build(
    contract: WorkflowContractIR,
    runtime: BuildRuntime | None = None,
    *,
    output_directory: str | Path = Path("build"),
    working_directory: str | Path = Path("_workdir"),
    temporary_directory: str | Path | None = None,
    monitor: WorkflowExecutionMonitor | bool | None = None,
) -> WorkflowReport:
    """Run a frozen workflow and persist its contract and report.

    Rich monitoring is enabled automatically on an interactive terminal. Pass
    ``monitor=True`` to force it, ``False`` to disable it, or provide a custom
    :class:`WorkflowExecutionMonitor` implementation.
    """
    configured = runtime or BuildRuntime()
    resolved_output = Path(output_directory).resolve()
    requested_working = Path(working_directory)
    resolved_working = (
        requested_working.resolve()
        if requested_working.is_absolute()
        else resolved_output / requested_working
    )
    resolved_temporary = (
        Path(temporary_directory)
        if temporary_directory is not None
        else configured.temporary_directory
    )
    configured = replace(
        configured,
        output_directory=resolved_output,
        working_directory=resolved_working,
        temporary_directory=resolved_temporary,
    )
    configured.output_directory.mkdir(parents=True, exist_ok=True)
    configured.working_directory.mkdir(parents=True, exist_ok=True)
    if configured.temporary_directory is not None:
        configured.temporary_directory.mkdir(parents=True, exist_ok=True)
    (configured.output_directory / "workflow_contract.json").write_text(
        contract.model_dump_json(indent=2), encoding="utf-8",
    )
    execution_monitor = _resolve_monitor(monitor)
    workflow = workflow_from_ir(contract.workflow)
    execution_monitor.start(workflow)
    try:
        report = _build(contract, configured, execution_monitor)
    except Exception as error:
        execution_monitor.workflow_halted(str(error))
        execution_monitor.log(
            "ERROR",
            f"Workflow execution stopped: {type(error).__name__}: {error}",
        )
        raise
    else:
        execution_monitor.workflow_finished(report)
    finally:
        execution_monitor.stop()
    (configured.output_directory / "build_report.json").write_text(
        json.dumps(
            asdict(report),
            indent=2,
            sort_keys=True,
            default=lambda item: (
                item.model_dump(mode="json")
                if hasattr(item, "model_dump") else str(item)
            ),
        ),
        encoding="utf-8",
    )
    return report


__all__ = ["PINNED_TIME_ZONE", "build"]
