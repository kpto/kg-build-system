"""Execute frozen workflow contracts through importable workflow modules."""
from __future__ import annotations

import asyncio
import importlib
from collections import defaultdict
from typing import Any

from ..compile.models import BuildContract
from .models import Artifact, BuildReport, BuildRuntime, Diagnostic, Failure, ModuleExecutionContext, StepOutcome, StepStatus


def _load_class(import_module: str, qualname: str) -> type[Any]:
    value: Any = importlib.import_module(import_module)
    for part in qualname.split("."):
        value = getattr(value, part)
    return value


async def _build(contract: BuildContract, runtime: BuildRuntime | None = None) -> BuildReport:
    runtime = runtime or BuildRuntime()
    try:
        import duckdb
    except ImportError as error:
        raise RuntimeError("DuckDB is required to execute builds") from error
    connection = duckdb.connect()
    if contract.settings.duckdb_threads is not None:
        connection.execute(f"SET threads = {contract.settings.duckdb_threads}")

    executors: dict[str, Any] = {}
    definitions = {module.reference.module_id: module for module in contract.workflow.modules}
    for module in contract.workflow.modules:
        reference = module.reference
        cls = _load_class(reference.import_module, reference.class_qualname)
        if getattr(cls, "ID", None) != reference.module_id:
            raise RuntimeError(f"module import does not provide {reference.module_id!r}")
        configuration = runtime.module_configuration.get(reference.module_id, {})
        missing = [field.key for field in module.runtime_fields if field.required and field.key not in configuration]
        if missing:
            raise ValueError(f"missing runtime configuration for {reference.module_id}: {', '.join(missing)}")
        factory_context = type("ExecutorFactoryContext", (), {"module": module, "runtime_configuration": configuration})()
        executors[reference.module_id] = await cls.create_executor(factory_context)

    output_owner = {slot.slot_id: step.step_id for step in contract.workflow.steps for slot in step.outputs}
    incoming: dict[str, list[str]] = defaultdict(list)
    consumed_outputs: set[str] = set()
    for workflow_connection in contract.workflow.connections:
        incoming[workflow_connection.input_slot_id].append(workflow_connection.output_slot_id)
        consumed_outputs.add(workflow_connection.output_slot_id)

    completed: set[str] = set()
    artifacts: dict[str, Artifact] = {}
    outcomes: list[StepOutcome] = []
    pending = list(contract.workflow.steps)
    while pending:
        ready = [step for step in pending if all(output_owner[slot_id] in completed for input_slot in step.inputs for slot_id in incoming[input_slot.slot_id])]
        if not ready:
            raise RuntimeError("workflow has a dependency cycle")
        for step in ready:
            inputs = {input_slot.slot_id: tuple(artifacts[slot_id] for slot_id in incoming[input_slot.slot_id]) for input_slot in step.inputs}
            context = ModuleExecutionContext(contract, definitions[step.module_id], runtime.module_configuration.get(step.module_id, {}), inputs, {"duckdb": connection})
            outcome = await executors[step.module_id].execute_step(context, step)
            if outcome.step_id != step.step_id or outcome.module_id != step.module_id:
                raise RuntimeError(f"module returned an outcome for a different step: {step.step_id}")
            if outcome.status != StepStatus.SUCCEEDED:
                raise RuntimeError(f"failure propagation is not implemented; {step.step_id} returned {outcome.status}")
            declared = {slot.slot_id: slot.artifact_role for slot in step.outputs}
            returned = {artifact.slot_id: artifact for artifact in outcome.artifacts}
            if set(returned) != set(declared):
                raise RuntimeError(f"step {step.step_id} did not return exactly its declared output artifacts")
            if any(artifact.role != declared[slot_id] for slot_id, artifact in returned.items()):
                raise RuntimeError(f"step {step.step_id} returned an artifact role inconsistent with its output slot")
            artifacts.update(returned)
            outcomes.append(outcome)
            completed.add(step.step_id)
            pending.remove(step)

    sink_step_ids = {
        step.step_id for step in contract.workflow.steps
        if not step.outputs or any(slot.slot_id not in consumed_outputs for slot in step.outputs)
    }
    all_artifacts = tuple(artifacts.values())
    all_diagnostics = tuple(diagnostic for outcome in outcomes for diagnostic in outcome.diagnostics)
    metrics: dict[str, int] = {}
    for outcome in outcomes:
        for name, value in outcome.metrics.items():
            metrics[name] = metrics.get(name, 0) + value
    return BuildReport(
        outcomes=tuple(outcomes),
        sink_outcomes=tuple(outcome for outcome in outcomes if outcome.step_id in sink_step_ids),
        artifacts=all_artifacts,
        diagnostics=all_diagnostics,
        recovered_failures=(),
        unresolved_failures=(),
        metrics=metrics,
        provenance={"blueprint_fingerprint": contract.blueprint_fingerprint, "workflow_fingerprint": contract.workflow_fingerprint, "workflow": contract.workflow.model_dump(mode="json")},
    )


def build(contract: BuildContract, runtime: BuildRuntime | None = None) -> BuildReport:
    """Run a frozen workflow while keeping the public MVP entry point synchronous."""
    return asyncio.run(_build(contract, runtime))
