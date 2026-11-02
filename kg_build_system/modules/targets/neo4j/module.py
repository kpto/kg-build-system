"""Workflow target that writes a Neo4j administrative-import bundle."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from ...._frozen_json import freeze_json
from ....kernel import (
    ArtifactType,
    CompilationContext,
    ExecutorFactoryContext,
    Input,
    ModuleCompiler,
    ModuleDefinition,
    ModuleReference,
    Output,
    Publication,
    RuntimeFieldDefinition,
    WorkflowContribution,
    WorkflowStep,
)
from ...interfaces import Module, ModuleRegistrationConfiguration
from ..._paths import validate_relative_path
from ..._runtime import as_mapping
from .._blueprint import blueprint_from_context
from ...core import CoreArtifactTypes, graph_record_components
from .executor import Neo4jExecutor
from .export import (
    Neo4jComponentExport,
    _ARRAY_ITEM_CAPABILITY,
    _PROPERTY_TYPE_CAPABILITY,
    annotation_label as _annotation_label,
    component_export_type as _component_export_type,
    component_imports,
    component_step_key as _component_step_key,
    component_step_name as _component_step_name,
    component_stem as _component_stem,
    display_logical_type as _display_logical_type,
    id_space as _id_space,
    supports_property as _supports_property,
    validate_properties as _validate_properties,
)
from .ir import (
    Neo4jComponentImportIR,
    Neo4jExportInstructionIR,
    Neo4jScriptInstructionIR,
    decode_neo4j_instruction,
    encode_neo4j_instruction,
)

_MODULE_ID = "neo4j"
_RECORDS_INPUT = "records"
_COMPONENTS_INPUT = "components"
# The step name doubles as the key its instruction is stored under in variables.
_SCRIPT_STEP_NAME = "script"


def _validate_relative_path(value: str, *, context: str) -> None:
    validate_relative_path(value, context=context)


@dataclass(frozen=True)
class Neo4jModuleConfiguration(ModuleRegistrationConfiguration):
    """Where the Neo4j import bundle lands and how the script connects.

    ``relative_directory`` is the bundle directory beneath the build output
    directory, ``script_name`` a Python filename inside it, and
    ``default_database`` the database named by the generated script. The runtime
    field ``relative_directory`` may replace the directory for one build.

    Example:
        ```python
        from kg_build_system.modules import (
            Neo4jModule, Neo4jModuleConfiguration, register_module,
        )

        modules = (
            register_module(
                Neo4jModule,
                Neo4jModuleConfiguration(relative_directory="neo4j-import"),
            ),
        )
        ```
    """

    relative_directory: str = "neo4j-import"
    script_name: str = "import_neo4j.py"
    default_database: str = "neo4j"

    def __post_init__(self) -> None:
        validate_relative_path(
            self.relative_directory, context="Neo4j output directory",
        )
        validate_relative_path(self.script_name, context="Neo4j script name")
        if (
            len(Path(self.script_name).parts) != 1
            or not self.script_name.endswith(".py")
        ):
            raise ValueError("Neo4j script name must be a Python filename")
        if not isinstance(self.default_database, str) or not self.default_database.strip():
            raise ValueError("Neo4j default database must be non-empty")


@dataclass(frozen=True)
class Neo4jModule(Module):
    """Export one Parquet file per component and a Neo4j import script.

    The module refuses property types its import format cannot represent and
    edges whose endpoints are not bound concrete nodes. The bundle is published
    as ``neo4j/import_bundle`` and configured by ``Neo4jModuleConfiguration``.

    Example:
        ```python
        from kg_build_system.modules import (
            Neo4jModule, Neo4jModuleConfiguration, register_module,
        )

        modules = (
            register_module(
                Neo4jModule, Neo4jModuleConfiguration(),
            ),
        )
        ```
    """

    configuration: Neo4jModuleConfiguration

    ID: ClassVar[str] = _MODULE_ID
    VERSION: ClassVar[str] = "2"
    PROPERTY_TYPE_CAPABILITY: ClassVar[frozenset[str]] = _PROPERTY_TYPE_CAPABILITY
    CONFIGURATION_TYPE: ClassVar[type[Neo4jModuleConfiguration]] = (
        Neo4jModuleConfiguration
    )

    @classmethod
    async def create_compiler(
        cls, context: CompilationContext[Any],
    ) -> ModuleCompiler:
        """Create the compiler for this module version.

        Example:
            ```python
            compiler = await MyModule.create_compiler(context)
            ```
        """
        return cls(context.configuration)

    @classmethod
    def create_executor(cls, context: ExecutorFactoryContext) -> Any:
        """Create the executor for this module version.

        Example:
            ```python
            executor = MyModule.create_executor(context)
            ```
        """
        return Neo4jExecutor(as_mapping(
            context.runtime_configuration,
            context="Neo4j runtime configuration",
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
        components = self._component_imports(context)
        definition = ModuleDefinition(
            reference=ModuleReference(
                module_id=self.ID,
                import_module=type(self).__module__,
                class_qualname=type(self).__qualname__,
                implementation_version=self.VERSION,
                configuration=freeze_json({
                    "default_database": self.configuration.default_database,
                    "relative_directory": self.configuration.relative_directory,
                    "script_name": self.configuration.script_name,
                }),
            ),
            runtime_fields=(RuntimeFieldDefinition(
                key="relative_directory",
                description=(
                    "Optional runtime replacement for the Neo4j import-bundle "
                    "directory."
                ),
                required=False,
            ),),
        )
        exports = tuple(
            self._component_export_step(component) for component in components
        )
        instructions = {
            _component_step_name(component): encode_neo4j_instruction(
                Neo4jExportInstructionIR(component=component)
            )
            for component in components
        }
        instructions[_SCRIPT_STEP_NAME] = encode_neo4j_instruction(
            Neo4jScriptInstructionIR(
                components=components,
                script_name=self.configuration.script_name,
                default_database=self.configuration.default_database,
            ),
        )
        return WorkflowContribution(
            definition,
            (*exports, self._script_step()),
            freeze_json({"instructions": instructions}),
        )

    @staticmethod
    def _component_imports(
        context: CompilationContext[Any],
    ) -> tuple[Neo4jComponentImportIR, ...]:
        return component_imports(graph_record_components(
            blueprint_from_context(context),
        ))

    @staticmethod
    def _component_export_step(
        component: Neo4jComponentImportIR,
    ) -> WorkflowStep:
        return WorkflowStep(
            inputs=(Input(
                CoreArtifactTypes.graph_records(
                    component.kind, component.component,
                ),
                name=_RECORDS_INPUT,
            ),),
            outputs=(
                Output(_component_export_type(component), name="result"),
            ),
            name=_component_step_name(component),
            assembly_preference="deferred",
        )

    @staticmethod
    def _script_step() -> WorkflowStep:
        return WorkflowStep(
            inputs=(
                Input(
                    ArtifactType(_MODULE_ID, "component.*"),
                    name=_COMPONENTS_INPUT,
                ),
            ),
            outputs=(
                Publication(
                    ArtifactType(_MODULE_ID, "import_bundle"), name="result",
                ),
            ),
            name=_SCRIPT_STEP_NAME,
            assembly_preference="deferred",
        )


__all__ = [
    "Neo4jComponentExport",
    "Neo4jExecutor",
    "Neo4jModule",
    "Neo4jModuleConfiguration",
]
