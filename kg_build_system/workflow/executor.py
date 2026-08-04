"""Execute frozen workflow contracts through importable workflow modules."""
from __future__ import annotations

import asyncio
import importlib
from collections import defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from ..compile.models import BuildContract
from .models import Artifact, BuildRuntime, ContinuableInput, DisruptedExecutionContext, DisruptingInput, ExecutionContext, ExecutorFactoryContext, Failure, PublishedArtifact, StepOutcome, StepStatus, WorkflowReport
from .services import ExecutionServices, LocalTemporaryStorage, LocalWorkingStorage, MappingCredentialResolver


def _load_class(import_module: str, qualname: str) -> type[Any]:
    value: Any = importlib.import_module(import_module)
    for part in qualname.split("."):
        value = getattr(value, part)
    return value


async def _build(contract: BuildContract, runtime: BuildRuntime | None = None) -> WorkflowReport:
    runtime = runtime or BuildRuntime()
    try:
        import duckdb
    except ImportError as error:
        raise RuntimeError("DuckDB is required to execute builds") from error
    connection = duckdb.connect()
    if contract.settings.duckdb_threads is not None:
        connection.execute(f"SET threads = {contract.settings.duckdb_threads}")

    with TemporaryDirectory(dir=runtime.temporary_storage) as temporary_directory:
      services = ExecutionServices(
          duckdb=connection,
          working_storage=LocalWorkingStorage(runtime.working_storage),
          temporary_storage=LocalTemporaryStorage(Path(temporary_directory)),
          credentials=MappingCredentialResolver(runtime.credentials),
      )
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
        factory_context = ExecutorFactoryContext(contract, module, configuration, services)
        executors[reference.module_id] = await cls.create_executor(factory_context)

      output_owner = {slot.slot_id: step.step_id for step in contract.workflow.steps for slot in step.outputs}
      incoming: dict[str, list[str]] = defaultdict(list)
      consumed_outputs: set[str] = set()
      for workflow_connection in contract.workflow.connections:
        incoming[workflow_connection.input_slot_id].append(workflow_connection.output_slot_id)
        consumed_outputs.add(workflow_connection.output_slot_id)

      completed: set[str] = set()
      artifacts: dict[str, Artifact] = {}
      outcomes_by_step: dict[str, StepOutcome] = {}
      outcomes: list[StepOutcome] = []
      pending = list(contract.workflow.steps)
      while pending:
        ready = [step for step in pending if all(output_owner[slot_id] in completed for input_slot in step.inputs for slot_id in incoming[input_slot.slot_id])]
        if not ready:
            raise RuntimeError("workflow has a dependency cycle")
        for step in ready:
            inputs = {}
            disruptions: list[DisruptingInput] = []
            for input_slot in step.inputs:
                contributions: list[ContinuableInput | DisruptingInput] = []
                for output_slot_id in incoming[input_slot.slot_id]:
                    previous = outcomes_by_step[output_owner[output_slot_id]]
                    artifact = artifacts.get(output_slot_id)
                    if previous.status in {StepStatus.SUCCEEDED, StepStatus.WARNING}:
                        contributions.append(ContinuableInput(output_slot_id, previous.status, artifact))
                    else:
                        disruption = DisruptingInput(output_slot_id, previous.status, artifact, previous.failure)
                        contributions.append(disruption)
                        disruptions.append(disruption)
                inputs[input_slot.slot_id] = tuple(contributions)
            try:
                if disruptions:
                    context = DisruptedExecutionContext(contract, definitions[step.module_id], step, runtime.module_configuration.get(step.module_id, {}), inputs, tuple(disruptions), services)
                    outcome = await executors[step.module_id].handle_disrupted(context)
                else:
                    continuable_inputs = {slot_id: tuple(item for item in values if isinstance(item, ContinuableInput)) for slot_id, values in inputs.items()}
                    context = ExecutionContext(contract, definitions[step.module_id], step, runtime.module_configuration.get(step.module_id, {}), continuable_inputs, services)
                    outcome = await executors[step.module_id].handle(context)
            except Exception as error:
                outcome = StepOutcome(
                    step_id=step.step_id,
                    module_id=step.module_id,
                    status=StepStatus.FAILED,
                    failure=Failure(str(error), step.module_id, step.step_id, type(error).__name__),
                )
            if outcome.step_id != step.step_id or outcome.module_id != step.module_id:
                raise RuntimeError(f"module returned an outcome for a different step: {step.step_id}")
            if outcome.status == StepStatus.FAILED and outcome.failure is None:
                raise RuntimeError(f"failed step {step.step_id} did not provide a failure")
            declared = {slot.slot_id: slot.artifact_role for slot in step.outputs}
            returned = {artifact.slot_id: artifact for artifact in outcome.artifacts}
            if not set(returned) <= set(declared):
                raise RuntimeError(f"step {step.step_id} returned an artifact for an undeclared output slot")
            if any(artifact.role != declared[slot_id] for slot_id, artifact in returned.items()):
                raise RuntimeError(f"step {step.step_id} returned an artifact role inconsistent with its output slot")
            artifacts.update(returned)
            outcomes_by_step[step.step_id] = outcome
            outcomes.append(outcome)
            completed.add(step.step_id)
            pending.remove(step)

      sink_step_ids = {
        step.step_id for step in contract.workflow.steps
        if not step.outputs or any(slot.slot_id not in consumed_outputs for slot in step.outputs)
    }
      sink_outcomes = tuple(outcome for outcome in outcomes if outcome.step_id in sink_step_ids)
      published_artifacts = tuple(
        artifact
        for outcome in sink_outcomes
        for artifact in outcome.result.get("published_artifacts", ())
        if isinstance(artifact, Artifact)
    )
      metrics: dict[str, int] = {}
      for outcome in outcomes:
        for name, value in outcome.metrics.items():
            metrics[name] = metrics.get(name, 0) + value
      return WorkflowReport(
        published_artifacts=tuple(PublishedArtifact(role=artifact.role, value=artifact.value) for artifact in published_artifacts),
        recovered_failures=(),
        unresolved_failures=tuple(outcome.failure for outcome in outcomes if outcome.status == StepStatus.FAILED and outcome.failure is not None),
        metrics=metrics,
        provenance={"blueprint_fingerprint": contract.blueprint_fingerprint, "workflow_fingerprint": contract.workflow_fingerprint},
    )


def build(contract: BuildContract, runtime: BuildRuntime | None = None) -> WorkflowReport:
    """Run a frozen workflow while keeping the public MVP entry point synchronous."""
    return asyncio.run(_build(contract, runtime))
