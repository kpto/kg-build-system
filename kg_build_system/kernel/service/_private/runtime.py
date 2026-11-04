"""Schedule workflow steps, dispatch instructions and assemble the report.

The kernel runtime owns resource allocation, scheduling, input classification
and the step lifecycle. It treats resources and instruction payloads as opaque:
no engine, SQL, DuckDB or distribution import appears here. An executor owns its
own engine bookkeeping.

Every schedule key is a typed ``StepId`` or ``OpeningId``. The only string left
is a step label or an executor input-map key.
"""
from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, cast

from ...model.public.key import Key
from ...model.public.runtime import (
    Artifact,
    ContinuableInput,
    DisruptedExecutionContext,
    DisruptingInput,
    ExecutionContext,
    Failure,
    PublishedArtifact,
    ResourceView,
    RuntimeConfiguration,
    StepOutcome,
    StepStatus,
    WorkflowReport,
)
from ...model.public.workflow import (
    ArtifactType,
    Component,
    InstructionKind,
    OpeningId,
    Publication,
    Step,
    StepId,
    WorkflowPlan,
    input_opening,
    output_opening,
    step_id,
)


def _unresolved(step: Step, role: str) -> ValueError:
    return ValueError(f"step {step_id(step)} has an unresolved {role}")


class WorkflowMonitor(Protocol):
    """A minimal observer for one workflow execution."""

    def start(self, plan: WorkflowPlan) -> None:
        """Begin observing one workflow."""
        ...

    def step_started(self, step_id: StepId, detail: str) -> None:
        """Record that one step started."""
        ...

    def step_finished(self, outcome: StepOutcome, detail: str) -> None:
        """Record that one step finished."""
        ...

    def workflow_finished(self, report: WorkflowReport) -> None:
        """Record the completed report."""
        ...

    def workflow_halted(self, message: str) -> None:
        """Record that execution halted."""
        ...

    def stop(self) -> None:
        """Stop observing and release presentation resources."""
        ...


class NullWorkflowMonitor:
    """No-op observer for non-interactive and embedded execution."""

    def start(self, plan: WorkflowPlan) -> None:
        """Begin observing one workflow."""
        pass

    def step_started(self, step_id: StepId, detail: str) -> None:
        """Record that one step started."""
        pass

    def step_finished(self, outcome: StepOutcome, detail: str) -> None:
        """Record that one step finished."""
        pass

    def workflow_finished(self, report: WorkflowReport) -> None:
        """Record the completed report."""
        pass

    def workflow_halted(self, message: str) -> None:
        """Record that execution halted."""
        pass

    def stop(self) -> None:
        """Stop observing and release presentation resources."""
        pass


def _notify(monitor: Any, name: str, *arguments: Any) -> None:
    method = getattr(monitor, name, None)
    if callable(method):
        method(*arguments)


def _resource_name(resource: type) -> str:
    """The fully qualified name of one resource type."""
    return f"{resource.__module__}.{resource.__qualname__}"


class _StepLogger:
    """A logger scoped to one step, backed by the workflow monitor."""

    def __init__(self, step_id: StepId, monitor: Any) -> None:
        self._step_id = step_id
        self._logger = _monitor_logger(monitor)

    def _write(self, level: str, message: str, args: tuple[Any, ...]) -> None:
        logger = self._logger
        if logger is None:
            return
        method = getattr(logger, level, None)
        if callable(method):
            method(f"[{self._step_id}] {message}", *args)

    def debug(self, message: str, *args: Any) -> None:
        self._write("debug", message, args)

    def info(self, message: str, *args: Any) -> None:
        self._write("info", message, args)

    def warning(self, message: str, *args: Any) -> None:
        self._write("warning", message, args)

    def error(self, message: str, *args: Any) -> None:
        self._write("error", message, args)


def _monitor_logger(monitor: Any) -> Any:
    """The logging-like object a monitor exposes, when it exposes one."""
    logger = getattr(monitor, "logger", None)
    if logger is not None:
        return logger
    if all(
        callable(getattr(monitor, level, None))
        for level in ("debug", "info", "warning", "error")
    ):
        return monitor
    return None


def _open_resources(
    providers: Sequence[Any], configuration: RuntimeConfiguration,
) -> dict[type, Any]:
    """Open every provider and merge its typed resources."""
    merged: dict[type, Any] = {}
    for provider in providers:
        provided = dict(provider.resources(configuration))
        for resource, value in provided.items():
            if resource in merged:
                raise ValueError(
                    "duplicate resource type "
                    f"{_resource_name(resource)} provided by more than one provider"
                )
            merged[resource] = value
    return merged


def _executor_views(
    executors: Mapping[InstructionKind, Any], merged: Mapping[type, Any],
) -> dict[int, ResourceView]:
    """Build the exact resource view each executor declared."""
    views: dict[int, ResourceView] = {}
    for executor in executors.values():
        key = id(executor)
        if key in views:
            continue
        declared = tuple(getattr(executor, "resources", ()))
        missing = [resource for resource in declared if resource not in merged]
        if missing:
            names = ", ".join(_resource_name(resource) for resource in missing)
            raise ValueError(
                f"executor {type(executor).__name__} requires missing resource(s): "
                f"{names}"
            )
        views[key] = ResourceView(
            {resource: merged[resource] for resource in declared},
        )
    return views


def _close_resources(providers: Sequence[Any]) -> None:
    """Close every provider in reverse order, even when one close raises."""
    failure: Exception | None = None
    for provider in reversed(tuple(providers)):
        try:
            provider.close()
        except Exception as error:
            if failure is None:
                failure = error
    if failure is not None:
        raise failure


@dataclass(frozen=True, slots=True)
class Schedule:
    """Steps and openings indexed by their typed identities."""

    steps: tuple[Step, ...]
    components: Mapping[str, Component]
    output_owner: Mapping[OpeningId, StepId]
    publication_ids: tuple[OpeningId, ...]
    publishing_steps: tuple[StepId, ...]
    incoming: Mapping[OpeningId, tuple[OpeningId, ...]]

    def sources(self, input_id: OpeningId) -> tuple[OpeningId, ...]:
        """Return the output openings feeding one taken opening."""
        return self.incoming.get(input_id, ())

    def is_ready(self, step: Step, completed: set[StepId]) -> bool:
        """Return whether every producer of a step has completed."""
        for taken in step.inputs:
            for source in self.sources(input_opening(step, taken)):
                if self.output_owner[source] not in completed:
                    return False
        return True


@dataclass(frozen=True, slots=True)
class _DeclaredOpenings:
    inputs: Mapping[OpeningId, StepId]
    outputs: Mapping[OpeningId, ArtifactType]
    owners: Mapping[OpeningId, StepId]


def _declared_openings(
    steps: Sequence[Step],
) -> _DeclaredOpenings:
    declared_inputs: dict[OpeningId, StepId] = {}
    declared_outputs: dict[OpeningId, ArtifactType] = {}
    owners: dict[OpeningId, StepId] = {}
    seen_steps: set[StepId] = set()
    for step in steps:
        identity = step_id(step)
        if identity in seen_steps:
            raise ValueError(f"duplicate step id {identity}")
        seen_steps.add(identity)
        for taken in step.inputs:
            if taken.opening_name is None:
                raise _unresolved(step, "input")
            opening = input_opening(step, taken)
            if opening in declared_inputs:
                raise ValueError(f"duplicate input opening {opening}")
            declared_inputs[opening] = identity
        names: set[Key] = set()
        for given in step.outputs:
            if given.opening_name is None:
                raise _unresolved(step, "output")
            if given.opening_name in names:
                raise ValueError(
                    f"step {identity} declares output "
                    f"{given.opening_name!s} twice"
                )
            names.add(given.opening_name)
            opening = output_opening(step, given)
            if opening in declared_outputs:
                raise ValueError(f"duplicate output opening {opening}")
            declared_outputs[opening] = given.type
            owners[opening] = identity
    return _DeclaredOpenings(declared_inputs, declared_outputs, owners)


def schedule(plan: WorkflowPlan) -> Schedule:
    """Validate a plan and index it by its typed identities.

    The scheduler is the single authority for executable plan identity. It
    refuses duplicate step ids, duplicate component ids, a step whose component
    is absent, an unresolved executable opening, a duplicate output name and a
    connection whose endpoint is not declared.
    """
    steps = tuple(plan.steps)
    component_ids = [component.id for component in plan.components]
    if len(component_ids) != len(set(component_ids)):
        raise ValueError("workflow component ids must be unique")
    components = {component.id: component for component in plan.components}
    declared = _declared_openings(steps)
    for step in steps:
        if step.component not in components:
            raise ValueError(
                f"step {step_id(step)} names unknown component "
                f"{step.component!r}"
            )
    incoming: dict[OpeningId, list[OpeningId]] = defaultdict(list)
    for connection in plan.connections:
        if connection.input not in declared.inputs:
            raise ValueError(
                f"connection input {connection.input} is not declared by a step"
            )
        if connection.output not in declared.outputs:
            raise ValueError(
                f"connection output {connection.output} is not declared by a step"
            )
        incoming[connection.input].append(connection.output)

    publication_ids = tuple(
        output_opening(step, given)
        for step in steps for given in step.outputs
        if isinstance(given, Publication)
    )
    publishing_steps = tuple(dict.fromkeys(
        step_id(step)
        for step in steps
        if any(isinstance(given, Publication) for given in step.outputs)
    ))
    return Schedule(
        steps=steps,
        components=components,
        output_owner=dict(declared.owners),
        publication_ids=publication_ids,
        publishing_steps=publishing_steps,
        incoming={key: tuple(value) for key, value in incoming.items()},
    )


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
    component: Component, configuration: dict[str, Any],
) -> None:
    """Refuse unknown, missing or wrongly typed runtime configuration."""
    fields = {field.key: field for field in component.runtime_fields}
    unknown = sorted(set(configuration) - set(fields))
    if unknown:
        raise ValueError(
            f"unknown runtime configuration for {component.id}: "
            + ", ".join(unknown)
        )
    missing = sorted(
        key for key, field in fields.items()
        if field.required and key not in configuration
    )
    if missing:
        raise ValueError(
            f"missing runtime configuration for {component.id}: "
            + ", ".join(missing)
        )
    invalid = sorted(
        key for key, value in configuration.items()
        if not _runtime_value_matches(value, fields[key].value_type)
    )
    if invalid:
        raise TypeError(
            f"invalid runtime configuration for {component.id}: "
            + ", ".join(invalid)
        )


@dataclass(slots=True)
class _ExecutionState:
    """The results accumulated while the schedule runs."""

    completed: set[StepId] = field(default_factory=set)
    artifacts: dict[OpeningId, Artifact] = field(default_factory=dict)
    outcomes_by_step: dict[StepId, StepOutcome] = field(default_factory=dict)
    active_failures_by_step: dict[StepId, set[Failure]] = field(
        default_factory=dict,
    )
    outcomes: list[StepOutcome] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class _StepRun:
    """The outcome of one step and what it returned."""

    outcome: StepOutcome
    inherited_failures: frozenset[Failure]
    returned_artifacts: Mapping[Key, Artifact]


def _gather_inputs(
    step: Step,
    scheduled: Schedule,
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
        for source in scheduled.sources(input_opening(step, taken)):
            owner = scheduled.output_owner[source]
            previous = state.outcomes_by_step[owner]
            inherited_failures.update(state.active_failures_by_step[owner])
            artifact = state.artifacts.get(source)
            if previous.status in {StepStatus.SUCCEEDED, StepStatus.WARNING}:
                gathered[taken.declared_name].append(ContinuableInput(
                    source,
                    cast(
                        Literal[StepStatus.SUCCEEDED, StepStatus.WARNING],
                        previous.status,
                    ),
                    artifact,
                ))
            else:
                disruption = DisruptingInput(
                    source,
                    cast(
                        Literal[StepStatus.FAILED, StepStatus.SKIPPED],
                        previous.status,
                    ),
                    artifact,
                    previous.failure,
                )
                gathered[taken.declared_name].append(disruption)
                disruptions.append(disruption)
    return (
        {name: tuple(values) for name, values in gathered.items()},
        tuple(disruptions),
        frozenset(inherited_failures),
    )


def _validate_outcome(
    outcome: StepOutcome,
    step: Step,
) -> Mapping[Key, Artifact]:
    """Check an outcome against what the schedule asked of this step."""
    identity = step_id(step)
    if outcome.step_id != identity:
        raise RuntimeError(
            f"executor returned an outcome for a different step: {identity}"
        )
    if outcome.status == StepStatus.FAILED and outcome.failure is None:
        raise RuntimeError(f"failed step {identity} did not provide a failure")
    if (
        outcome.failure is not None
        and outcome.failure.step_id != identity
    ):
        raise RuntimeError(
            f"step {identity} reported a failure for a different step"
        )
    declared: dict[Key, ArtifactType] = {}
    for given in step.outputs:
        if given.opening_name is None:
            raise _unresolved(step, "output")
        if given.opening_name in declared:
            raise RuntimeError(
                f"step {identity} declares output {given.opening_name!s} twice"
            )
        declared[given.opening_name] = given.type
    returned: dict[Key, Artifact] = {}
    for artifact in outcome.artifacts:
        if artifact.output_name in returned:
            raise RuntimeError(
                f"step {identity} returned output "
                f"{artifact.output_name!s} twice"
            )
        returned[artifact.output_name] = artifact
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
    step: Step,
    *,
    scheduled: Schedule,
    executors: Mapping[InstructionKind, Any],
    views: Mapping[int, ResourceView],
    state: _ExecutionState,
    configuration: RuntimeConfiguration,
    monitor: Any,
) -> _StepRun:
    """Run one ready step through its instruction executor."""
    identity = step_id(step)
    detail = (
        f"Processing {len(step.inputs)} input(s) → "
        f"{len(step.outputs)} output(s)"
    )
    _notify(monitor, "step_started", identity, detail)
    by_input, disruptions, inherited_failures = _gather_inputs(
        step, scheduled, state,
    )
    runtime_configuration = dict(
        configuration.component_configuration.get(step.component, {}),
    )
    component = scheduled.components[step.component]
    _validate_runtime_configuration(component, runtime_configuration)
    executor = executors.get(step.instruction.kind)
    if executor is None:
        raise RuntimeError(
            f"no executor for instruction kind {step.instruction.kind}"
        )
    resources = views[id(executor)]
    logger = _StepLogger(identity, monitor)
    try:
        if disruptions:
            context = DisruptedExecutionContext(
                step=step,
                runtime_configuration=runtime_configuration,
                inputs=by_input,
                disruptions=tuple(disruptions),
                resources=resources,
                logger=logger,
            )
        else:
            continuable_inputs = {
                name: tuple(
                    item for item in values if isinstance(item, ContinuableInput)
                )
                for name, values in by_input.items()
            }
            context = ExecutionContext(
                step=step,
                runtime_configuration=runtime_configuration,
                inputs=continuable_inputs,
                resources=resources,
                logger=logger,
            )
        outcome = executor.execute(context, step.instruction)
    except Exception as error:
        outcome = StepOutcome(
            step_id=identity,
            status=StepStatus.FAILED,
            failure=Failure(
                str(error), identity, type(error).__name__,
            ),
        )
    returned = _validate_outcome(outcome, step)
    return _StepRun(
        outcome=outcome,
        inherited_failures=inherited_failures,
        returned_artifacts=returned,
    )


def _record_step(
    step: Step,
    run: _StepRun,
    state: _ExecutionState,
    pending: list[Step],
) -> None:
    """Record one outcome, its artifacts and the failures it keeps active."""
    outcome = run.outcome
    state.artifacts.update({
        artifact.opening(outcome.step_id): artifact
        for artifact in run.returned_artifacts.values()
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
    pending.remove(step)


def _outcome_detail(outcome: StepOutcome) -> str:
    """A short description of one finished outcome."""
    detail = f"{outcome.status.value}; {len(outcome.artifacts)} artifact(s)"
    if outcome.failure is not None:
        detail += f" — {outcome.failure.message}"
    return detail


def _execute(
    scheduled: Schedule,
    executors: Mapping[InstructionKind, Any],
    views: Mapping[int, ResourceView],
    configuration: RuntimeConfiguration,
    monitor: Any,
) -> _ExecutionState:
    """Run every step in waves whose producers have all completed."""
    state = _ExecutionState()
    pending = list(scheduled.steps)
    while pending:
        ready = [
            step for step in pending
            if scheduled.is_ready(step, state.completed)
        ]
        if not ready:
            raise RuntimeError("workflow has a dependency cycle")
        for step in ready:
            run = _execute_step(
                step,
                scheduled=scheduled,
                executors=executors,
                views=views,
                state=state,
                configuration=configuration,
                monitor=monitor,
            )
            _record_step(step, run, state, pending)
            detail = _outcome_detail(run.outcome)
            _notify(monitor, "step_finished", run.outcome, detail)
    return state


def _published_artifacts(
    scheduled: Schedule, state: _ExecutionState,
) -> tuple[PublishedArtifact, ...]:
    """The artifacts the plan publishes, in declaration order."""
    return tuple(
        PublishedArtifact(
            opening=output_id,
            type=state.artifacts[output_id].type,
            value=state.artifacts[output_id].value,
        )
        for output_id in scheduled.publication_ids
        if output_id in state.artifacts
    )


def _classify_failures(
    scheduled: Schedule, state: _ExecutionState,
) -> tuple[tuple[Failure, ...], tuple[Failure, ...]]:
    """Split failures into those still active at a publisher and recovered ones."""
    unresolved_set = (
        set().union(*(
            state.active_failures_by_step[step_id]
            for step_id in scheduled.publishing_steps
            if step_id in state.active_failures_by_step
        ))
        if scheduled.publishing_steps else set()
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
    scheduled: Schedule, state: _ExecutionState,
) -> tuple[
    tuple[PublishedArtifact, ...],
    tuple[Failure, ...],
    tuple[Failure, ...],
]:
    """Split the finished execution into publications and the two failure sets."""
    recovered, unresolved = _classify_failures(scheduled, state)
    return _published_artifacts(scheduled, state), recovered, unresolved


def _report(
    plan: WorkflowPlan,
    *,
    published: tuple[PublishedArtifact, ...],
    recovered: tuple[Failure, ...],
    unresolved: tuple[Failure, ...],
) -> WorkflowReport:
    """Assemble the report from the execution result and plan provenance."""
    provenance: dict[str, Any] = (
        dict(plan.provenance)
        if isinstance(plan.provenance, dict)
        else {"plan": plan.provenance}
    )
    return WorkflowReport(
        published_artifacts=published,
        recovered_failures=recovered,
        unresolved_failures=unresolved,
        provenance=provenance,
    )


class WorkflowRuntime:
    """The kernel's scheduler-backed implementation of the ``Runtime`` protocol."""

    def __init__(self, providers: Sequence[Any] = ()) -> None:
        self._providers = tuple(providers)

    def execute(
        self,
        plan: WorkflowPlan,
        executors: Mapping[InstructionKind, Any],
        *,
        configuration: RuntimeConfiguration,
        monitor: Any = None,
    ) -> WorkflowReport:
        """Run one plan and return its report."""
        observer: Any = (
            NullWorkflowMonitor()
            if monitor is None or isinstance(monitor, bool)
            else monitor
        )
        _notify(observer, "start", plan)
        try:
            try:
                merged = _open_resources(self._providers, configuration)
                views = _executor_views(executors, merged)
                scheduled = schedule(plan)
                unknown = sorted(
                    set(configuration.component_configuration)
                    - set(scheduled.components)
                )
                if unknown:
                    raise ValueError(
                        "unknown component configuration: " + ", ".join(unknown)
                    )
                state = _execute(
                    scheduled, executors, views, configuration, observer,
                )
                published, recovered, unresolved = _classify(scheduled, state)
                report = _report(
                    plan,
                    published=published,
                    recovered=recovered,
                    unresolved=unresolved,
                )
                _notify(observer, "workflow_finished", report)
                return report
            finally:
                _close_resources(self._providers)
        except Exception as error:
            _notify(observer, "workflow_halted", str(error))
            raise
        finally:
            _notify(observer, "stop")


def succeeded(
    context: ExecutionContext,
    value: Any,
    *,
    status: StepStatus = StepStatus.SUCCEEDED,
) -> StepOutcome:
    """The outcome of a step that emits its first declared output."""
    artifacts: tuple[Artifact, ...] = ()
    if context.step.outputs:
        output = context.step.outputs[0]
        if output.opening_name is None:
            raise _unresolved(context.step, "output")
        artifacts = (Artifact(output.opening_name, output.type, value),)
    return StepOutcome(
        step_id=context.step_id,
        status=status,
        artifacts=artifacts,
    )


def skipped(context: DisruptedExecutionContext) -> StepOutcome:
    """The default disrupted policy: carry the failure forward without running."""
    return StepOutcome(
        step_id=context.step_id,
        status=StepStatus.SKIPPED,
    )


__all__ = [
    "NullWorkflowMonitor", "Schedule", "WorkflowMonitor", "WorkflowRuntime",
    "schedule", "skipped", "succeeded",
]
