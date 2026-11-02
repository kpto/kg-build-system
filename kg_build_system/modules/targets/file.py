"""Target that writes normalized graph records as JSON Lines."""
from __future__ import annotations

import datetime
import json
import uuid
from dataclasses import dataclass
from typing import Any, ClassVar

from ..._frozen_json import freeze_json
from ...kernel import (
    Artifact,
    ArtifactType,
    CompilationContext,
    DisruptedExecutionContext,
    ExecutionContext,
    ExecutorFactoryContext,
    Input,
    ModuleCompiler,
    ModuleDefinition,
    ModuleReference,
    Publication,
    RuntimeFieldDefinition,
    StepOutcome,
    StepStatus,
    WorkflowContribution,
    WorkflowStep,
)
from ...types.interfaces import canonical_value_text
from ..core import CoreArtifactTypes
from ..interfaces import Module, ModuleRegistrationConfiguration
from .._paths import validate_relative_path
from .._runtime import as_mapping, execution_services, output_name, skipped
from ._relations import (
    artifact_of, input_values, output_path, query, reference,
)

_RECORDS_INPUT = "records"


def _validate_relative_path(value: str) -> None:
    validate_relative_path(value, context="file output path")


def _canonical_property_value(value: Any) -> Any:
    """The canonical form of one property value as it reaches the graph file.

    ``json.dumps`` hands this only the values it cannot encode itself, so the
    JSON scalars are returned untouched and an existing record keeps its bytes.
    The build key is passed here directly before taking its text, so a key that
    is temporal or a ``uuid`` is written in canonical form too. A scalar with a
    canonical text form takes it from the shared mapping; a value outside the
    canonical vocabulary — a ``bytes``, ``Decimal`` or ``timedelta`` the
    boundary refuses — has no form here and raises rather than being quietly
    stringified into the graph.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time, uuid.UUID)):
        return canonical_value_text(value)
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
    """Where the graph file is written, beneath the build output directory.

    ``relative_path`` must stay inside the output directory. The runtime field
    ``relative_path`` may replace it for one build.

    Example:
        ```python
        from kg_build_system.modules import (
            FileModule, FileModuleConfiguration, register_module,
        )

        modules = (
            register_module(
                FileModule, FileModuleConfiguration("graph.jsonl"),
            ),
        )
        ```
    """

    relative_path: str

    def __post_init__(self) -> None:
        validate_relative_path(self.relative_path, context="file output path")


@dataclass(frozen=True)
class FileModule(Module):
    """Write graph records as sorted JSON Lines.

    Registers no publication beyond ``file/write_result``; the file is the
    product. ``FileModuleConfiguration`` names its location.

    Example:
        ```python
        from kg_build_system.modules import (
            FileModule, FileModuleConfiguration, register_module,
        )

        modules = (
            register_module(
                FileModule, FileModuleConfiguration("graph.jsonl"),
            ),
        )
        ```
    """

    configuration: FileModuleConfiguration

    ID: ClassVar[str] = "file"
    VERSION: ClassVar[str] = "1"
    CONFIGURATION_TYPE: ClassVar[type[FileModuleConfiguration]] = (
        FileModuleConfiguration
    )

    @classmethod
    async def create_compiler(
        cls, context: CompilationContext[Any],
    ) -> ModuleCompiler:
        return cls(context.configuration)

    @classmethod
    def create_executor(cls, context: ExecutorFactoryContext) -> Any:
        return FileExecutor(as_mapping(
            context.runtime_configuration, context="file runtime configuration",
        ))

    async def compile(
        self, context: CompilationContext[Any],
    ) -> WorkflowContribution:
        """Compile this module's stages into a workflow contribution.

        Example:
            ```python
            contribution = await module.compile(context)
            ```
        """
        step = WorkflowStep(
            inputs=(Input(ArtifactType("core", "graph.*"), name=_RECORDS_INPUT),),
            outputs=(
                Publication(ArtifactType(self.ID, "write_result"), name="result"),
            ),
            name="write",
            assembly_preference="deferred",
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
        return WorkflowContribution(definition, (step,))


class FileExecutor:
    """Write every graph-record relation the step receives, in one pass."""

    def __init__(self, configuration: Any) -> None:
        self._configuration = dict(as_mapping(
            configuration, context="file runtime configuration",
        ))

    def _relative_path(self, context: ExecutionContext) -> str:
        compiled = as_mapping(
            context.module.reference.configuration,
            context="file compiled configuration",
        )
        configured_path = compiled.get("relative_path")
        if not isinstance(configured_path, str):
            raise RuntimeError(
                "file module requires a compiled relative output path"
            )
        runtime_path = self._configuration.get("relative_path")
        relative_path = runtime_path if runtime_path is not None else configured_path
        if not isinstance(relative_path, str):
            raise TypeError("runtime file output path must be a string")
        validate_relative_path(relative_path, context="file output path")
        return relative_path

    def handle(self, context: ExecutionContext, services: Any = None) -> StepOutcome:
        services = execution_services(context, services)
        relative_path = self._relative_path(context)
        path = output_path(services, relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        node_count = 0
        edge_count = 0
        with path.open("w", encoding="utf-8") as stream:
            for contribution in input_values(context, _RECORDS_INPUT):
                artifact = artifact_of(contribution)
                if artifact is None:
                    continue
                identity = CoreArtifactTypes.graph_record_identity(artifact.type)
                if identity is None:
                    continue

                relation = reference(services, artifact.value)
                result = query(services, f"SELECT * FROM {relation}")
                columns = tuple(column[0] for column in result.description)
                while batch := result.fetchmany(1_000):
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
            "location": str(path),
        }
        output = context.step.outputs[0]
        artifact = Artifact(output_name(output), output.type, summary)
        return StepOutcome(
            step_id=context.step_id,
            module_id=context.module_id,
            status=StepStatus.SUCCEEDED,
            artifacts=(artifact,),
        )

    def handle_disrupted(
        self, context: DisruptedExecutionContext, services: Any = None,
    ) -> StepOutcome:
        return skipped(context)


__all__ = [
    "FileExecutor", "FileModule", "FileModuleConfiguration",
]
