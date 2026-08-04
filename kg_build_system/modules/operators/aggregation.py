from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, ClassVar
from ...compile.models import CollectionInputSlot, ModuleDefinition, ModuleReference, OutputSlot, WorkflowStep
from ...workflow.interfaces import Module, ModuleCompilationResult, ModuleCompiler, ModuleExecutor, ModuleRegistration, ModuleRegistrationConfiguration, WorkflowStepDraft
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
                input_slot=CollectionInputSlot(slot_id=f"{self.ID}::{component.name}.inputs")
                step=WorkflowStep(step_id=f"{self.ID}::{component.name}",module_id=self.ID,inputs=(input_slot,),outputs=(OutputSlot(slot_id=f"{self.ID}::{component.name}.output",artifact_role=CoreArtifactRoles.graph_records(component.kind,component.name)),),payload={"relation":f"kg_aggregate_{component.name.lower()}"})
                steps.append(WorkflowStepDraft(step,{input_slot.slot_id:lambda _input, output, component=component: (identity := CoreArtifactRoles.graph_record_identity(output.artifact_role)) is not None and identity.kind == component.kind and identity.component == component.name}))
        return ModuleCompilationResult(ModuleDefinition(reference=ModuleReference(module_id=self.ID,import_module=type(self).__module__,class_qualname=type(self).__qualname__,implementation_version="1",priority=0,configuration={})),tuple(steps))

class _Executor:
    async def execute_step(self, context: ModuleExecutionContext, step: WorkflowStep) -> StepOutcome:
        payload=step.payload or {}; relation=str(payload["relation"]).replace('"','""')
        inputs=tuple(artifact.value for artifacts in context.inputs.values() for artifact in artifacts)
        if not inputs: raise RuntimeError("binding aggregation requires graph-record inputs")
        sql=" UNION ALL ".join(f'SELECT * FROM "{str(input).replace(chr(34), chr(34)*2)}"' for input in inputs)
        context.services["duckdb"].execute(f'CREATE TEMP TABLE "{relation}" AS {sql}')
        slot=step.outputs[0]; return StepOutcome(step.step_id,step.module_id,StepStatus.SUCCEEDED,(Artifact(slot.slot_id,slot.artifact_role,payload["relation"]),))
