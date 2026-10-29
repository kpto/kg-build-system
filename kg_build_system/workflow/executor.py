"""Execute frozen workflow contracts through importable workflow modules."""
from __future__ import annotations

import importlib
import json
import logging
from collections import defaultdict
from collections.abc import Mapping
from contextlib import ExitStack
from dataclasses import asdict, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Literal, cast

from pydantic import JsonValue

from .._frozen_json import thaw_json
from .identity import opening_identity, output_name, step_identity
from .ir import WorkflowContractIR
from .mapping import workflow_from_ir
from .models import Artifact, BuildRuntime, DefinedStep, ModuleDefinition, Publication, ContinuableInput, DisruptedExecutionContext, DisruptingInput, ExecutionContext, ExecutorFactoryContext, Failure, PublishedArtifact, StepOutcome, StepStatus, WorkflowReport
from .monitor import (
    NullWorkflowMonitor, RichWorkflowMonitor, WorkflowExecutionMonitor,
)
from ..engines.interfaces import DuckDBRelationService, configure_framework_macros
from .services import (
    ExecutionServices, LocalTemporaryStorage,
    LocalWorkingStorage, MappingCredentialResolver,
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


def _build(
    contract: WorkflowContractIR, runtime: BuildRuntime,
    monitor: WorkflowExecutionMonitor,
) -> WorkflowReport:
    try:
        import duckdb
    except ImportError as error:
        raise RuntimeError("DuckDB is required to execute builds") from error
    workflow = workflow_from_ir(contract.workflow)

    working_directory = runtime.working_directory
    with ExitStack() as resources:
      temporary_directory = resources.enter_context(
          TemporaryDirectory(dir=runtime.temporary_directory)
      )
      if runtime.duckdb_storage == "disk":
          storage_directory = Path(resources.enter_context(
              TemporaryDirectory(
                  prefix=".kg-build-duckdb-", dir=working_directory,
              )
          ))
      else:
          storage_directory = Path(temporary_directory)
      connection = _open_duckdb(duckdb, runtime, storage_directory)
      try:
          _configure_duckdb(connection, runtime, storage_directory)
          time_zone = _effective_duckdb_time_zone(connection)
      except BaseException:
          connection.close()
          raise
      if isinstance(monitor, RichWorkflowMonitor):
          memory_limit, threads = _effective_duckdb_resources(connection)
          monitor.set_duckdb_settings(
              storage=runtime.duckdb_storage,
              compression=runtime.duckdb_compression,
              memory_limit=memory_limit,
              threads=threads,
          )
      relations = DuckDBRelationService(
          connection,
          checkpoint_on_step=(
              runtime.duckdb_compression or runtime.duckdb_storage == "disk"
          ),
      )
      resources.callback(relations.close)
      services = ExecutionServices(
          relations=relations,
          output_storage=LocalWorkingStorage(runtime.output_directory),
          working_storage=LocalWorkingStorage(working_directory),
          temporary_storage=LocalTemporaryStorage(Path(temporary_directory)),
          credentials=MappingCredentialResolver(runtime.credentials),
          logger=_MonitorLogger(monitor),
      )
      executors: dict[str, Any] = {}
      definitions: dict[str, ModuleDefinition] = {}
      module_variables: dict[str, Mapping[str, Any]] = {}
      for contribution in workflow.contributions:
        module = contribution.module
        reference = module.reference
        definitions[reference.module_id] = module
        module_variables[reference.module_id] = (
            dict(thaw_json(contribution.variables))
            if contribution.variables is not None else {}
        )
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
        factory_context = ExecutorFactoryContext(
            module, module_variables[reference.module_id], configuration,
        )
        executors[reference.module_id] = cls.create_executor(factory_context)

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
      for workflow_connection in workflow.connections:
        incoming[workflow_connection.input_id].append(workflow_connection.output_id)

      completed: set[str] = set()
      artifacts: dict[str, Artifact] = {}
      outcomes_by_step: dict[str, StepOutcome] = {}
      active_failures_by_step: dict[str, set[Failure]] = {}
      outcomes: list[StepOutcome] = []
      pending = list(steps)
      while pending:
        ready = [
            entry for entry in pending
            if all(
                output_owner[source] in completed
                for taken in entry[1].inputs
                for source in incoming[opening_identity(
                    identity_of[(entry[0], entry[1].name)], taken.name,
                )]
            )
        ]
        if not ready:
            raise RuntimeError("workflow has a dependency cycle")
        for module_id, step in ready:
            identity = identity_of[(module_id, step.name)]
            detail = (
                f"Processing {len(step.inputs)} input(s) → "
                f"{len(step.outputs)} output(s)"
            )
            monitor.step_started(identity, detail)
            step_services = replace(
                services,
                logger=_MonitorLogger(
                    monitor, module_id=module_id, step_id=identity,
                ),
            )
            step_services.logger.info("Started: %s", detail)
            gathered: dict[str, list[ContinuableInput | DisruptingInput]] = defaultdict(list)
            disruptions: list[DisruptingInput] = []
            inherited_failures: set[Failure] = set()
            for taken in step.inputs:
                for output_id in incoming[opening_identity(identity, taken.name)]:
                    owner = output_owner[output_id]
                    previous = outcomes_by_step[owner]
                    inherited_failures.update(active_failures_by_step[owner])
                    artifact = artifacts.get(output_id)
                    if previous.status in {StepStatus.SUCCEEDED, StepStatus.WARNING}:
                        gathered[taken.input_name].append(ContinuableInput(
                            output_id,
                            cast(Literal[StepStatus.SUCCEEDED, StepStatus.WARNING], previous.status),
                            artifact,
                        ))
                    else:
                        disruption = DisruptingInput(
                            output_id,
                            cast(Literal[StepStatus.FAILED, StepStatus.SKIPPED], previous.status),
                            artifact,
                            previous.failure,
                        )
                        gathered[taken.input_name].append(disruption)
                        disruptions.append(disruption)
            by_input = {name: tuple(values) for name, values in gathered.items()}
            runtime_configuration = runtime.module_configuration.get(module_id, {})
            try:
                if disruptions:
                    context = DisruptedExecutionContext(
                        definitions[module_id], step, module_id, identity,
                        module_variables[module_id], runtime_configuration, by_input,
                        tuple(disruptions),
                    )
                    outcome = executors[module_id].handle_disrupted(context, step_services)
                else:
                    continuable_inputs = {
                        name: tuple(
                            item for item in values if isinstance(item, ContinuableInput)
                        )
                        for name, values in by_input.items()
                    }
                    context = ExecutionContext(
                        definitions[module_id], step, module_id, identity,
                        module_variables[module_id], runtime_configuration,
                        continuable_inputs,
                    )
                    outcome = executors[module_id].handle(context, step_services)
                relations.finish_step()
            except Exception as error:
                step_services.logger.error(
                    "%s: %s", type(error).__name__, error,
                )
                outcome = StepOutcome(
                    step_id=identity,
                    module_id=module_id,
                    status=StepStatus.FAILED,
                    failure=Failure(str(error), module_id, identity, type(error).__name__),
                )
            if outcome.step_id != identity or outcome.module_id != module_id:
                raise RuntimeError(f"module returned an outcome for a different step: {identity}")
            if outcome.status == StepStatus.FAILED and outcome.failure is None:
                raise RuntimeError(f"failed step {identity} did not provide a failure")
            declared = {output.name: output.type for output in step.outputs}
            returned = {artifact.output_name: artifact for artifact in outcome.artifacts}
            if not set(returned) <= set(declared):
                raise RuntimeError(f"step {identity} returned an artifact for an undeclared output")
            if any(artifact.type != declared[name] for name, artifact in returned.items()):
                raise RuntimeError(
                    f"step {identity} returned an artifact type its output does not declare"
                )
            artifacts.update({
                opening_identity(identity, name): artifact
                for name, artifact in returned.items()
            })
            outcomes_by_step[identity] = outcome
            if outcome.status == StepStatus.FAILED:
                active_failures_by_step[identity] = inherited_failures | {
                    outcome.failure
                } if outcome.failure is not None else inherited_failures
            elif outcome.status == StepStatus.SKIPPED:
                active_failures_by_step[identity] = inherited_failures
            else:
                active_failures_by_step[identity] = set()
            outcomes.append(outcome)
            completed.add(identity)
            pending.remove((module_id, step))
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

      published = tuple(
          PublishedArtifact(type=artifact.type, value=artifact.value)
          for artifact in (
              artifacts[output_id] for output_id in publication_ids if output_id in artifacts
          )
      )
      unresolved = set().union(
          *(
              active_failures_by_step[step_id]
              for step_id in publishing_steps
              if step_id in active_failures_by_step
          ),
      ) if publishing_steps else set()
      all_failures = tuple(
          outcome.failure for outcome in outcomes if outcome.failure is not None
      )
      provenance: dict[str, JsonValue] = (
          dict(contract.provenance)
          if isinstance(contract.provenance, dict)
          else {"contract": contract.provenance}
      )
      provenance["workflow_fingerprint"] = contract.workflow_fingerprint
      duckdb_provenance: dict[str, JsonValue] = {"TimeZone": time_zone}
      provenance["duckdb"] = duckdb_provenance
      return WorkflowReport(
        published_artifacts=published,
        recovered_failures=tuple(failure for failure in all_failures if failure not in unresolved),
        unresolved_failures=tuple(failure for failure in all_failures if failure in unresolved),
        provenance=provenance,
    )


def build(
    contract: WorkflowContractIR, runtime: BuildRuntime | None = None, *,
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
    resolved_temporary = Path(temporary_directory) if temporary_directory is not None else configured.temporary_directory
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
            "ERROR", f"Workflow execution stopped: {type(error).__name__}: {error}",
        )
        raise
    else:
        execution_monitor.workflow_finished(report)
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
