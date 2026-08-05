from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, ClassVar
from ...compile.models import ArtifactRole, CollectionInputSlot, ModuleDefinition, ModuleReference, OutputSlot, SingleInputSlot, WorkflowStep
from ...workflow.interfaces import Module, ModuleCompilationResult, ModuleCompiler, ModuleExecutor, ModuleRegistration, ModuleRegistrationConfiguration, WorkflowStepDraft
from ...workflow.models import Artifact, DisruptedExecutionContext, ExecutionContext, Failure, StepOutcome, StepStatus, WorkflowArtifactRoles
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
    async def create_compiler(cls,context:Any)->ModuleCompiler:return cls(context.registration_configuration)
    @classmethod
    async def create_executor(cls,context:Any)->ModuleExecutor:return _Executor()
    async def compile(self,context:Any)->ModuleCompilationResult:
        steps=[]
        for component in context.blueprint.components:
            for prop in component.properties:
                slot=SingleInputSlot(slot_id=f"{self.ID}::{component.name}.{prop.name}.input")
                step=WorkflowStep(step_id=f"{self.ID}::{component.name}.{prop.name}",module_id=self.ID,inputs=(slot,),outputs=(OutputSlot(slot_id=f"{self.ID}::{component.name}.{prop.name}.output",artifact_role=ArtifactRole(namespace=self.ID,name=f"findings.{component.name}.{prop.name}")),),payload={"action":"findings","component":component.name,"field":prop.name})
                steps.append(WorkflowStepDraft(step,{slot.slot_id:lambda _input,output,component=component: output.artifact_role == CoreArtifactRoles.graph_records(component.kind,component.name)}))
        finding_slot=CollectionInputSlot(slot_id=f"{self.ID}::report.findings")
        record_slots=tuple(SingleInputSlot(slot_id=f"{self.ID}::report.{component.name}.records") for component in context.blueprint.components)
        outputs=(OutputSlot(slot_id=f"{self.ID}::report.output",artifact_role=WorkflowArtifactRoles.published(self.ID,"report")),*tuple(OutputSlot(slot_id=f"{self.ID}::report.{component.name}.output",artifact_role=CoreArtifactRoles.graph_records(component.kind,component.name)) for component in context.blueprint.components))
        report=WorkflowStep(step_id=f"{self.ID}::report",module_id=self.ID,assembly_preference="deferred",inputs=(finding_slot,*record_slots),outputs=outputs,payload={"action":"report","fail_on_error":self.configuration.fail_on_error})
        candidates={finding_slot.slot_id:lambda _input,output:output.artifact_role.namespace==self.ID and output.artifact_role.name.startswith("findings.")}
        candidates.update({slot.slot_id:lambda _input,output,component=component: output.artifact_role == CoreArtifactRoles.graph_records(component.kind,component.name) for slot,component in zip(record_slots,context.blueprint.components,strict=True)})
        steps.append(WorkflowStepDraft(report,candidates))
        return ModuleCompilationResult(ModuleDefinition(reference=ModuleReference(module_id=self.ID,import_module=type(self).__module__,class_qualname=type(self).__qualname__,implementation_version="1",priority=0,configuration={"fail_on_error":self.configuration.fail_on_error})),tuple(steps))
class _Executor(ModuleExecutor):
    async def handle(self,context:ExecutionContext)->StepOutcome:
        step=context.step; payload=step.payload or {}; slot=step.outputs[0]
        if payload["action"]=="findings":
            relation=next(item.artifact.value for inputs in context.inputs.values() for item in inputs if item.artifact is not None)
            field=str(payload["field"]).replace('"','""')
            sql=f'SELECT build_key, count(DISTINCT "{field}") FROM "{str(relation).replace(chr(34),chr(34)*2)}" WHERE build_key IS NOT NULL GROUP BY build_key HAVING count(DISTINCT "{field}") FILTER (WHERE "{field}" IS NOT NULL)>1'
            findings=tuple(ConflictingNonNullValueFinding(payload["component"],str(key),payload["field"],count) for key,count in context.services.duckdb.execute(sql).fetchall())
            return StepOutcome(step.step_id,step.module_id,StepStatus.SUCCEEDED,(Artifact(slot.slot_id,slot.artifact_role,findings),))
        findings=tuple(finding for item in context.inputs.get("reject_conflicting_non_null_values::report.findings", ()) if item.artifact is not None for finding in item.artifact.value)
        record_artifacts=tuple(item.artifact for slot_id,inputs in context.inputs.items() if slot_id != "reject_conflicting_non_null_values::report.findings" for item in inputs if item.artifact is not None)
        if not findings:
            return StepOutcome(step.step_id,step.module_id,StepStatus.SUCCEEDED,tuple(Artifact(output.slot_id,output.artifact_role,record_artifacts[index].value) for index,output in enumerate(step.outputs[1:])))
        report=ConflictingNonNullValuesReport(findings)
        failure=Failure(f"validation found {len(findings)} conflicting non-null value(s)",step.module_id,step.step_id) if findings and payload["fail_on_error"] else None
        artifacts=(Artifact(slot.slot_id,slot.artifact_role,report),)
        if failure is None:
            artifacts += tuple(Artifact(output.slot_id,output.artifact_role,record_artifacts[index].value) for index,output in enumerate(step.outputs[1:]))
        return StepOutcome(step.step_id,step.module_id,StepStatus.FAILED if failure else StepStatus.SUCCEEDED,artifacts,failure=failure)

    async def handle_disrupted(self, context: DisruptedExecutionContext) -> StepOutcome:
        return await super().handle_disrupted(context)
