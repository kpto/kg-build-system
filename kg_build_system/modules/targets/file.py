"""Workflow module that writes normalized graph records as JSON Lines."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, ClassVar

from ..._frozen_json import freeze_json, thaw_json
from ...workflow.models import (
    CollectionInputSlot, ModuleDefinition, ModuleReference, OutputSlot,
    RuntimeFieldDefinition, WorkflowStep,
)
from ...compile.interfaces import CompilationContext, ModuleCompiler
from ...modules.interfaces import Module, ModuleRegistrationConfiguration
from ...workflow.interfaces import ModuleExecutor
from ...workflow.models import (
    Artifact,
    DisruptedExecutionContext,
    ExecutionContext,
    ExecutorFactoryContext,
    StepOutcome,
    StepStatus,
    WorkflowContribution,
    WorkflowStepDraft,
    WorkflowArtifactRoles,
)
from ..core import CoreArtifactRoles


def _validate_relative_path(value: str) -> None:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(
            "file output path must be relative to the build output directory"
        )


@dataclass(frozen=True)
class FileModuleConfiguration(ModuleRegistrationConfiguration):
    relative_path: str

    def __post_init__(self) -> None:
        _validate_relative_path(self.relative_path)


@dataclass(frozen=True)
class FileModule(Module):
    configuration: FileModuleConfiguration

    ID: ClassVar[str] = "file"
    VERSION: ClassVar[str] = "1"
    CONFIGURATION_TYPE: ClassVar[type[FileModuleConfiguration]] = FileModuleConfiguration

    @classmethod
    async def create_compiler(
        cls, context: CompilationContext[Any],
    ) -> ModuleCompiler:
        return cls(context.configuration)

    @classmethod
    async def create_executor(
        cls, context: ExecutorFactoryContext,
    ) -> ModuleExecutor:
        return FileExecutor(dict(context.runtime_configuration))

    async def compile(
        self, context: CompilationContext[Any],
    ) -> WorkflowContribution:
        records = CollectionInputSlot(slot_id="file::write.records")
        step = WorkflowStep(
            step_id="file::write",
            module_id=self.ID,
            inputs=(records,),
            outputs=(
                OutputSlot(
                    slot_id="file::write.result",
                    artifact_role=WorkflowArtifactRoles.published(
                        self.ID, "write_result"
                    ),
                ),
            ),
            payload=freeze_json({}),
        )
        definition = ModuleDefinition(
            reference=ModuleReference(
                module_id=self.ID,
                import_module=type(self).__module__,
                class_qualname=type(self).__qualname__,
                implementation_version=self.VERSION,
                configuration=freeze_json({
                    "relative_path": self.configuration.relative_path,
                }),
            ),
            runtime_fields=(
                RuntimeFieldDefinition(
                    key="relative_path",
                    description=(
                        "Optional runtime replacement for the relative output path."
                    ),
                    required=False,
                ),
            ),
        )
        candidates = {
            records.slot_id: lambda _input, output: (
                CoreArtifactRoles.is_graph_records(output.artifact_role)
            )
        }
        return WorkflowContribution(
            definition,
            (WorkflowStepDraft(
                definition=step,
                assembly_preference="deferred",
                candidates=candidates,
            ),),
        )


class FileExecutor(ModuleExecutor):
    def __init__(self, configuration: dict[str, Any]) -> None:
        self._configuration = configuration

    def _relative_path(self, context: ExecutionContext) -> str:
        compiled = thaw_json(  # type: ignore[arg-type]
            context.module.reference.configuration
        )
        if not isinstance(compiled, dict):
            raise RuntimeError("file module requires an object configuration")
        configured_path = compiled.get("relative_path")
        if not isinstance(configured_path, str):
            raise RuntimeError("file module requires a compiled relative output path")
        runtime_path = self._configuration.get("relative_path")
        relative_path = runtime_path if runtime_path is not None else configured_path
        if not isinstance(relative_path, str):
            raise TypeError("runtime file output path must be a string")
        _validate_relative_path(relative_path)
        return relative_path

    async def handle(self, context: ExecutionContext) -> StepOutcome:
        relative_path = self._relative_path(context)
        output_path = context.services.output_storage.child(
            PurePosixPath(relative_path)
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        node_count = 0
        edge_count = 0
        with output_path.open("w", encoding="utf-8") as stream:
            for contributions in context.inputs.values():
                for contribution in contributions:
                    artifact = contribution.artifact
                    if artifact is None:
                        continue
                    identity = CoreArtifactRoles.graph_record_identity(artifact.role)
                    if identity is None:
                        continue

                    relation = context.services.relations.reference(artifact.value)
                    query = context.services.relations.query(
                        f"SELECT * FROM {relation}"
                    )
                    columns = tuple(column[0] for column in query.description)
                    while batch := query.fetchmany(1_000):
                        for row in batch:
                            record = dict(zip(columns, row, strict=True))
                            record.update(
                                build_key=str(record["build_key"]),
                                type=identity.component,
                                kind=identity.kind,
                            )
                            if identity.kind == "node":
                                node_count += 1
                            else:
                                edge_count += 1
                            stream.write(
                                json.dumps(record, sort_keys=True, default=str) + "\n"
                            )

        summary = {
            "nodes": node_count,
            "edges": edge_count,
            "location": str(output_path),
        }
        output = context.step.outputs[0]
        artifact = Artifact(output.slot_id, output.artifact_role, summary)
        return StepOutcome(
            context.step.step_id,
            context.step.module_id,
            StepStatus.SUCCEEDED,
            (artifact,),
        )

    async def handle_disrupted(
        self, context: DisruptedExecutionContext,
    ) -> StepOutcome:
        return await super().handle_disrupted(context)
