from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, ClassVar
from ...compile.models import ModuleDefinition, ModuleReference, OutputSlot, SingleInputSlot, WorkflowStep
from ...workflow.interfaces import Module, ModuleCompilationResult, ModuleCompiler, ModuleExecutor, ModuleRegistration, ModuleRegistrationConfiguration, WorkflowStepDraft
from ...workflow.models import Artifact, DisruptedExecutionContext, ExecutionContext, StepOutcome, StepStatus
from ..core.core import CoreArtifactRoles
@dataclass(frozen=True)
class _Configuration(ModuleRegistrationConfiguration): pass
@dataclass(frozen=True)
class CollapseExactDuplicatesModule(Module, ModuleRegistration[_Configuration]):
    configuration: _Configuration = field(default_factory=_Configuration); ID: ClassVar[str]="collapse_exact_duplicates"
    @classmethod
    async def create_compiler(cls, context: Any) -> ModuleCompiler: return cls(context.registration_configuration)
    @classmethod
    async def create_executor(cls, context: Any) -> ModuleExecutor: return _Executor()
    async def compile(self, context: Any) -> ModuleCompilationResult:
        steps=[]
        for component in context.blueprint.components:
            slot=SingleInputSlot(slot_id=f"{self.ID}::{component.name}.input"); relation=f"kg_distinct_{component.name.lower()}"
            step=WorkflowStep(step_id=f"{self.ID}::{component.name}",module_id=self.ID,inputs=(slot,),outputs=(OutputSlot(slot_id=f"{self.ID}::{component.name}.output",artifact_role=CoreArtifactRoles.graph_records(component.kind,component.name)),),payload={"relation":relation})
            steps.append(WorkflowStepDraft(step,{slot.slot_id:lambda _input, output, component=component: output.artifact_role == CoreArtifactRoles.graph_records(component.kind, component.name)}))
        return ModuleCompilationResult(ModuleDefinition(reference=ModuleReference(module_id=self.ID,import_module=type(self).__module__,class_qualname=type(self).__qualname__,implementation_version="1",priority=0,configuration={})),tuple(steps))
class _Executor(ModuleExecutor):
    async def handle(self, context: ExecutionContext) -> StepOutcome:
        step = context.step; payload=step.payload or {}; relation=str(payload["relation"]).replace('"','""'); input_relation=next(item.artifact.value for inputs in context.inputs.values() for item in inputs if item.artifact is not None)
        context.services.duckdb.execute(f'CREATE TEMP TABLE "{relation}" AS SELECT DISTINCT * FROM "{str(input_relation).replace(chr(34),chr(34)*2)}"'); slot=step.outputs[0]
        return StepOutcome(step.step_id,step.module_id,StepStatus.SUCCEEDED,(Artifact(slot.slot_id,slot.artifact_role,payload["relation"]),))

    async def handle_disrupted(self, context: DisruptedExecutionContext) -> StepOutcome:
        return await super().handle_disrupted(context)
