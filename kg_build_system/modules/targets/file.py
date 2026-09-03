"""Workflow module that writes normalized graph records as JSON Lines."""
from __future__ import annotations

import datetime
import json
import uuid
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, ClassVar

from ..._frozen_json import freeze_json, thaw_json
from ...workflow.models import (
    CollectionInputSlot, ModuleDefinition, ModuleReference, OutputSlot,
    RuntimeFieldDefinition, WorkflowStep,
)
from ...compile.interfaces import CompilationContext, ModuleCompiler
from ...modules.interfaces import Module, ModuleRegistrationConfiguration
from ...modules._paths import validate_relative_path
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
    validate_relative_path(value, context="file output path")


def _canonical_property_value(value: Any) -> Any:
    """The canonical form of one property value as it reaches the graph file.

    ``json.dumps`` hands this only the values it cannot encode itself, so the
    JSON scalars are returned untouched and an existing record keeps its bytes.
    The build key is passed here directly before taking its text, so a key that
    is temporal or a ``uuid`` is written in canonical form too.
    The temporal canonicals are written with ``isoformat()``, which keeps the
    ISO-8601 ``T`` separator that ``str()`` replaces with a space, and ``uuid``
    with its hyphenated text. A value outside the canonical vocabulary — a
    ``bytes``, ``Decimal`` or ``timedelta`` the boundary refuses — has no form
    here and raises rather than being quietly stringified into the graph.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    # A datetime is a date, so the three share one test and one canonical form.
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, dict):
        return {
            key: _canonical_property_value(item) for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_canonical_property_value(item) for item in value]
    raise TypeError(
        f"graph property of type {type(value).__qualname__} has no canonical"
        " form in the file target"
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
    def create_executor(
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

    def handle(self, context: ExecutionContext) -> StepOutcome:
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
                                build_key=str(
                                    _canonical_property_value(record["build_key"])
                                ),
                                type=identity.component,
                                kind=identity.kind,
                            )
                            if identity.kind == "node":
                                node_count += 1
                            else:
                                edge_count += 1
                            stream.write(
                                json.dumps(
                                    record,
                                    sort_keys=True,
                                    default=_canonical_property_value,
                                ) + "\n"
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

    def handle_disrupted(
        self, context: DisruptedExecutionContext,
    ) -> StepOutcome:
        return super().handle_disrupted(context)
