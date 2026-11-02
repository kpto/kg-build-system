"""Workflow module that describes the effective topology as JSON and HTML."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, ClassVar

from ....._frozen_json import freeze_json
from .....kernel import (
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
    StepOutcome,
    StepStatus,
    WorkflowContribution,
    WorkflowStep,
)
from ....internal.module import Module, ModuleRegistrationConfiguration
from ..._paths import validate_relative_path
from ..._runtime import as_mapping, execution_services, output_name, skipped
from .._blueprint import blueprint_from_context
from .._relations import output_path
from .document import build_document
from .ir import (
    MetaGraphDocumentIR,
    decode_meta_graph_instruction,
    encode_meta_graph_instruction,
)
from .observation import (
    Observed as _Observed,
    _canonical_example_value,
    _example_order_key,
    _inclusive_records,
    _inclusive_values,
    _observe,
    _ordered_examples,
    observed_components as _observed_components,
)
from .render import render
from .topology import component_entries

_MODULE_ID = "meta_graph"

_RECORDS_INPUT = "records"

# The step name doubles as the key its instruction is stored under in variables.
_DOCUMENT_STEP_NAME = "document"

# Count column for the aggregate observation query, kept for the module's
# historical surface; the observation module owns the value.
_TOTAL_COLUMN = "_kg_example_count"


def _document(
    instruction: MetaGraphDocumentIR,
    observed: dict[tuple[str, str], _Observed],
    location: str,
) -> dict[str, Any]:
    """The legacy assembly entry point, kept beside the module that owns it."""
    return build_document(
        instruction, observed, location,
        module_id=_MODULE_ID, module_version=MetaGraphModule.VERSION,
    )


@dataclass(frozen=True)
class MetaGraphModuleConfiguration(ModuleRegistrationConfiguration):
    """Where the document lands, and how much of the data it may quote.

    ``example_limit`` bounds the example values quoted per property;
    ``include_html`` also writes a self-contained page at
    ``html_relative_path``. Both paths stay beneath the build output directory.

    Example:
        ```python
        from kg_build_system.modules import (
            MetaGraphModule, MetaGraphModuleConfiguration, register_module,
        )

        modules = (
            register_module(
                MetaGraphModule,
                MetaGraphModuleConfiguration(example_limit=5),
            ),
        )
        ```
    """

    relative_path: str = "meta_graph.json"
    example_limit: int = 3
    include_html: bool = True
    html_relative_path: str = "meta_graph.html"

    def __post_init__(self) -> None:
        validate_relative_path(
            self.relative_path, context="meta-graph document path",
        )
        validate_relative_path(
            self.html_relative_path, context="meta-graph HTML path",
        )
        if self.example_limit < 0:
            raise ValueError("meta-graph example limit may not be negative")


@dataclass(frozen=True)
class MetaGraphModule(Module):
    """Write the effective-topology document and optional HTML page.

    The document quotes at most ``example_limit`` values per property;
    ``MetaGraphModuleConfiguration`` controls both output paths and the page.

    Example:
        ```python
        from kg_build_system.modules import (
            MetaGraphModule, MetaGraphModuleConfiguration, register_module,
        )

        modules = (
            register_module(
                MetaGraphModule,
                MetaGraphModuleConfiguration(example_limit=3),
            ),
        )
        ```
    """

    configuration: MetaGraphModuleConfiguration

    ID: ClassVar[str] = _MODULE_ID
    VERSION: ClassVar[str] = "2"
    CONFIGURATION_TYPE: ClassVar[
        type[MetaGraphModuleConfiguration]
    ] = MetaGraphModuleConfiguration

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
        return MetaGraphExecutor()

    async def compile(
        self, context: CompilationContext[Any],
    ) -> WorkflowContribution:
        """Compile this module's stages into a workflow contribution.

        Example:
            ```python
            contribution = await module.compile(context)
            ```
        """
        entries = component_entries(blueprint_from_context(context))
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
        )
        step = WorkflowStep(
            inputs=(Input(ArtifactType("core", "graph.*"), name=_RECORDS_INPUT),),
            outputs=(
                Publication(
                    ArtifactType(self.ID, "meta_graph_document"), name="result",
                ),
            ),
            name=_DOCUMENT_STEP_NAME,
            assembly_preference="deferred",
        )
        instruction = encode_meta_graph_instruction(MetaGraphDocumentIR(
            relative_path=self.configuration.relative_path,
            example_limit=self.configuration.example_limit,
            include_html=self.configuration.include_html,
            html_relative_path=self.configuration.html_relative_path,
            components=entries,
        ))
        return WorkflowContribution(
            definition,
            (step,),
            freeze_json({"instructions": {_DOCUMENT_STEP_NAME: instruction}}),
        )


class MetaGraphExecutor:
    """Measure the received records and write the document and optional page."""

    def handle(self, context: ExecutionContext, services: Any = None) -> StepOutcome:
        services = execution_services(context, services)
        instruction = decode_meta_graph_instruction(
            self._instruction(context),
        )
        # The path came from a serialized contract, so re-check it cannot escape.
        validate_relative_path(
            instruction.relative_path, context="meta-graph document path",
        )
        path = output_path(services, instruction.relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        document = build_document(
            instruction,
            _observed_components(context, instruction, services),
            str(path),
            module_id=_MODULE_ID,
            module_version=self._module_version(context),
        )

        html_path = None
        if instruction.include_html:
            validate_relative_path(
                instruction.html_relative_path, context="meta-graph HTML path",
            )
            html_path = output_path(services, instruction.html_relative_path)
            # Recorded before either file is written, so the JSON on disk and
            # the copy embedded in the page name the same pair.
            document["summary"]["html_location"] = str(html_path)

        path.write_text(
            # Examples are canonicalised as they are observed, so nothing here
            # should need the hook. It stays as the fail-closed last line: a
            # value that reached the document without a canonical form is a bug,
            # and ``default=str`` would have hidden it behind a spelling the file
            # target never writes.
            json.dumps(
                document, sort_keys=True, indent=2,
                default=_canonical_example_value, allow_nan=False,
            ) + "\n",
            encoding="utf-8",
        )

        if html_path is not None:
            html_path.parent.mkdir(parents=True, exist_ok=True)
            html_path.write_text(render(document), encoding="utf-8")

        output = context.step.outputs[0]
        artifact = Artifact(
            output_name(output), output.type, dict(document["summary"]),
        )
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

    @staticmethod
    def _instruction(context: ExecutionContext) -> Any:
        variables = as_mapping(
            context.variables, context="meta-graph module variables",
        )
        instructions = as_mapping(
            variables.get("instructions"), context="meta-graph instructions",
        )
        return instructions[context.step.name]

    @staticmethod
    def _module_version(context: ExecutionContext) -> str:
        return (
            context.module.reference.implementation_version
            or MetaGraphModule.VERSION
        )


__all__ = [
    "MetaGraphExecutor",
    "MetaGraphModule",
    "MetaGraphModuleConfiguration",
]
