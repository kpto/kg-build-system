"""Small workflow modules for graph-record normalisation and validation."""
from __future__ import annotations
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, ClassVar
from ..compile.models import ArtifactRole, CollectionInputSlot, CompiledModule, ModuleReference, OutputSlot, SingleInputSlot, WorkflowStep
from .workflow import ModuleContributor, ModuleDeclarationDraft, StepExecutor, WorkflowModule, WorkflowStepDraft, role_is

def _quote(name: str) -> str: return '"' + name.replace('"', '""') + '"'
def _module(module_id: str, runtime: type[Any], priority: int) -> CompiledModule:
    return CompiledModule(reference=ModuleReference(module_id=module_id, import_module=runtime.__module__, class_qualname=runtime.__qualname__, implementation_version="1", priority=priority))

class SqlStepRuntime(WorkflowModule, StepExecutor):
    ID: ClassVar[str]
    @classmethod
    async def create_runtime(cls, _configuration: Mapping[str, Any]) -> SqlStepRuntime: return cls()
    async def execute_step(self, context: Any, step: WorkflowStep) -> Any:
        payload = step.payload or {}; connection = context.services["duckdb"]
        if payload["action"] == "diagnostic": return [f"{payload['component']}({key}) has {count} non-null values for {payload['field']}" for key, count in connection.execute(payload["sql"]).fetchall()]
        materialization = "TABLE" if payload["materialization"] == "temporary_table" else "VIEW"
        connection.execute(f'CREATE TEMP {materialization} {_quote(str(payload["relation"]))} AS {payload["sql"]}')
        return payload["relation"]

class BindingAggregationRuntime(SqlStepRuntime): ID = "binding_aggregation"
class ExactDuplicateCollapseRuntime(SqlStepRuntime): ID = "collapse_exact_duplicates"
class CompatibleFactMergeRuntime(SqlStepRuntime): ID = "merge_compatible_facts"
class ConflictingValueRejectionRuntime(SqlStepRuntime): ID = "reject_conflicting_non_null_values"

@dataclass(frozen=True)
class BindingAggregationModule(ModuleContributor):
    @property
    def module_class(self) -> type[BindingAggregationRuntime]: return BindingAggregationRuntime
    async def declare(self, context: Any) -> ModuleDeclarationDraft:
        blueprint = context
        steps: list[WorkflowStepDraft] = []
        for component in blueprint.components:
            indexes = [index for index, binding in enumerate(blueprint.bindings) if binding.component == component.name]
            if not indexes: continue
            inputs = tuple(SingleInputSlot(slot_id=f"binding_aggregation::{component.name}.{index}") for index in indexes)
            step = WorkflowStep(step_id=f"binding_aggregation::{component.name}", module_id="binding_aggregation", inputs=inputs, outputs=(OutputSlot(slot_id=f"binding_aggregation::{component.name}.output", artifact_role=ArtifactRole(namespace="core", name=f"relation.raw.{component.name}")),), payload={"action":"relation", "relation":f"kg_raw_{component.name.lower()}", "sql":" UNION ALL ".join(f"SELECT * FROM kg_binding_{index}" for index in indexes), "materialization":"temporary_table"})
            steps.append(WorkflowStepDraft(step, {slot.slot_id: role_is(ArtifactRole(namespace="core", name=f"relation.binding.{index}")) for slot, index in zip(inputs, indexes, strict=True)}))
        return ModuleDeclarationDraft(_module("binding_aggregation", BindingAggregationRuntime, 10), tuple(steps))

@dataclass(frozen=True)
class CollapseExactDuplicatesModule(ModuleContributor):
    @property
    def module_class(self) -> type[ExactDuplicateCollapseRuntime]: return ExactDuplicateCollapseRuntime
    async def declare(self, context: Any) -> ModuleDeclarationDraft:
        blueprint = context
        steps: list[WorkflowStepDraft] = []
        for component in blueprint.components:
            input_slot = SingleInputSlot(slot_id=f"collapse_exact_duplicates::{component.name}.input")
            step = WorkflowStep(step_id=f"collapse_exact_duplicates::{component.name}", module_id="collapse_exact_duplicates", inputs=(input_slot,), outputs=(OutputSlot(slot_id=f"collapse_exact_duplicates::{component.name}.output", artifact_role=ArtifactRole(namespace="core", name=f"relation.distinct.{component.name}")),), payload={"action":"relation", "relation":f"kg_distinct_{component.name.lower()}", "sql":f"SELECT DISTINCT * FROM {_quote(f'kg_raw_{component.name.lower()}')}", "materialization":"temporary_table"})
            steps.append(WorkflowStepDraft(step, {input_slot.slot_id: role_is(ArtifactRole(namespace="core", name=f"relation.raw.{component.name}"))}))
        return ModuleDeclarationDraft(_module("collapse_exact_duplicates", ExactDuplicateCollapseRuntime, 20), tuple(steps))

@dataclass(frozen=True)
class MergeCompatibleFactsModule(ModuleContributor):
    @property
    def module_class(self) -> type[CompatibleFactMergeRuntime]: return CompatibleFactMergeRuntime
    async def declare(self, context: Any) -> ModuleDeclarationDraft:
        blueprint = context
        steps: list[WorkflowStepDraft] = []
        for component in blueprint.components:
            input_slot = SingleInputSlot(slot_id=f"merge_compatible_facts::{component.name}.input")
            fields = [property.name for property in component.properties]
            if component.kind == "edge": fields = ["source_build_key", "target_build_key", *fields]
            select = ", ".join([_quote("build_key"), *(f"min({_quote(field)}) AS {_quote(field)}" for field in fields)])
            step = WorkflowStep(step_id=f"merge_compatible_facts::{component.name}", module_id="merge_compatible_facts", inputs=(input_slot,), outputs=(OutputSlot(slot_id=f"merge_compatible_facts::{component.name}.output", artifact_role=ArtifactRole(namespace="core", name=f"graph.records.{component.kind}.{component.name}")),), payload={"action":"relation", "relation":f"kg_normalised_{component.name.lower()}", "sql":f"SELECT {select} FROM {_quote(f'kg_distinct_{component.name.lower()}')} GROUP BY {_quote('build_key')}", "materialization":"temporary_table"})
            steps.append(WorkflowStepDraft(step, {input_slot.slot_id: role_is(ArtifactRole(namespace="core", name=f"relation.distinct.{component.name}"))}))
        return ModuleDeclarationDraft(_module("merge_compatible_facts", CompatibleFactMergeRuntime, 30), tuple(steps))

@dataclass(frozen=True)
class RejectConflictingNonNullValuesModule(ModuleContributor):
    @property
    def module_class(self) -> type[ConflictingValueRejectionRuntime]: return ConflictingValueRejectionRuntime
    async def declare(self, context: Any) -> ModuleDeclarationDraft:
        blueprint = context
        steps: list[WorkflowStepDraft] = []
        for component in blueprint.components:
            for property_definition in component.properties:
                input_slot = CollectionInputSlot(slot_id=f"reject_conflicting_non_null_values::{component.name}.{property_definition.name}.input")
                field = property_definition.name; raw = f"kg_raw_{component.name.lower()}"
                step = WorkflowStep(step_id=f"reject_conflicting_non_null_values::{component.name}.{field}", module_id="reject_conflicting_non_null_values", inputs=(input_slot,), outputs=(OutputSlot(slot_id=f"reject_conflicting_non_null_values::{component.name}.{field}.output", artifact_role=ArtifactRole(namespace="core", name=f"diagnostic.conflicting_value.{component.name}.{field}")),), payload={"action":"diagnostic", "component":component.name, "field":field, "sql":f"SELECT build_key, count(DISTINCT {_quote(field)}) AS values FROM {_quote(raw)} WHERE build_key IS NOT NULL GROUP BY build_key HAVING count(DISTINCT {_quote(field)}) FILTER (WHERE {_quote(field)} IS NOT NULL) > 1"})
                steps.append(WorkflowStepDraft(step, {input_slot.slot_id: lambda _input, output: output.artifact_role.namespace == "core" and output.artifact_role.name.startswith("graph.records.")}))
        return ModuleDeclarationDraft(_module("reject_conflicting_non_null_values", ConflictingValueRejectionRuntime, 40), tuple(steps))
