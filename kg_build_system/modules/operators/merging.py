"""Workflow operator that merges compatible facts by graph identity."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from ..._frozen_json import freeze_json
from ...workflow.models import (
    Artifact, DisruptedExecutionContext, ExecutionContext,
    ExecutorFactoryContext, Input, ModuleDefinition, ModuleReference, Output,
    StepOutcome, StepStatus, WorkflowContribution, WorkflowStep,
)
from ...compile.interfaces import CompilationContext, ModuleCompiler
from ...modules.interfaces import Module, ModuleRegistrationConfiguration
from ...workflow.identity import output_name
from ...workflow.interfaces import ModuleExecutor
from ..core import CoreArtifactTypes, graph_record_components


@dataclass(frozen=True)
class _Configuration(ModuleRegistrationConfiguration):
    """The operator has no configurable behavior."""


_RECORDS_INPUT = "records"
_MERGED_OUTPUT = "merged"


def _quote_identifier(value: object) -> str:
    return str(value).replace('"', '""')


@dataclass(frozen=True)
class MergeCompatibleFactsModule(Module):
    configuration: _Configuration
    ID: ClassVar[str] = "merge_compatible_facts"
    VERSION: ClassVar[str] = "1"
    CONFIGURATION_TYPE: ClassVar[type[_Configuration]] = _Configuration

    @classmethod
    async def create_compiler(
        cls, context: CompilationContext[Any],
    ) -> ModuleCompiler:
        return cls(context.configuration)

    @classmethod
    def create_executor(
        cls, context: ExecutorFactoryContext,
    ) -> ModuleExecutor:
        return _Executor()

    async def compile(
        self, context: CompilationContext[Any],
    ) -> WorkflowContribution:
        steps: list[WorkflowStep] = []
        instructions: dict[str, Any] = {}
        for component in graph_record_components(context.blueprint):
            records_type = CoreArtifactTypes.graph_records(
                component.kind, component.name
            )
            fields = [prop.name for prop in component.properties]
            if component.kind == "edge":
                fields = ["source_build_key", "target_build_key", *fields]
            aggregates = [
                f'min("{_quote_identifier(name)}") AS "{_quote_identifier(name)}"'
                for name in fields
            ]
            select = ", ".join(['"build_key"', *aggregates])
            steps.append(WorkflowStep(
                inputs=(Input(records_type, _RECORDS_INPUT),),
                outputs=(Output(records_type, _MERGED_OUTPUT),),
                name=component.name,
            ))
            instructions[component.name] = {
                "relation": f"kg_normalised_{component.name.lower()}",
                "select": select,
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


class _Executor(ModuleExecutor):
    def handle(self, context: ExecutionContext) -> StepOutcome:
        instructions = context.variables["instructions"][context.step.name]
        if not isinstance(instructions, dict):
            raise ValueError("fact merging requires an object instruction")

        input_relation = next(
            (
                item.artifact.value
                for item in context.inputs[_RECORDS_INPUT]
                if item.artifact is not None
            ),
            None,
        )
        if input_relation is None:
            return StepOutcome(
                step_id=context.step_id,
                module_id=context.module_id,
                status=StepStatus.SUCCEEDED,
            )

        source = context.services.relations.reference(input_relation)
        relation = context.services.relations.materialize(
            str(instructions["relation"]),
            f'SELECT {instructions["select"]} FROM {source} GROUP BY "build_key"',
        )

        outputs = {output_name(given): given for given in context.step.outputs}
        artifact = Artifact(
            _MERGED_OUTPUT, outputs[_MERGED_OUTPUT].type, relation,
        )
        return StepOutcome(
            step_id=context.step_id,
            module_id=context.module_id,
            status=StepStatus.SUCCEEDED,
            artifacts=(artifact,),
        )

    def handle_disrupted(
        self, context: DisruptedExecutionContext,
    ) -> StepOutcome:
        return super().handle_disrupted(context)
