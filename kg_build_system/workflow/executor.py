"""Execute frozen workflow contracts through importable workflow modules."""
from __future__ import annotations

import asyncio
import importlib
import json
import logging
from collections import defaultdict
from contextlib import ExitStack
from dataclasses import asdict, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Literal, cast

from .ir import WorkflowContractIR
from .mapping import workflow_from_ir
from .models import Artifact, BuildRuntime, ContinuableInput, DisruptedExecutionContext, DisruptingInput, ExecutionContext, ExecutorFactoryContext, Failure, PublishedArtifact, StepOutcome, StepStatus, WorkflowArtifactRoles, WorkflowReport
from .monitor import (
    NullWorkflowMonitor, RichWorkflowMonitor, WorkflowExecutionMonitor,
)
from .services import ExecutionServices, LocalTemporaryStorage, LocalWorkingStorage, MappingCredentialResolver


_LOGGER = logging.getLogger("kg_build_system.workflow.execution")
_LOGGER.addHandler(logging.NullHandler())
_DUCKDB_BUILD_DATABASE = "kg_build_memory"


class _MonitorLogger:
    def __init__(
        self, monitor: WorkflowExecutionMonitor, *,
        module_id: str | None = None, step_id: str | None = None,
    ) -> None:
        self._monitor = monitor
        self._module_id = module_id
        self._step_id = step_id

    def debug(self, message: str, *args: object) -> None:
        self._emit(logging.DEBUG, message, args)

    def info(self, message: str, *args: object) -> None:
        self._emit(logging.INFO, message, args)

    def warning(self, message: str, *args: object) -> None:
        self._emit(logging.WARNING, message, args)

    def error(self, message: str, *args: object) -> None:
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


def _resolve_monitor(
    monitor: WorkflowExecutionMonitor | bool | None,
) -> WorkflowExecutionMonitor:
    if monitor is False:
        return NullWorkflowMonitor()
    if monitor is not None and monitor is not True:
        return monitor
    rich_monitor = RichWorkflowMonitor()
    if monitor is True or rich_monitor.console.is_terminal:
        return rich_monitor
    return NullWorkflowMonitor()


def _load_class(import_module: str, qualname: str) -> type[Any]:
    value: Any = importlib.import_module(import_module)
    for part in qualname.split("."):
        value = getattr(value, part)
    return value


def _runtime_value_matches(value: Any, value_type: str) -> bool:
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
    module: Any, configuration: dict[str, Any],
) -> None:
    fields = {field.key: field for field in module.runtime_fields}
    unknown = sorted(set(configuration) - set(fields))
    if unknown:
        raise ValueError(
            f"unknown runtime configuration for {module.reference.module_id}: "
            + ", ".join(unknown)
        )
    missing = sorted(
        key for key, field in fields.items()
        if field.required and key not in configuration
    )
    if missing:
        raise ValueError(
            f"missing runtime configuration for {module.reference.module_id}: "
            + ", ".join(missing)
        )
    invalid = sorted(
        key for key, value in configuration.items()
        if not _runtime_value_matches(value, fields[key].value_type)
    )
    if invalid:
        raise TypeError(
            f"invalid runtime configuration for {module.reference.module_id}: "
            + ", ".join(invalid)
        )


def _configure_duckdb(
    connection: Any, runtime: BuildRuntime, temporary_directory: Path,
) -> None:
    """Configure bounded, compressed in-memory storage for one build."""
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
        "SET temp_directory = ?", [temporary_directory.resolve().as_posix()]
    )
    compression = " (COMPRESS)" if runtime.duckdb_compression else ""
    connection.execute(
        f"ATTACH ':memory:' AS {_DUCKDB_BUILD_DATABASE}{compression}"
    )
    connection.execute(f"USE {_DUCKDB_BUILD_DATABASE}")


async def _build(
    contract: WorkflowContractIR, runtime: BuildRuntime,
    monitor: WorkflowExecutionMonitor,
) -> WorkflowReport:
    try:
        import duckdb
    except ImportError as error:
        raise RuntimeError("DuckDB is required to execute builds") from error
    connection = duckdb.connect()
    workflow = workflow_from_ir(contract.workflow)

    working_directory = runtime.working_directory or runtime.output_directory
    with ExitStack() as resources:
      temporary_directory = resources.enter_context(
          TemporaryDirectory(dir=runtime.temporary_directory)
      )
      resources.callback(connection.close)
      _configure_duckdb(connection, runtime, Path(temporary_directory))
      services = ExecutionServices(
          duckdb=connection,
          output_storage=LocalWorkingStorage(runtime.output_directory),
          working_storage=LocalWorkingStorage(working_directory),
          temporary_storage=LocalTemporaryStorage(Path(temporary_directory)),
          credentials=MappingCredentialResolver(runtime.credentials),
          logger=_MonitorLogger(monitor),
          duckdb_compression=runtime.duckdb_compression,
      )
      executors: dict[str, Any] = {}
      definitions = {module.reference.module_id: module for module in workflow.modules}
      for module in workflow.modules:
        reference = module.reference
        cls = _load_class(reference.import_module, reference.class_qualname)
        if getattr(cls, "ID", None) != reference.module_id:
            raise RuntimeError(f"module import does not provide {reference.module_id!r}")
        runtime_version = getattr(cls, "VERSION", None)
        if str(runtime_version) != reference.implementation_version:
            raise RuntimeError(
                f"module {reference.module_id!r} implementation version "
                f"{runtime_version!r} does not match compiled version "
                f"{reference.implementation_version!r}"
            )
        configuration = runtime.module_configuration.get(reference.module_id, {})
        _validate_runtime_configuration(module, configuration)
        module_services = replace(
            services,
            logger=_MonitorLogger(
                monitor, module_id=reference.module_id,
            ),
        )
        factory_context = ExecutorFactoryContext(
            module, configuration, module_services,
        )
        executors[reference.module_id] = await cls.create_executor(factory_context)

      output_owner = {slot.slot_id: step.step_id for step in workflow.steps for slot in step.outputs}
      incoming: dict[str, list[str]] = defaultdict(list)
      for workflow_connection in workflow.connections:
        incoming[workflow_connection.input_slot_id].append(workflow_connection.output_slot_id)

      completed: set[str] = set()
      artifacts: dict[str, Artifact] = {}
      outcomes_by_step: dict[str, StepOutcome] = {}
      active_failures_by_step: dict[str, set[Failure]] = {}
      outcomes: list[StepOutcome] = []
      pending = list(workflow.steps)
      while pending:
        ready = [step for step in pending if all(output_owner[slot_id] in completed for input_slot in step.inputs for slot_id in incoming[input_slot.slot_id])]
        if not ready:
            raise RuntimeError("workflow has a dependency cycle")
        for step in ready:
            detail = (
                f"Processing {len(step.inputs)} input slot(s) → "
                f"{len(step.outputs)} output slot(s)"
            )
            monitor.step_started(step, detail)
            step_services = replace(
                services,
                logger=_MonitorLogger(
                    monitor, module_id=step.module_id, step_id=step.step_id,
                ),
            )
            step_services.logger.info("Started: %s", detail)
            inputs = {}
            disruptions: list[DisruptingInput] = []
            inherited_failures: set[Failure] = set()
            for input_slot in step.inputs:
                contributions: list[ContinuableInput | DisruptingInput] = []
                for output_slot_id in incoming[input_slot.slot_id]:
                    owner = output_owner[output_slot_id]
                    previous = outcomes_by_step[owner]
                    inherited_failures.update(active_failures_by_step[owner])
                    artifact = artifacts.get(output_slot_id)
                    if previous.status in {StepStatus.SUCCEEDED, StepStatus.WARNING}:
                        contributions.append(ContinuableInput(
                            output_slot_id,
                            cast(Literal[StepStatus.SUCCEEDED, StepStatus.WARNING], previous.status),
                            artifact,
                        ))
                    else:
                        disruption = DisruptingInput(
                            output_slot_id,
                            cast(Literal[StepStatus.FAILED, StepStatus.SKIPPED], previous.status),
                            artifact,
                            previous.failure,
                        )
                        contributions.append(disruption)
                        disruptions.append(disruption)
                inputs[input_slot.slot_id] = tuple(contributions)
            try:
                if disruptions:
                    context = DisruptedExecutionContext(definitions[step.module_id], step, runtime.module_configuration.get(step.module_id, {}), inputs, tuple(disruptions), step_services)
                    outcome = await executors[step.module_id].handle_disrupted(context)
                else:
                    continuable_inputs = {slot_id: tuple(item for item in values if isinstance(item, ContinuableInput)) for slot_id, values in inputs.items()}
                    context = ExecutionContext(definitions[step.module_id], step, runtime.module_configuration.get(step.module_id, {}), continuable_inputs, step_services)
                    outcome = await executors[step.module_id].handle(context)
            except Exception as error:
                step_services.logger.error(
                    "%s: %s", type(error).__name__, error,
                )
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
            if outcome.status == StepStatus.FAILED:
                active_failures_by_step[step.step_id] = inherited_failures | {
                    outcome.failure
                } if outcome.failure is not None else inherited_failures
            elif outcome.status == StepStatus.SKIPPED:
                active_failures_by_step[step.step_id] = inherited_failures
            else:
                active_failures_by_step[step.step_id] = set()
            outcomes.append(outcome)
            completed.add(step.step_id)
            pending.remove(step)
            outcome_detail = f"{outcome.status.value}; {len(outcome.artifacts)} artifact(s)"
            if outcome.failure is not None:
                outcome_detail += f" — {outcome.failure.message}"
            monitor.step_finished(outcome, outcome_detail)
            if outcome.status == StepStatus.FAILED:
                step_services.logger.error("Finished: %s", outcome_detail)
            elif outcome.status == StepStatus.WARNING:
                step_services.logger.warning("Finished: %s", outcome_detail)
            else:
                step_services.logger.info("Finished: %s", outcome_detail)

      published_artifacts = tuple(
        artifact
        for outcome in outcomes
        for artifact in outcome.artifacts
        if WorkflowArtifactRoles.is_published(artifact.role)
    )
      producer_steps = {
          output_owner[connection.output_slot_id]
          for connection in workflow.connections
      }
      sink_steps = {
          step.step_id for step in workflow.steps
          if step.step_id not in producer_steps
      }
      unresolved = set().union(
          *(active_failures_by_step[step_id] for step_id in sink_steps),
      ) if sink_steps else set()
      all_failures = tuple(
          outcome.failure for outcome in outcomes if outcome.failure is not None
      )
      provenance = (
          dict(contract.provenance)
          if isinstance(contract.provenance, dict)
          else {"contract": contract.provenance}
      )
      provenance["workflow_fingerprint"] = contract.workflow_fingerprint
      return WorkflowReport(
        published_artifacts=tuple(PublishedArtifact(role=artifact.role, value=artifact.value) for artifact in published_artifacts),
        recovered_failures=tuple(failure for failure in all_failures if failure not in unresolved),
        unresolved_failures=tuple(failure for failure in all_failures if failure in unresolved),
        provenance=provenance,
    )


def build(
    contract: WorkflowContractIR, runtime: BuildRuntime | None = None, *,
    output_directory: str | Path | None = None,
    working_directory: str | Path | None = None,
    temporary_directory: str | Path | None = None,
    monitor: WorkflowExecutionMonitor | bool | None = None,
) -> WorkflowReport:
    """Run a frozen workflow and persist its contract and report.

    Rich monitoring is enabled automatically on an interactive terminal. Pass
    ``monitor=True`` to force it, ``False`` to disable it, or provide a custom
    :class:`WorkflowExecutionMonitor` implementation.
    """
    configured = runtime or BuildRuntime()
    resolved_output = Path(output_directory) if output_directory is not None else configured.output_directory
    resolved_working = Path(working_directory) if working_directory is not None else configured.working_directory
    resolved_temporary = Path(temporary_directory) if temporary_directory is not None else configured.temporary_directory
    configured = replace(
        configured,
        output_directory=resolved_output,
        working_directory=resolved_working or resolved_output,
        temporary_directory=resolved_temporary,
    )
    configured.output_directory.mkdir(parents=True, exist_ok=True)
    assert configured.working_directory is not None
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
        report = asyncio.run(_build(contract, configured, execution_monitor))
    except Exception as error:
        execution_monitor.log(
            "ERROR", f"Workflow execution stopped: {type(error).__name__}: {error}",
        )
        raise
    finally:
        execution_monitor.stop()
    (configured.output_directory / "build_report.json").write_text(
        json.dumps(
            asdict(report), indent=2, sort_keys=True,
            default=lambda item: item.model_dump(mode="json") if hasattr(item, "model_dump") else str(item),
        ),
        encoding="utf-8",
    )
    return report
