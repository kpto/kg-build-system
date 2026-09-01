"""Workflow operator that removes exact duplicate graph records."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from ..._frozen_json import freeze_json, thaw_json
from ...workflow.models import (
    ModuleDefinition, ModuleReference, OutputSlot, SingleInputSlot, WorkflowStep,
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
    role_is,
)
from ..core import CoreArtifactRoles, graph_record_components


@dataclass(frozen=True)
class _Configuration(ModuleRegistrationConfiguration):
    """The operator has no configurable behavior."""


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
        steps: list[WorkflowStepDraft] = []
        for component in graph_record_components(context.blueprint):
            input_slot = SingleInputSlot(
                slot_id=f"{self.ID}::{component.name}.input"
            )
            output_role = CoreArtifactRoles.graph_records(
                component.kind, component.name
            )
            relation = f"kg_distinct_{component.name.lower()}"
            step = WorkflowStep(
                step_id=f"{self.ID}::{component.name}",
                module_id=self.ID,
                inputs=(input_slot,),
                outputs=(
                    OutputSlot(
                        slot_id=f"{self.ID}::{component.name}.output",
                        artifact_role=output_role,
                    ),
                ),
                payload=freeze_json({"relation": relation}),
            )
            steps.append(
                WorkflowStepDraft(
                    definition=step,
                    candidates={input_slot.slot_id: role_is(output_role)},
                )
            )

        definition = ModuleDefinition(
            reference=ModuleReference(
                module_id=self.ID,
                import_module=type(self).__module__,
                class_qualname=type(self).__qualname__,
                implementation_version=self.VERSION,
                configuration=freeze_json({}),
            )
        )
        return WorkflowContribution(definition, tuple(steps))


class _Executor(ModuleExecutor):
    def handle(self, context: ExecutionContext) -> StepOutcome:
        payload = thaw_json(context.step.payload)  # type: ignore[arg-type]
        if not isinstance(payload, dict):
            raise ValueError("deduplication requires an object payload")

        input_relation = next(
            item.artifact.value
            for contributions in context.inputs.values()
            for item in contributions
            if item.artifact is not None
        )
        source = context.services.relations.reference(input_relation)
        relation = context.services.relations.materialize(
            str(payload["relation"]), f"SELECT DISTINCT * FROM {source}",
        )

        output = context.step.outputs[0]
        artifact = Artifact(
            output.slot_id, output.artifact_role, relation
        )
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
