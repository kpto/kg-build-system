"""File-output workflow contributor and runtime module."""
from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from ..compile.models import ArtifactRole, CollectionInputSlot, CompiledModule, ModuleReference, OutputSlot, RuntimeFieldDefinition, WorkflowStep
from .workflow import ModuleDeclarationDraft, WorkflowStepDraft, role_is


@dataclass(frozen=True)
class FileModule:
    """Author-facing file-output workflow module declaration."""
    location: str

    @property
    def module_class(self) -> type[FileRuntime]:
        return FileRuntime

    async def declare(self, _context: Any) -> ModuleDeclarationDraft:
        record_input = CollectionInputSlot(slot_id="file::write.records")
        diagnostic_input = CollectionInputSlot(slot_id="file::write.diagnostics")
        step = WorkflowStep(
            step_id="file::write",
            module_id="file",
            assembly_preference="deferred",
            inputs=(record_input, diagnostic_input),
            outputs=(OutputSlot(slot_id="file::write.result", artifact_role=ArtifactRole(namespace="file", name="result")),),
            payload={"location": self.location},
        )
        return ModuleDeclarationDraft(
            module=CompiledModule(
                reference=ModuleReference(module_id="file", import_module=__name__, class_qualname="FileRuntime", implementation_version="1", priority=100),
                runtime_fields=(RuntimeFieldDefinition(key="output_location", description="Optional runtime replacement for the output location.", required=False),),
            ),
            steps=(WorkflowStepDraft(step, {
                record_input.slot_id: lambda _input, output: output.artifact_role.namespace == "core" and output.artifact_role.name.startswith("graph.records."),
                diagnostic_input.slot_id: lambda _input, output: output.artifact_role.namespace == "core" and output.artifact_role.name.startswith("diagnostic."),
            }),),
        )


class FileRuntime:
    ID: ClassVar[str] = "file"

    def __init__(self, configuration: Mapping[str, Any]) -> None:
        self._configuration = configuration

    @classmethod
    async def create_runtime(cls, configuration: Mapping[str, Any]) -> FileRuntime:
        return cls(configuration)

    async def execute_step(self, context: Any, step: WorkflowStep) -> dict[str, Any]:
        location = str(self._configuration.get("output_location") or (step.payload or {})["location"])
        diagnostics = [item for values in context.inputs.values() for item in values if item.role.name.startswith("diagnostic.")]
        failures = [message for item in diagnostics for message in item.value]
        if failures:
            raise ValueError("graph normalisation failed: " + "; ".join(failures))
        output = Path(location); output.parent.mkdir(parents=True, exist_ok=True)
        connection = context.services["duckdb"]
        nodes = edges = 0
        with output.open("w", encoding="utf-8") as stream:
            for values in context.inputs.values():
                for artifact in values:
                    if not artifact.role.name.startswith("graph.records."):
                        continue
                    result = connection.execute(f'SELECT * FROM "{artifact.value}"')
                    columns = tuple(column[0] for column in result.description)
                    _, _, kind, component = artifact.role.name.split(".", 3)
                    for row in result.fetchall():
                        record = dict(zip(columns, row, strict=True))
                        record.update(build_key=str(record["build_key"]), type=component, kind=kind)
                        nodes += kind == "node"; edges += kind == "edge"
                        stream.write(json.dumps(record, sort_keys=True, default=str) + "\n")
        manifest = output.with_suffix(output.suffix + ".manifest.json")
        manifest.write_text(json.dumps({"nodes": nodes, "edges": edges, "blueprint_fingerprint": context.contract.blueprint_fingerprint, "workflow_fingerprint": context.contract.workflow_fingerprint}, sort_keys=True), encoding="utf-8")
        return {"nodes": nodes, "edges": edges, "location": str(output), "manifest": str(manifest)}
