"""Execute a build contract by scheduling steps and dispatching instructions."""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Literal, cast

from pydantic import JsonValue

from ......kernel import (
    Artifact,
    ContinuableInput,
    DisruptedExecutionContext,
    DisruptingInput,
    ExecutionContext,
    Failure,
    ModuleDefinition,
    Publication,
    PublishedArtifact,
    StepOutcome,
    StepStatus,
)
from ....model.internal.contract import BuildContract, ContractStep
from ..engine import EngineSession, engine_session
from ..engine.sql import SqlInstructionExecutor
from ..instructions import InstructionDispatcher
from ..storage import (
    LocalTemporaryStorage,
    LocalWorkingStorage,
    MappingCredentialResolver,
)
from ....model.public import BuildRuntime, WorkflowReport
from .identity import opening_identity, output_name, step_identity
from .module import ContractModuleInstructionExecutor, legacy_instruction
from .monitor import (
    NullWorkflowMonitor,
    RichWorkflowMonitor,
    WorkflowExecutionMonitor,
)
from .python import PythonInstructionExecutor
from .scheduler import Schedule, schedule
from .services import ExecutionServices, WorkflowLogger

_LOGGER = logging.getLogger("kg_build_system.pipeline.build.execution")
_LOGGER.addHandler(logging.NullHandler())


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
        rendered = message % args if args else message
        extra = {
            "workflow_module_id": self._module_id,
            "workflow_step_id": self._step_id,
        }
        _LOGGER.log(level, rendered, extra=extra)
        self._monitor.log(
            logging.getLevelName(level), rendered, step_id=self._step_id,
        )


def resolve_monitor(
    monitor: WorkflowExecutionMonitor | bool | None,
) -> WorkflowExecutionMonitor:
    """Resolve the public monitor option into an observer."""
    if monitor is False:
        return NullWorkflowMonitor()
    if monitor is not None and monitor is not True:
        return monitor
    rich_monitor = RichWorkflowMonitor()
    if monitor is True or rich_monitor.console.is_terminal:
        return rich_monitor
    return NullWorkflowMonitor()


def _runtime_value_matches(value: Any, value_type: str) -> bool:
    """Whether one runtime configuration value has its declared scalar shape."""
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
    """Refuse unknown, missing or wrongly typed runtime configuration."""
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


def _show_engine_settings(
    monitor: WorkflowExecutionMonitor,
    runtime: BuildRuntime,
    engine: EngineSession,
) -> None:
    """Show the safe engine settings when the monitor supports it."""
    if isinstance(monitor, RichWorkflowMonitor):
        monitor.set_duckdb_settings(
            storage=runtime.duckdb_storage,
            compression=runtime.duckdb_compression,
            memory_limit=engine.memory_limit,
            threads=engine.threads,
        )


@dataclass(slots=True)
class _ExecutionState:
    """The results accumulated while the schedule runs."""

    completed: set[str] = field(default_factory=set)
    artifacts: dict[str, Artifact] = field(default_factory=dict)
    outcomes_by_step: dict[str, StepOutcome] = field(default_factory=dict)
    active_failures_by_step: dict[str, set[Failure]] = field(
        default_factory=dict,
    )
    outcomes: list[StepOutcome] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class _StepRun:
    """The outcome of one step and what it returned."""

    outcome: StepOutcome
    inherited_failures: frozenset[Failure]
    returned_artifacts: Mapping[str, Artifact]


def _step_services(
    services: ExecutionServices,
    monitor: WorkflowExecutionMonitor,
    module_id: str,
    identity: str,
) -> ExecutionServices:
    """Give one step a logger scoped to its module and identity."""
    return replace(
        services,
        logger=_MonitorLogger(
            monitor, module_id=module_id, step_id=identity,
        ),
    )


def _gather_inputs(
    step: ContractStep,
    identity: str,
    schedule: Schedule,
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
    step: ContractStep,
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
    step: ContractStep,
    *,
    schedule: Schedule,
    dispatcher: InstructionDispatcher,
    state: _ExecutionState,
    services: ExecutionServices,
    runtime: BuildRuntime,
    monitor: WorkflowExecutionMonitor,
    engine: EngineSession,
) -> _StepRun:
    """Run one ready step through its instruction."""
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
    _validate_runtime_configuration(step.module, runtime_configuration)
    instruction = step.instruction or legacy_instruction(step)
    try:
        if disruptions:
            context = DisruptedExecutionContext(
                step.module,
                step.defined_step,
                module_id,
                identity,
                step.variables,
                runtime_configuration,
                by_input,
                tuple(disruptions),
                step_services,
            )
        else:
            continuable_inputs = {
                name: tuple(
                    item for item in values if isinstance(item, ContinuableInput)
                )
                for name, values in by_input.items()
            }
            context = ExecutionContext(
                step.module,
                step.defined_step,
                module_id,
                identity,
                step.variables,
                runtime_configuration,
                continuable_inputs,
                step_services,
            )
        outcome = dispatcher.execute(context, instruction)
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
    entry: tuple[str, ContractStep],
    run: _StepRun,
    state: _ExecutionState,
    pending: list[tuple[str, ContractStep]],
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
    """A short description of one finished outcome."""
    detail = f"{outcome.status.value}; {len(outcome.artifacts)} artifact(s)"
    if outcome.failure is not None:
        detail += f" — {outcome.failure.message}"
    return detail


def _log_outcome(
    logger: WorkflowLogger, outcome: StepOutcome, detail: str,
) -> None:
    """Log one finished outcome at its status level."""
    if outcome.status == StepStatus.FAILED:
        logger.error("Finished: %s", detail)
    elif outcome.status == StepStatus.WARNING:
        logger.warning("Finished: %s", detail)
    else:
        logger.info("Finished: %s", detail)


def _execute(
    schedule: Schedule,
    dispatcher: InstructionDispatcher,
    services: ExecutionServices,
    runtime: BuildRuntime,
    monitor: WorkflowExecutionMonitor,
    engine: EngineSession,
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
                dispatcher=dispatcher,
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
    schedule: Schedule, state: _ExecutionState,
) -> tuple[PublishedArtifact, ...]:
    """The artifacts the contract publishes, in declaration order."""
    return tuple(
        PublishedArtifact(type=artifact.type, value=artifact.value)
        for artifact in (
            state.artifacts[output_id]
            for output_id in schedule.publication_ids
            if output_id in state.artifacts
        )
    )


def _classify_failures(
    schedule: Schedule, state: _ExecutionState,
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
    schedule: Schedule, state: _ExecutionState,
) -> tuple[
    tuple[PublishedArtifact, ...],
    tuple[Failure, ...],
    tuple[Failure, ...],
]:
    """Split the finished execution into publications and the two failure sets."""
    recovered, unresolved = _classify_failures(schedule, state)
    return _published_artifacts(schedule, state), recovered, unresolved


def _report(
    contract: BuildContract,
    *,
    time_zone: str,
    published: tuple[PublishedArtifact, ...],
    recovered: tuple[Failure, ...],
    unresolved: tuple[Failure, ...],
) -> WorkflowReport:
    """Assemble the report from the execution result and contract provenance."""
    provenance: dict[str, JsonValue] = (
        dict(contract.provenance)
        if isinstance(contract.provenance, dict)
        else {"contract": contract.provenance}
    )
    provenance["workflow_fingerprint"] = contract.fingerprint
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
    engine: EngineSession,
    monitor: WorkflowExecutionMonitor,
) -> ExecutionServices:
    """Assemble the live services one build passes to its executors."""
    return ExecutionServices(
        relations=engine.relations,
        output_storage=LocalWorkingStorage(runtime.output_directory),
        working_storage=LocalWorkingStorage(layout.working_directory),
        temporary_storage=LocalTemporaryStorage(layout.temporary_directory),
        credentials=MappingCredentialResolver(runtime.credentials),
        logger=_MonitorLogger(monitor),
    )


def default_dispatcher() -> InstructionDispatcher:
    """The generic instruction executors plus the contract module fallback.

    ``sql`` and ``python`` are build-level kinds. Every other kind is resolved
    through the module named by the step's contract contribution; the build does
    not name a target.
    """
    return InstructionDispatcher(
        {
            "sql": SqlInstructionExecutor(),
            "python": PythonInstructionExecutor(),
        },
        fallback=ContractModuleInstructionExecutor(),
    )


def execute_contract(
    contract: BuildContract,
    runtime: BuildRuntime,
    monitor: WorkflowExecutionMonitor,
    *,
    dispatcher: InstructionDispatcher | None = None,
) -> WorkflowReport:
    """Run one build contract through its instructions."""
    with _layout(runtime) as layout:
        with engine_session(runtime, layout.storage_directory) as engine:
            _show_engine_settings(monitor, runtime, engine)
            services = _services(runtime, layout, engine, monitor)
            sched = schedule(contract.workflow)
            state = _execute(
                sched,
                dispatcher or default_dispatcher(),
                services,
                runtime,
                monitor,
                engine,
            )
            published, recovered, unresolved = _classify(sched, state)
            return _report(
                contract,
                time_zone=engine.time_zone,
                published=published,
                recovered=recovered,
                unresolved=unresolved,
            )


__all__ = ["default_dispatcher", "execute_contract", "resolve_monitor"]
