"""Workflow operator that removes exact duplicate graph records."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from ...compile.models import (
    ModuleDefinition,
    ModuleReference,
    OutputSlot,
    SingleInputSlot,
    WorkflowStep,
)
from ...workflow.interfaces import (
    CompilationContext,
    Module,
    ModuleCompilationResult,
    ModuleCompiler,
    ModuleExecutor,
    ModuleRegistration,
    ModuleRegistrationConfiguration,
    WorkflowStepDraft,
    role_is,
)
from ...workflow.models import (
    Artifact,
    DisruptedExecutionContext,
    ExecutionContext,
    ExecutorFactoryContext,
    StepOutcome,
    StepStatus,
)
from ..core import CoreArtifactRoles


@dataclass(frozen=True)
class _Configuration(ModuleRegistrationConfiguration):
    """The operator has no configurable behavior."""


def _quote_identifier(value: object) -> str:
    return str(value).replace('"', '""')


@dataclass(frozen=True)
class CollapseExactDuplicatesModule(Module, ModuleRegistration[_Configuration]):
    configuration: _Configuration = field(default_factory=_Configuration)

    ID: ClassVar[str] = "collapse_exact_duplicates"
    VERSION: ClassVar[str] = "1"

    @classmethod
    async def create_compiler(
        cls, context: CompilationContext[Any],
    ) -> ModuleCompiler:
        return cls(context.registration_configuration)

    @classmethod
    async def create_executor(
        cls, context: ExecutorFactoryContext,
    ) -> ModuleExecutor:
        return _Executor()

    async def compile(
        self, context: CompilationContext[Any],
    ) -> ModuleCompilationResult:
        steps: list[WorkflowStepDraft] = []
        for component in context.blueprint.components:
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
                payload={"relation": relation},
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
                priority=0,
                configuration={},
            )
        )
        return ModuleCompilationResult(definition, tuple(steps))


class _Executor(ModuleExecutor):
    async def handle(self, context: ExecutionContext) -> StepOutcome:
        payload = context.step.payload
        if not isinstance(payload, dict):
            raise ValueError("deduplication requires an object payload")

        input_relation = next(
            item.artifact.value
            for contributions in context.inputs.values()
            for item in contributions
            if item.artifact is not None
        )
        relation = _quote_identifier(payload["relation"])
        source = _quote_identifier(input_relation)
        context.services.duckdb.execute(
            f'CREATE TEMP TABLE "{relation}" AS '
            f'SELECT DISTINCT * FROM "{source}"'
        )

        output = context.step.outputs[0]
        artifact = Artifact(
            output.slot_id, output.artifact_role, payload["relation"]
        )
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
