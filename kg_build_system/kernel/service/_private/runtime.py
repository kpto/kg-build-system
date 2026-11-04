"""Schedule workflow steps, dispatch instructions and assemble the report.

The kernel runtime owns resource allocation, scheduling, input classification
and the step lifecycle. It treats resources and instruction payloads as opaque:
no engine, SQL, DuckDB or distribution import appears here. An executor owns its
own engine bookkeeping.
"""
from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, cast

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
    Component,
    InstructionKind,
    Publication,
    Step,
    WorkflowPlan,
)

DEFAULT_OUTPUT_NAME = "output"


def output_name(given: Any) -> str:
    """The name an output or publication takes in an outcome."""
    return given.name or DEFAULT_OUTPUT_NAME


def step_identity(component: str, name: str) -> str:
    """The identity of one step across the whole workflow."""
    return f"{component}.{name}"


def opening_identity(identity: str, name: str) -> str:
    """The identity of one input or output of a step known by its identity."""
    return f"{identity}.{name}"


class WorkflowMonitor(Protocol):
    """A minimal observer for one workflow execution."""

    def start(self, plan: WorkflowPlan) -> None:
        """Begin observing one workflow."""
        ...

    def step_started(self, step_id: str, detail: str) -> None:
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

    def step_started(self, step_id: str, detail: str) -> None:
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

    def __init__(self, step_id: str, monitor: Any) -> None:
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
    """Steps indexed by the identities their openings and producers use."""

    steps: tuple[Step, ...]
    components: Mapping[str, Component]
    identity_of: Mapping[tuple[str, str], str]
    output_owner: Mapping[str, str]
    publication_ids: tuple[str, ...]
    publishing_steps: tuple[str, ...]
    incoming: Mapping[str, tuple[str, ...]]

    def identity(self, step: Step) -> str:
        """Return the whole-workflow identity of one step."""
        return self.identity_of[(step.component, step.name)]

    def sources(self, step_id: str, taken_name: str) -> tuple[str, ...]:
        """Return the output identities feeding one taken opening."""
        return self.incoming.get(opening_identity(step_id, taken_name), ())

    def is_ready(self, step: Step, completed: set[str]) -> bool:
        """Return whether every producer of a step has completed."""
        identity = self.identity(step)
        return all(
            self.output_owner[source] in completed
            for taken in step.inputs
            for source in self.sources(
                identity, taken.name or taken.input_name,
            )
        )


def schedule(plan: WorkflowPlan) -> Schedule:
    """Index a workflow plan by its generated identities."""
    steps = tuple(plan.steps)
    identity_of = {
        (step.component, step.name): step_identity(step.component, step.name)
        for step in steps
    }
    output_owner = {
        opening_identity(identity_of[(step.component, step.name)], output_name(output)):
            identity_of[(step.component, step.name)]
        for step in steps for output in step.outputs
    }
    publication_ids = tuple(
        opening_identity(identity_of[(step.component, step.name)], output_name(output))
        for step in steps for output in step.outputs
        if isinstance(output, Publication)
    )
    publishing_steps = tuple(dict.fromkeys(
        identity_of[(step.component, step.name)]
        for step in steps
        if any(isinstance(output, Publication) for output in step.outputs)
    ))
    incoming: dict[str, list[str]] = defaultdict(list)
    for connection in plan.connections:
        incoming[connection.input_id].append(connection.output_id)
    return Schedule(
        steps=steps,
        components={component.id: component for component in plan.components},
        identity_of=identity_of,
        output_owner=output_owner,
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


def _gather_inputs(
    step: Step,
    identity: str,
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
        for source in scheduled.sources(
            identity, taken.name or taken.input_name,
        ):
            owner = scheduled.output_owner[source]
            previous = state.outcomes_by_step[owner]
            inherited_failures.update(state.active_failures_by_step[owner])
            artifact = state.artifacts.get(source)
            if previous.status in {StepStatus.SUCCEEDED, StepStatus.WARNING}:
                gathered[taken.input_name].append(ContinuableInput(
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
    step: Step,
) -> Mapping[str, Artifact]:
    """Check an outcome against what the schedule asked of this step."""
    if outcome.step_id != identity:
        raise RuntimeError(
            f"executor returned an outcome for a different step: {identity}"
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
    identity = scheduled.identity(step)
    detail = (
        f"Processing {len(step.inputs)} input(s) → "
        f"{len(step.outputs)} output(s)"
    )
    _notify(monitor, "step_started", identity, detail)
    by_input, disruptions, inherited_failures = _gather_inputs(
        step, identity, scheduled, state,
    )
    runtime_configuration = dict(
        configuration.component_configuration.get(step.component, {}),
    )
    component = scheduled.components[step.component]
    _validate_runtime_configuration(component, runtime_configuration)
    executor = executors.get(step.instruction.kind)
    if executor is None:
        raise RuntimeError(
            f"no executor for instruction kind {step.instruction.kind!r}"
        )
    resources = views[id(executor)]
    logger = _StepLogger(identity, monitor)
    try:
        if disruptions:
            context = DisruptedExecutionContext(
                step=step,
                step_id=identity,
                component=step.component,
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
                step_id=identity,
                component=step.component,
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
    returned = _validate_outcome(outcome, identity, step)
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
        PublishedArtifact(type=artifact.type, value=artifact.value)
        for artifact in (
            state.artifacts[output_id]
            for output_id in scheduled.publication_ids
            if output_id in state.artifacts
        )
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
        artifacts = (Artifact(output_name(output), output.type, value),)
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
    "opening_identity", "output_name", "schedule", "skipped", "step_identity",
    "succeeded",
]
