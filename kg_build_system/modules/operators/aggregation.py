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
class BindingAggregationModule(Module, ModuleRegistration[_Configuration]):
    configuration: _Configuration = field(default_factory=_Configuration)
    ID: ClassVar[str] = "binding_aggregation"
    @classmethod
    async def create_compiler(cls, context: Any) -> ModuleCompiler: return context.registration
    @classmethod
    async def create_executor(cls, context: Any) -> ModuleExecutor: return _Executor()
    async def compile(self, context: Any) -> ModuleCompilationResult:
        steps=[]
        for component in context.components:
            indexes=[i for i,binding in enumerate(context.bindings) if binding.component == component.name]
            if indexes:
                inputs=tuple(SingleInputSlot(slot_id=f"{self.ID}::{component.name}.{i}") for i in indexes)
                step=WorkflowStep(step_id=f"{self.ID}::{component.name}",module_id=self.ID,inputs=inputs,outputs=(OutputSlot(slot_id=f"{self.ID}::{component.name}.output",artifact_role=CoreArtifactRoles.raw_relation(component.name)),),payload={"relation":f"kg_raw_{component.name.lower()}","sql":" UNION ALL ".join(f"SELECT * FROM kg_binding_{i}" for i in indexes)})
                steps.append(WorkflowStepDraft(step,{slot.slot_id:role_is(CoreArtifactRoles.binding_relation(i)) for slot,i in zip(inputs,indexes,strict=True)}))
        return ModuleCompilationResult(ModuleDefinition(reference=ModuleReference(module_id=self.ID,import_module=type(self).__module__,class_qualname=type(self).__qualname__,implementation_version="1",priority=0,configuration={})),tuple(steps))

class _Executor:
    async def execute_step(self, context: ModuleExecutionContext, step: WorkflowStep) -> StepOutcome:
        payload=step.payload or {}; relation=str(payload["relation"]).replace('"','""'); context.services["duckdb"].execute(f'CREATE TEMP TABLE "{relation}" AS {payload["sql"]}')
        slot=step.outputs[0]; return StepOutcome(step.step_id,step.module_id,StepStatus.SUCCEEDED,(Artifact(slot.slot_id,slot.artifact_role,payload["relation"]),))
