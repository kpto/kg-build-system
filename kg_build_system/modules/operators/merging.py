"""Workflow operator that merges compatible facts by graph identity."""
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
from ..core import CoreArtifactRoles


@dataclass(frozen=True)
class _Configuration(ModuleRegistrationConfiguration):
    """The operator has no configurable behavior."""


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
    async def create_executor(
        cls, context: ExecutorFactoryContext,
    ) -> ModuleExecutor:
        return _Executor()

    async def compile(
        self, context: CompilationContext[Any],
    ) -> WorkflowContribution:
        steps: list[WorkflowStepDraft] = []
        for component in context.blueprint.components:
            input_slot = SingleInputSlot(
                slot_id=f"{self.ID}::{component.name}.input"
            )
            output_role = CoreArtifactRoles.graph_records(
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
            relation = f"kg_normalised_{component.name.lower()}"
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
                payload=freeze_json({"relation": relation, "select": select}),
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
    async def handle(self, context: ExecutionContext) -> StepOutcome:
        payload = thaw_json(context.step.payload)  # type: ignore[arg-type]
        if not isinstance(payload, dict):
            raise ValueError("fact merging requires an object payload")

        input_relation = next(
            (
                item.artifact.value
                for contributions in context.inputs.values()
                for item in contributions
                if item.artifact is not None
            ),
            None,
        )
        if input_relation is None:
            return StepOutcome(
                context.step.step_id,
                context.step.module_id,
                StepStatus.SUCCEEDED,
            )

        relation = _quote_identifier(payload["relation"])
        source = _quote_identifier(input_relation)
        context.services.duckdb.execute(
            f'CREATE TABLE "{relation}" AS '
            f'SELECT {payload["select"]} FROM "{source}" GROUP BY "build_key"'
        )
        if context.services.duckdb_compression:
            context.services.duckdb.execute("CHECKPOINT")

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
