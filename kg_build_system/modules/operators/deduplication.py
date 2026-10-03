"""Workflow operator that removes exact duplicate graph records."""
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
_DISTINCT_OUTPUT = "distinct"


@dataclass(frozen=True)
class CollapseExactDuplicatesModule(Module):
    configuration: _Configuration
    ID: ClassVar[str] = "collapse_exact_duplicates"
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


class _Executor(ModuleExecutor):
    def handle(self, context: ExecutionContext) -> StepOutcome:
        instructions = context.variables["instructions"][context.step.name]
        if not isinstance(instructions, dict):
            raise ValueError("deduplication requires an object instruction")

        input_relation = next(
            item.artifact.value
            for item in context.inputs[_RECORDS_INPUT]
            if item.artifact is not None
        )
        source = context.services.relations.reference(input_relation)
        relation = context.services.relations.materialize(
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
        self, context: DisruptedExecutionContext,
    ) -> StepOutcome:
        return super().handle_disrupted(context)
