"""Execute frozen workflow contracts through importable workflow modules."""
from __future__ import annotations

import asyncio
import importlib
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from ..compile.models import ArtifactRole, BuildContract, ModuleDefinition, WorkflowStep


@dataclass(frozen=True)
class BuildRuntime:
    credentials: dict[str, str] = field(default_factory=dict)
    module_configuration: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass(frozen=True)
class Artifact:
    role: ArtifactRole
    value: Any


@dataclass(frozen=True)
class ModuleExecutionContext:
    contract: BuildContract
    module: ModuleDefinition
    inputs: Mapping[str, tuple[Artifact, ...]]
    services: Mapping[str, Any]


@dataclass(frozen=True)
class BuildReport:
    nodes: int
    edges: int
    diagnostics: tuple[str, ...]
    provenance: dict[str, Any]


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
        executors[reference.module_id] = await cls.create_runtime(configuration)
    output_owner = {slot.slot_id: (step, slot) for step in contract.workflow.steps for slot in step.outputs}
    incoming: dict[str, list[str]] = defaultdict(list)
    for connection_def in contract.workflow.connections:
        incoming[connection_def.input_slot_id].append(connection_def.output_slot_id)
    completed: set[str] = set(); artifacts: dict[str, Artifact] = {}; results: list[Any] = []
    pending = list(contract.workflow.steps)
    while pending:
        ready = [step for step in pending if all(output_owner[output_slot_id][0].step_id in completed for output_slot_id in (slot for input_slot in step.inputs for slot in incoming[input_slot.slot_id]))]
        if not ready:
            raise RuntimeError("workflow has a dependency cycle")
        for step in ready:
            inputs = {input_slot.slot_id: tuple(artifacts[slot] for slot in incoming[input_slot.slot_id]) for input_slot in step.inputs}
            value = await executors[step.module_id].execute_step(ModuleExecutionContext(contract, definitions[step.module_id], inputs, {"duckdb": connection}), step)
            if len(step.outputs) == 1:
                artifacts[step.outputs[0].slot_id] = Artifact(step.outputs[0].artifact_role, value)
            elif step.outputs:
                if not isinstance(value, Mapping): raise RuntimeError(f"step {step.step_id} must return output-slot values")
                for slot in step.outputs: artifacts[slot.slot_id] = Artifact(slot.artifact_role, value[slot.slot_id])
            results.append(value); completed.add(step.step_id); pending.remove(step)
    file_results = [result for result in results if isinstance(result, dict) and "nodes" in result and "edges" in result]
    nodes = sum(result["nodes"] for result in file_results); edges = sum(result["edges"] for result in file_results)
    return BuildReport(nodes=nodes, edges=edges, diagnostics=(), provenance={"blueprint_fingerprint": contract.blueprint_fingerprint, "workflow_fingerprint": contract.workflow_fingerprint, "workflow": contract.workflow.model_dump(mode="json")})


def build(contract: BuildContract, runtime: BuildRuntime | None = None) -> BuildReport:
    """Run a frozen workflow while keeping the public MVP entry point synchronous."""
    return asyncio.run(_build(contract, runtime))
