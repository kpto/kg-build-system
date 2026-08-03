from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, ClassVar
from ...compile.models import ArtifactRole, CollectionInputSlot, ModuleDefinition, ModuleReference, OutputSlot, WorkflowStep
from ...workflow.interfaces import Module, ModuleCompilationResult, ModuleCompiler, ModuleExecutor, ModuleRegistration, ModuleRegistrationConfiguration, WorkflowStepDraft
from ...workflow.models import Artifact, Failure, ModuleExecutionContext, StepOutcome, StepStatus
from ..core.core import CoreArtifactRoles
@dataclass(frozen=True)
class RejectConflictingNonNullValuesConfiguration(ModuleRegistrationConfiguration): fail_on_error: bool=True
@dataclass(frozen=True)
class ConflictingNonNullValueFinding: component:str; build_key:str; property_name:str; distinct_values:int
@dataclass(frozen=True)
class ConflictingNonNullValuesReport: findings:tuple[ConflictingNonNullValueFinding,...]
@dataclass(frozen=True)
class RejectConflictingNonNullValuesModule(Module, ModuleRegistration[RejectConflictingNonNullValuesConfiguration]):
    configuration: RejectConflictingNonNullValuesConfiguration=field(default_factory=RejectConflictingNonNullValuesConfiguration); ID:ClassVar[str]="reject_conflicting_non_null_values"
    @classmethod
    async def create_compiler(cls,context:Any)->ModuleCompiler:return context.registration
    @classmethod
    async def create_executor(cls,context:Any)->ModuleExecutor:return _Executor()
    async def compile(self,context:Any)->ModuleCompilationResult:
        steps=[]
        for component in context.components:
            for prop in component.properties:
                slot=CollectionInputSlot(slot_id=f"{self.ID}::{component.name}.{prop.name}.input")
                step=WorkflowStep(step_id=f"{self.ID}::{component.name}.{prop.name}",module_id=self.ID,inputs=(slot,),outputs=(OutputSlot(slot_id=f"{self.ID}::{component.name}.{prop.name}.output",artifact_role=ArtifactRole(namespace=self.ID,name=f"findings.{component.name}.{prop.name}")),),payload={"action":"findings","component":component.name,"field":prop.name,"sql":f'SELECT build_key, count(DISTINCT "{prop.name}") FROM "kg_raw_{component.name.lower()}" WHERE build_key IS NOT NULL GROUP BY build_key HAVING count(DISTINCT "{prop.name}") FILTER (WHERE "{prop.name}" IS NOT NULL)>1'})
                steps.append(WorkflowStepDraft(step,{slot.slot_id:lambda _input,output:CoreArtifactRoles.is_graph_records(output.artifact_role)}))
        slot=CollectionInputSlot(slot_id=f"{self.ID}::report.findings")
        steps.append(WorkflowStepDraft(WorkflowStep(step_id=f"{self.ID}::report",module_id=self.ID,assembly_preference="deferred",inputs=(slot,),outputs=(OutputSlot(slot_id=f"{self.ID}::report.output",artifact_role=CoreArtifactRoles.published(self.ID,"report")),),payload={"action":"report","fail_on_error":self.configuration.fail_on_error}),{slot.slot_id:lambda _input,output:output.artifact_role.namespace==self.ID and output.artifact_role.name.startswith("findings.")}))
        return ModuleCompilationResult(ModuleDefinition(reference=ModuleReference(module_id=self.ID,import_module=type(self).__module__,class_qualname=type(self).__qualname__,implementation_version="1",priority=0,configuration={"fail_on_error":self.configuration.fail_on_error})),tuple(steps))
class _Executor:
    async def execute_step(self,context:ModuleExecutionContext,step:WorkflowStep)->StepOutcome:
        payload=step.payload or {}; slot=step.outputs[0]
        if payload["action"]=="findings":
            findings=tuple(ConflictingNonNullValueFinding(payload["component"],str(key),payload["field"],count) for key,count in context.services["duckdb"].execute(payload["sql"]).fetchall())
            return StepOutcome(step.step_id,step.module_id,StepStatus.SUCCEEDED,(Artifact(slot.slot_id,slot.artifact_role,findings),))
        findings=tuple(finding for artifacts in context.inputs.values() for artifact in artifacts for finding in artifact.value)
        if not findings: return StepOutcome(step.step_id,step.module_id,StepStatus.SUCCEEDED)
        report=ConflictingNonNullValuesReport(findings)
        failure=Failure(f"validation found {len(findings)} conflicting non-null value(s)",step.module_id,step.step_id) if findings and payload["fail_on_error"] else None
        return StepOutcome(step.step_id,step.module_id,StepStatus.FAILED if failure else StepStatus.SUCCEEDED,(Artifact(slot.slot_id,slot.artifact_role,report),),failure=failure)
