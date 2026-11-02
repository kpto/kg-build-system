"""Workflow operator that removes exact duplicate graph records."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from ...._frozen_json import freeze_json
from ....compile.internal import ModuleCompiler
from ....kernel import (
    Artifact,
    CompilationContext,
    DisruptedExecutionContext,
    ExecutionContext,
    ExecutorFactoryContext,
    Input,
    ModuleDefinition,
    ModuleReference,
    Output,
    StepOutcome,
    StepStatus,
    WorkflowContribution,
    WorkflowStep,
)
from .._runtime import (
    as_mapping,
    execution_services,
    instruction_payload,
    output_name,
    skipped,
)
from ..core import CoreArtifactTypes, graph_record_components
from ..core.plan import blueprint_from_context
from ...internal.module import Module, ModuleRegistrationConfiguration


@dataclass(frozen=True)
class _Configuration(ModuleRegistrationConfiguration):
    """The operator has no configurable behavior."""


_RECORDS_INPUT = "records"
_DISTINCT_OUTPUT = "distinct"


@dataclass(frozen=True)
class CollapseExactDuplicatesModule(Module):
    """Drop rows identical in every graph-record column.

    A repeated build key whose values differ is left alone. There is no
    configuration, so registration needs no configuration value.

    Example:
        ```python
        from kg_build_system.modules import (
            CollapseExactDuplicatesModule, register_module,
        )

        modules = (register_module(CollapseExactDuplicatesModule),)
        ```
    """

    configuration: _Configuration

    ID: ClassVar[str] = "collapse_exact_duplicates"
    VERSION: ClassVar[str] = "1"
    CONFIGURATION_TYPE: ClassVar[type[_Configuration]] = _Configuration

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
        return _Executor()

    async def compile(self, context: CompilationContext[Any]) -> WorkflowContribution:
        """Compile this module's stages into a workflow contribution.

        Example:
            ```python
            contribution = await module.compile(context)
            ```
        """
        steps: list[WorkflowStep] = []
        instructions: dict[str, Any] = {}
        for component in graph_record_components(blueprint_from_context(context)):
            records_type = CoreArtifactTypes.graph_records(
                component.kind, component.name,
            )
            steps.append(WorkflowStep(
                inputs=(Input(records_type, _RECORDS_INPUT),),
                outputs=(Output(records_type, _DISTINCT_OUTPUT),),
                name=component.name,
            ))
            instructions[component.name] = {
                "relation": f"kg_distinct_{component.name.lower()}",
            }

        definition = ModuleDefinition(
            reference=ModuleReference(
                module_id=self.ID,
                import_module=type(self).__module__,
                class_qualname=type(self).__qualname__,
                implementation_version=self.VERSION,
                configuration=freeze_json({}),
            )
        )
        return WorkflowContribution(
            definition, tuple(steps), freeze_json({"instructions": instructions}),
        )


class _Executor:
    def handle(
        self, context: ExecutionContext, services: Any = None,
    ) -> StepOutcome:
        services = execution_services(context, services)
        instructions = as_mapping(
            instruction_payload(context),
            context="deduplication instruction",
        )
        input_relation = next(
            item.artifact.value
            for item in context.inputs[_RECORDS_INPUT]
            if item.artifact is not None
        )
        source = services.relations.reference(input_relation)
        relation = services.relations.materialize(
            str(instructions["relation"]), f"SELECT DISTINCT * FROM {source}",
        )
        outputs = {output_name(given): given for given in context.step.outputs}
        artifact = Artifact(
            _DISTINCT_OUTPUT, outputs[_DISTINCT_OUTPUT].type, relation,
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


__all__ = ["CollapseExactDuplicatesModule"]
