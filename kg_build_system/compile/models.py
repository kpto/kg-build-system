"""Canonical immutable declaration, compilation, and workflow IR."""
from __future__ import annotations

from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, PlainSerializer, PlainValidator, model_validator

from .ir import BuildBlueprint as CanonicalBuildBlueprint
from .ir import SourceDefinition as CanonicalSourceDefinition


class IRModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class AnnotationDefinition(IRModel):
    namespace: str = Field(min_length=1)
    annotation_id: str = Field(min_length=1)
    arguments: JsonValue


class ValueType(IRModel):
    kind: Literal["scalar", "collection", "unknown"]
    name: str
    nullable: bool = False
    item_nullable: bool = False
    item: str | None = None


class FieldReference(IRModel):
    kind: Literal["field"] = "field"
    table: str = Field(min_length=1)
    path: tuple[str, ...] = Field(min_length=1)
    value_type: ValueType
    collection_paths: tuple[tuple[str, ...], ...] = ()
    annotations: tuple[AnnotationDefinition, ...] = ()


class LiteralValue(IRModel):
    kind: Literal["literal"] = "literal"
    value: str | int | float | bool | None
    value_type: ValueType


class Operation(IRModel):
    kind: Literal["operation"] = "operation"
    op: Literal["concat", "coalesce", "cast", "deterministic_uuid", "expand", "struct_field", "lookup_one"]
    args: tuple["Value", ...] = Field(min_length=1)
    value_type: ValueType
    sql_type: str | None = None
    field_name: str | None = None


Value = Annotated[FieldReference | LiteralValue | Operation, Field(discriminator="kind")]
Operation.model_rebuild()


class PropertyDefinition(IRModel):
    name: str = Field(min_length=1)
    value_type: ValueType
    nullable: bool
    annotations: tuple[AnnotationDefinition, ...] = ()


class ComponentDefinition(IRModel):
    name: str = Field(min_length=1)
    kind: Literal["node", "edge"]
    description: str | None = None
    properties: tuple[PropertyDefinition, ...] = ()
    source: str | None = None
    target: str | None = None
    annotations: tuple[AnnotationDefinition, ...] = ()


class ProjectionDefinition(IRModel):
    name: str = Field(min_length=1)
    fields: dict[str, Value] = Field(min_length=1)
    annotations: tuple[AnnotationDefinition, ...] = ()
    field_annotations: dict[str, tuple[AnnotationDefinition, ...]] = Field(default_factory=dict)


class NodeBindingDefinition(IRModel):
    kind: Literal["node"] = "node"
    symbol_id: str = Field(min_length=1)
    debug_name: str | None = None
    component: str
    build_key: Value
    properties: dict[str, Value] = Field(default_factory=dict)
    annotations: tuple[AnnotationDefinition, ...] = ()


class EdgeBindingDefinition(IRModel):
    kind: Literal["edge"] = "edge"
    symbol_id: str = Field(min_length=1)
    debug_name: str | None = None
    component: str
    build_key: Value
    source_build_key: Value
    target_build_key: Value
    properties: dict[str, Value] = Field(default_factory=dict)
    annotations: tuple[AnnotationDefinition, ...] = ()


BindingDefinition = Annotated[NodeBindingDefinition | EdgeBindingDefinition, Field(discriminator="kind")]


class SourceDefinition(IRModel):
    table: str = Field(min_length=1)
    location: str = Field(min_length=1)
    format: Literal["csv", "json", "parquet"]
    credential_reference: str | None = None
    version: str | None = None
    annotations: tuple[AnnotationDefinition, ...] = ()


class BlueprintModule(IRModel):
    """A serialisable workflow-module selection in a build blueprint."""
    module_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    module_import: str = Field(min_length=1)
    module_qualname: str = Field(min_length=1)
    configuration: JsonValue | None = None


class LegacyBuildBlueprint(IRModel):
    components: tuple[ComponentDefinition, ...] = Field(min_length=1)
    projections: tuple[ProjectionDefinition, ...] = ()
    bindings: tuple[BindingDefinition, ...] = Field(min_length=1)
    sources: tuple[SourceDefinition, ...] = ()
    modules: tuple[BlueprintModule, ...] = ()


# Workflow contracts use the version-2 declaration graph.  The legacy models
# above remain temporarily importable for old serialized fixtures only.
BuildBlueprint = CanonicalBuildBlueprint


class ModuleReference(IRModel):
    module_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    import_module: str = Field(min_length=1)
    class_qualname: str = Field(min_length=1)
    implementation_version: str = Field(min_length=1)
    priority: int = Field(ge=0)
    configuration: JsonValue | None = None


class RuntimeFieldDefinition(IRModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    description: str = Field(min_length=1)
    required: bool = True
    value_type: Literal["string", "integer", "number", "boolean", "json"] = "string"
    secret: bool = False


class ModuleDefinition(IRModel):
    reference: ModuleReference
    runtime_fields: tuple[RuntimeFieldDefinition, ...] = ()


class ArtifactRole(IRModel):
    namespace: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1)


class OutputSlot(IRModel):
    slot_id: str = Field(min_length=1)
    artifact_role: ArtifactRole


class SingleInputSlot(IRModel):
    kind: Literal["single"] = "single"
    slot_id: str = Field(min_length=1)


class CollectionInputSlot(IRModel):
    kind: Literal["collection"] = "collection"
    slot_id: str = Field(min_length=1)


InputSlot = Annotated[SingleInputSlot | CollectionInputSlot, Field(discriminator="kind")]


class WorkflowStep(IRModel):
    step_id: str = Field(min_length=1)
    module_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    assembly_preference: Literal["eager", "deferred"] = "eager"
    inputs: tuple[InputSlot, ...] = ()
    outputs: tuple[OutputSlot, ...] = ()
    payload: JsonValue | None = None


class Connection(IRModel):
    input_slot_id: str = Field(min_length=1)
    output_slot_id: str = Field(min_length=1)


class WorkflowDefinition(IRModel):
    modules: tuple[ModuleDefinition, ...] = Field(min_length=1)
    steps: tuple[WorkflowStep, ...] = Field(min_length=1)
    connections: tuple[Connection, ...] = ()

    @model_validator(mode="after")
    def validate_workflow(self) -> Self:
        module_ids = [module.reference.module_id for module in self.modules]
        if len(module_ids) != len(set(module_ids)): raise ValueError("workflow module IDs must be unique")
        step_ids = [step.step_id for step in self.steps]
        if len(step_ids) != len(set(step_ids)): raise ValueError("workflow step IDs must be unique")
        if any(step.module_id not in module_ids for step in self.steps): raise ValueError("workflow step references an unknown module")
        inputs = {slot.slot_id: slot for step in self.steps for slot in step.inputs}
        outputs = {slot.slot_id for step in self.steps for slot in step.outputs}
        if len(inputs) != sum(len(step.inputs) for step in self.steps): raise ValueError("workflow input slot IDs must be unique")
        if len(outputs) != sum(len(step.outputs) for step in self.steps): raise ValueError("workflow output slot IDs must be unique")
        counts: dict[str, int] = {}
        for connection in self.connections:
            if connection.input_slot_id not in inputs or connection.output_slot_id not in outputs: raise ValueError("workflow connection references an unknown slot")
            counts[connection.input_slot_id] = counts.get(connection.input_slot_id, 0) + 1
        for slot_id, slot in inputs.items():
            if isinstance(slot, SingleInputSlot) and counts.get(slot_id) != 1: raise ValueError(f"single input {slot_id!r} requires exactly one connection")
        return self


class BuildSettings(IRModel):
    duckdb_threads: int | None = Field(default=None, ge=1)


class SourceOverride(IRModel):
    table: str = Field(min_length=1)
    original: CanonicalSourceDefinition | None = None
    override: CanonicalSourceDefinition


class BuildOverrides(IRModel):
    sources: tuple[SourceOverride, ...] = ()


def _decode_contract_blueprint(value: Any) -> BuildBlueprint:
    return BuildBlueprint.model_validate(value)


def _encode_contract_blueprint(value: BuildBlueprint) -> dict[str, Any]:
    return value.model_dump(mode="json")


ContractBlueprint = Annotated[
    BuildBlueprint,
    PlainValidator(_decode_contract_blueprint),
    PlainSerializer(_encode_contract_blueprint, return_type=dict[str, Any]),
]


class BuildContract(IRModel):
    # Pydantic's generic dataclass handling erases concrete expression-node
    # subclasses.  This boundary deliberately delegates to the canonical v2
    # blueprint codec instead.
    blueprint: ContractBlueprint
    blueprint_fingerprint: str = Field(min_length=1)
    sources: tuple[CanonicalSourceDefinition, ...] = Field(min_length=1)
    settings: BuildSettings = Field(default_factory=BuildSettings)
    overrides: BuildOverrides = Field(default_factory=BuildOverrides)
    workflow_fingerprint: str = Field(min_length=1)
    workflow: WorkflowDefinition
