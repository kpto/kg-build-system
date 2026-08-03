"""Workflow modules for graph-record normalisation and validation."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, ClassVar
from ..compile.models import ArtifactRole, CollectionInputSlot, ModuleDefinition, ModuleReference, OutputSlot, SingleInputSlot, WorkflowStep
from .workflow import Module, ModuleCompilationResult, ModuleCompiler, ModuleExecutor, ModuleRegistration, ModuleRegistrationConfiguration, WorkflowStepDraft, role_is

@dataclass(frozen=True)
class EmptyConfiguration(ModuleRegistrationConfiguration): pass

def _definition(module: type[Module]) -> ModuleDefinition:
    return ModuleDefinition(reference=ModuleReference(module_id=module.ID, import_module=module.__module__, class_qualname=module.__qualname__, implementation_version=str(getattr(module, "VERSION", "1")), priority=0, configuration={}))

def _quote(name: str) -> str: return '"' + name.replace('"', '""') + '"'

class SqlExecutor:
    async def execute_step(self, context: Any, step: WorkflowStep) -> Any:
        payload = step.payload or {}; connection = context.services["duckdb"]
        if payload["action"] == "diagnostic": return [f"{payload['component']}({key}) has {count} non-null values for {payload['field']}" for key, count in connection.execute(payload["sql"]).fetchall()]
        materialization = "TABLE" if payload["materialization"] == "temporary_table" else "VIEW"
        connection.execute(f'CREATE TEMP {materialization} {_quote(str(payload["relation"]))} AS {payload["sql"]}')
        return payload["relation"]

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
            step=WorkflowStep(step_id=f"{self.ID}::{component.name}", module_id=self.ID, inputs=inputs, outputs=(OutputSlot(slot_id=f"{self.ID}::{component.name}.output", artifact_role=ArtifactRole(namespace="core", name=f"relation.raw.{component.name}")),), payload={"action":"relation","relation":f"kg_raw_{component.name.lower()}","sql":" UNION ALL ".join(f"SELECT * FROM kg_binding_{i}" for i in indexes),"materialization":"temporary_table"})
            steps.append(WorkflowStepDraft(step,{slot.slot_id:role_is(ArtifactRole(namespace="core",name=f"relation.binding.{i}")) for slot,i in zip(inputs,indexes,strict=True)}))
        return ModuleCompilationResult(_definition(type(self)),tuple(steps))

@dataclass(frozen=True)
class CollapseExactDuplicatesModule(_SqlModule):
    configuration: EmptyConfiguration = field(default_factory=EmptyConfiguration)
    ID: ClassVar[str] = "collapse_exact_duplicates"
    async def compile(self, context: Any) -> ModuleCompilationResult:
        steps=[]
        for component in context.components:
            slot=SingleInputSlot(slot_id=f"{self.ID}::{component.name}.input")
            step=WorkflowStep(step_id=f"{self.ID}::{component.name}",module_id=self.ID,inputs=(slot,),outputs=(OutputSlot(slot_id=f"{self.ID}::{component.name}.output",artifact_role=ArtifactRole(namespace="core",name=f"relation.distinct.{component.name}")),),payload={"action":"relation","relation":f"kg_distinct_{component.name.lower()}","sql":f"SELECT DISTINCT * FROM {_quote(f'kg_raw_{component.name.lower()}')}","materialization":"temporary_table"})
            steps.append(WorkflowStepDraft(step,{slot.slot_id:role_is(ArtifactRole(namespace="core",name=f"relation.raw.{component.name}"))}))
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
            step=WorkflowStep(step_id=f"{self.ID}::{component.name}",module_id=self.ID,inputs=(slot,),outputs=(OutputSlot(slot_id=f"{self.ID}::{component.name}.output",artifact_role=ArtifactRole(namespace="core",name=f"graph.records.{component.kind}.{component.name}")),),payload={"action":"relation","relation":f"kg_normalised_{component.name.lower()}","sql":f"SELECT {select} FROM {_quote(f'kg_distinct_{component.name.lower()}')} GROUP BY {_quote('build_key')}","materialization":"temporary_table"})
            steps.append(WorkflowStepDraft(step,{slot.slot_id:role_is(ArtifactRole(namespace="core",name=f"relation.distinct.{component.name}"))}))
        return ModuleCompilationResult(_definition(type(self)),tuple(steps))

@dataclass(frozen=True)
class RejectConflictingNonNullValuesModule(_SqlModule):
    configuration: EmptyConfiguration = field(default_factory=EmptyConfiguration)
    ID: ClassVar[str] = "reject_conflicting_non_null_values"
    async def compile(self, context: Any) -> ModuleCompilationResult:
        steps=[]
        for component in context.components:
            for prop in component.properties:
                slot=CollectionInputSlot(slot_id=f"{self.ID}::{component.name}.{prop.name}.input"); raw=f"kg_raw_{component.name.lower()}"
                step=WorkflowStep(step_id=f"{self.ID}::{component.name}.{prop.name}",module_id=self.ID,inputs=(slot,),outputs=(OutputSlot(slot_id=f"{self.ID}::{component.name}.{prop.name}.output",artifact_role=ArtifactRole(namespace="core",name=f"diagnostic.conflicting_value.{component.name}.{prop.name}")),),payload={"action":"diagnostic","component":component.name,"field":prop.name,"sql":f"SELECT build_key, count(DISTINCT {_quote(prop.name)}) AS values FROM {_quote(raw)} WHERE build_key IS NOT NULL GROUP BY build_key HAVING count(DISTINCT {_quote(prop.name)}) FILTER (WHERE {_quote(prop.name)} IS NOT NULL) > 1"})
                steps.append(WorkflowStepDraft(step,{slot.slot_id:lambda _input,output:output.artifact_role.namespace=="core" and output.artifact_role.name.startswith("graph.records.")}))
        return ModuleCompilationResult(_definition(type(self)),tuple(steps))
