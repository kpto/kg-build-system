"""Workflow modules for graph-record normalisation and validation."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, ClassVar
from ..compile.models import ArtifactRole, CollectionInputSlot, ModuleDefinition, ModuleReference, OutputSlot, SingleInputSlot, WorkflowStep
from ..workflow.interfaces import Module, ModuleCompilationResult, ModuleCompiler, ModuleExecutor, ModuleRegistration, ModuleRegistrationConfiguration, WorkflowStepDraft, role_is
from ..workflow.models import Artifact, Failure, ModuleExecutionContext, StepOutcome, StepStatus
from .core import CoreArtifactRoles

@dataclass(frozen=True)
class EmptyConfiguration(ModuleRegistrationConfiguration): pass

@dataclass(frozen=True)
class RejectConflictingNonNullValuesConfiguration(ModuleRegistrationConfiguration):
    """Controls whether conflicting values are a validation gate."""

    fail_on_error: bool = True

@dataclass(frozen=True)
class ConflictingNonNullValueFinding:
    component: str
    build_key: str
    property_name: str
    distinct_values: int

@dataclass(frozen=True)
class ConflictingNonNullValuesReport:
    findings: tuple[ConflictingNonNullValueFinding, ...]

def _definition(module: type[Module]) -> ModuleDefinition:
    return ModuleDefinition(reference=ModuleReference(module_id=module.ID, import_module=module.__module__, class_qualname=module.__qualname__, implementation_version=str(getattr(module, "VERSION", "1")), priority=0, configuration={}))

def _quote(name: str) -> str: return '"' + name.replace('"', '""') + '"'

class SqlExecutor:
    async def execute_step(self, context: ModuleExecutionContext, step: WorkflowStep) -> StepOutcome:
        payload = step.payload or {}; connection = context.services["duckdb"]
        output = step.outputs[0]
        if payload["action"] == "findings":
            findings = tuple(
                ConflictingNonNullValueFinding(
                    component=payload["component"], build_key=str(key),
                    property_name=payload["field"], distinct_values=count,
                )
                for key, count in connection.execute(payload["sql"]).fetchall()
            )
            return StepOutcome(step.step_id, step.module_id, StepStatus.SUCCEEDED, (Artifact(output.slot_id, output.artifact_role, findings),))
        if payload["action"] == "aggregate_findings":
            findings = tuple(
                finding
                for artifacts in context.inputs.values()
                for artifact in artifacts
                for finding in artifact.value
            )
            if not findings:
                return StepOutcome(step.step_id, step.module_id, StepStatus.SUCCEEDED)
            report = ConflictingNonNullValuesReport(findings=findings)
            failed = bool(findings) and bool(payload.get("fail_on_error", False))
            failure = Failure(
                message=f"validation found {len(findings)} conflicting non-null value(s)",
                module_id=step.module_id,
                step_id=step.step_id,
            ) if failed else None
            return StepOutcome(
                step.step_id,
                step.module_id,
                StepStatus.FAILED if failed else StepStatus.SUCCEEDED,
                (Artifact(output.slot_id, output.artifact_role, report),),
                failure=failure,
            )
        materialization = "TABLE" if payload["materialization"] == "temporary_table" else "VIEW"
        connection.execute(f'CREATE TEMP {materialization} {_quote(str(payload["relation"]))} AS {payload["sql"]}')
        return StepOutcome(step.step_id, step.module_id, StepStatus.SUCCEEDED, (Artifact(output.slot_id, output.artifact_role, payload["relation"]),))

class _SqlModule(Module, ModuleRegistration[EmptyConfiguration]):
    configuration: EmptyConfiguration = field(default_factory=EmptyConfiguration)
    @classmethod
    async def create_compiler(cls, context: Any) -> ModuleCompiler: return context.registration
    @classmethod
    async def create_executor(cls, context: Any) -> ModuleExecutor: return SqlExecutor()

@dataclass(frozen=True)
class BindingAggregationModule(_SqlModule):
    configuration: EmptyConfiguration = field(default_factory=EmptyConfiguration)
    ID: ClassVar[str] = "binding_aggregation"
    async def compile(self, context: Any) -> ModuleCompilationResult:
        steps=[]
        for component in context.components:
            indexes=[i for i,binding in enumerate(context.bindings) if binding.component == component.name]
            if not indexes: continue
            inputs=tuple(SingleInputSlot(slot_id=f"{self.ID}::{component.name}.{i}") for i in indexes)
            step=WorkflowStep(step_id=f"{self.ID}::{component.name}", module_id=self.ID, inputs=inputs, outputs=(OutputSlot(slot_id=f"{self.ID}::{component.name}.output", artifact_role=CoreArtifactRoles.raw_relation(component.name)),), payload={"action":"relation","relation":f"kg_raw_{component.name.lower()}","sql":" UNION ALL ".join(f"SELECT * FROM kg_binding_{i}" for i in indexes),"materialization":"temporary_table"})
            steps.append(WorkflowStepDraft(step,{slot.slot_id:role_is(CoreArtifactRoles.binding_relation(i)) for slot,i in zip(inputs,indexes,strict=True)}))
        return ModuleCompilationResult(_definition(type(self)),tuple(steps))

@dataclass(frozen=True)
class CollapseExactDuplicatesModule(_SqlModule):
    configuration: EmptyConfiguration = field(default_factory=EmptyConfiguration)
    ID: ClassVar[str] = "collapse_exact_duplicates"
    async def compile(self, context: Any) -> ModuleCompilationResult:
        steps=[]
        for component in context.components:
            slot=SingleInputSlot(slot_id=f"{self.ID}::{component.name}.input")
            step=WorkflowStep(step_id=f"{self.ID}::{component.name}",module_id=self.ID,inputs=(slot,),outputs=(OutputSlot(slot_id=f"{self.ID}::{component.name}.output",artifact_role=CoreArtifactRoles.distinct_relation(component.name)),),payload={"action":"relation","relation":f"kg_distinct_{component.name.lower()}","sql":f"SELECT DISTINCT * FROM {_quote(f'kg_raw_{component.name.lower()}')}","materialization":"temporary_table"})
            steps.append(WorkflowStepDraft(step,{slot.slot_id:role_is(CoreArtifactRoles.raw_relation(component.name))}))
        return ModuleCompilationResult(_definition(type(self)),tuple(steps))

@dataclass(frozen=True)
class MergeCompatibleFactsModule(_SqlModule):
    configuration: EmptyConfiguration = field(default_factory=EmptyConfiguration)
    ID: ClassVar[str] = "merge_compatible_facts"
    async def compile(self, context: Any) -> ModuleCompilationResult:
        steps=[]
        for component in context.components:
            slot=SingleInputSlot(slot_id=f"{self.ID}::{component.name}.input"); fields=[p.name for p in component.properties]
            if component.kind == "edge": fields=["source_build_key","target_build_key",*fields]
            select=", ".join([_quote("build_key"),*(f"min({_quote(field)}) AS {_quote(field)}" for field in fields)])
            step=WorkflowStep(step_id=f"{self.ID}::{component.name}",module_id=self.ID,inputs=(slot,),outputs=(OutputSlot(slot_id=f"{self.ID}::{component.name}.output",artifact_role=CoreArtifactRoles.graph_records(component.kind, component.name)),),payload={"action":"relation","relation":f"kg_normalised_{component.name.lower()}","sql":f"SELECT {select} FROM {_quote(f'kg_distinct_{component.name.lower()}')} GROUP BY {_quote('build_key')}","materialization":"temporary_table"})
            steps.append(WorkflowStepDraft(step,{slot.slot_id:role_is(CoreArtifactRoles.distinct_relation(component.name))}))
        return ModuleCompilationResult(_definition(type(self)),tuple(steps))

@dataclass(frozen=True)
class RejectConflictingNonNullValuesModule(Module, ModuleRegistration[RejectConflictingNonNullValuesConfiguration]):
    configuration: RejectConflictingNonNullValuesConfiguration = field(default_factory=RejectConflictingNonNullValuesConfiguration)
    ID: ClassVar[str] = "reject_conflicting_non_null_values"
    @classmethod
    async def create_compiler(cls, context: Any) -> ModuleCompiler: return context.registration
    @classmethod
    async def create_executor(cls, context: Any) -> ModuleExecutor: return SqlExecutor()
    async def compile(self, context: Any) -> ModuleCompilationResult:
        steps=[]
        for component in context.components:
            for prop in component.properties:
                slot=CollectionInputSlot(slot_id=f"{self.ID}::{component.name}.{prop.name}.input"); raw=f"kg_raw_{component.name.lower()}"
                step=WorkflowStep(step_id=f"{self.ID}::{component.name}.{prop.name}",module_id=self.ID,inputs=(slot,),outputs=(OutputSlot(slot_id=f"{self.ID}::{component.name}.{prop.name}.output",artifact_role=ArtifactRole(namespace=self.ID, name=f"findings.{component.name}.{prop.name}")),),payload={"action":"findings","component":component.name,"field":prop.name,"sql":f"SELECT build_key, count(DISTINCT {_quote(prop.name)}) AS values FROM {_quote(raw)} WHERE build_key IS NOT NULL GROUP BY build_key HAVING count(DISTINCT {_quote(prop.name)}) FILTER (WHERE {_quote(prop.name)} IS NOT NULL) > 1"})
                steps.append(WorkflowStepDraft(step,{slot.slot_id:lambda _input,output:CoreArtifactRoles.is_graph_records(output.artifact_role)}))
        findings_slot = CollectionInputSlot(slot_id=f"{self.ID}::report.findings")
        report_step = WorkflowStep(
            step_id=f"{self.ID}::report",
            module_id=self.ID,
            assembly_preference="deferred",
            inputs=(findings_slot,),
            outputs=(OutputSlot(slot_id=f"{self.ID}::report.output", artifact_role=CoreArtifactRoles.published(self.ID, "report")),),
            payload={"action": "aggregate_findings", "fail_on_error": self.configuration.fail_on_error},
        )
        steps.append(WorkflowStepDraft(report_step, {
            findings_slot.slot_id: lambda _input, output: output.artifact_role.namespace == self.ID and output.artifact_role.name.startswith("findings."),
        }))
        return ModuleCompilationResult(_definition(type(self)),tuple(steps))
