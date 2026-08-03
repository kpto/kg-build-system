from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, ClassVar
from ...compile.models import ModuleDefinition, ModuleReference, OutputSlot, SingleInputSlot, WorkflowStep
from ...workflow.interfaces import Module, ModuleCompilationResult, ModuleCompiler, ModuleExecutor, ModuleRegistration, ModuleRegistrationConfiguration, WorkflowStepDraft, role_is
from ...workflow.models import Artifact, ModuleExecutionContext, StepOutcome, StepStatus
from ..core.core import CoreArtifactRoles
@dataclass(frozen=True)
class _Configuration(ModuleRegistrationConfiguration): pass
@dataclass(frozen=True)
class MergeCompatibleFactsModule(Module, ModuleRegistration[_Configuration]):
    configuration: _Configuration = field(default_factory=_Configuration); ID: ClassVar[str]="merge_compatible_facts"
    @classmethod
    async def create_compiler(cls, context: Any) -> ModuleCompiler: return context.registration
    @classmethod
    async def create_executor(cls, context: Any) -> ModuleExecutor: return _Executor()
    async def compile(self, context: Any) -> ModuleCompilationResult:
        steps=[]
        for component in context.components:
            slot=SingleInputSlot(slot_id=f"{self.ID}::{component.name}.input"); fields=[property.name for property in component.properties]
            if component.kind=="edge": fields=["source_build_key","target_build_key",*fields]
            select=", ".join(['"build_key"',*(f'min("{field}") AS "{field}"' for field in fields)]); relation=f"kg_normalised_{component.name.lower()}"
            step=WorkflowStep(step_id=f"{self.ID}::{component.name}",module_id=self.ID,inputs=(slot,),outputs=(OutputSlot(slot_id=f"{self.ID}::{component.name}.output",artifact_role=CoreArtifactRoles.graph_records(component.kind,component.name)),),payload={"relation":relation,"sql":f'SELECT {select} FROM "kg_distinct_{component.name.lower()}" GROUP BY "build_key"'})
            steps.append(WorkflowStepDraft(step,{slot.slot_id:role_is(CoreArtifactRoles.distinct_relation(component.name))}))
        return ModuleCompilationResult(ModuleDefinition(reference=ModuleReference(module_id=self.ID,import_module=type(self).__module__,class_qualname=type(self).__qualname__,implementation_version="1",priority=0,configuration={})),tuple(steps))
class _Executor:
    async def execute_step(self, context: ModuleExecutionContext, step: WorkflowStep) -> StepOutcome:
        payload=step.payload or {}; relation=str(payload["relation"]).replace('"','""'); context.services["duckdb"].execute(f'CREATE TEMP TABLE "{relation}" AS {payload["sql"]}'); slot=step.outputs[0]; return StepOutcome(step.step_id,step.module_id,StepStatus.SUCCEEDED,(Artifact(slot.slot_id,slot.artifact_role,payload["relation"]),))
