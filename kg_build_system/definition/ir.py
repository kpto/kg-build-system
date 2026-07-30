"""Pydantic models for the canonical compiler IR.

These models deliberately contain no lowering or execution logic.  Their
validators enforce the structural invariants shared by every target.
"""
from __future__ import annotations

from typing import Annotated, Literal, Self
from pydantic import BaseModel, ConfigDict, Field, model_validator

class IRModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

class ValueType(IRModel):
    kind: Literal["scalar", "collection", "unknown"]
    name: str
    nullable: bool = False
    item_nullable: bool = False
    item: str | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> Self:
        if self.kind == "collection" and self.item is None: raise ValueError("collection types require an item type")
        if self.kind != "collection" and (self.item is not None or self.item_nullable): raise ValueError("only collection types may declare item metadata")
        return self

class FieldReference(IRModel):
    kind: Literal["field"] = "field"
    table: str = Field(min_length=1)
    path: tuple[str, ...] = Field(min_length=1)
    value_type: ValueType
    collection_paths: tuple[tuple[str, ...], ...] = ()

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

    @model_validator(mode="after")
    def validate_operation(self) -> Self:
        if self.op == "cast" and not self.sql_type: raise ValueError("cast requires sql_type")
        if self.op != "cast" and self.sql_type is not None: raise ValueError("sql_type is only valid for cast")
        if self.op == "struct_field" and not self.field_name: raise ValueError("struct_field requires field_name")
        if self.op != "struct_field" and self.field_name is not None: raise ValueError("field_name is only valid for struct_field")
        if self.op == "lookup_one" and len(self.args) != 3: raise ValueError("lookup_one requires key, match, and value")
        if self.op == "expand" and self.value_type.kind != "scalar": raise ValueError("expand resolves to a scalar item")
        return self

Value = Annotated[FieldReference | LiteralValue | Operation, Field(discriminator="kind")]
Operation.model_rebuild()

class PropertyDefinition(IRModel):
    name: str = Field(min_length=1)
    value_type: ValueType
    nullable: bool

class ComponentDefinition(IRModel):
    name: str = Field(min_length=1)
    kind: Literal["node", "edge"]
    properties: tuple[PropertyDefinition, ...] = ()
    source: str | None = None
    target: str | None = None

    @model_validator(mode="after")
    def validate_edge_endpoints(self) -> Self:
        if self.kind == "edge" and (not self.source or not self.target): raise ValueError("edge components require source and target")
        if self.kind == "node" and (self.source or self.target): raise ValueError("node components cannot declare endpoints")
        return self

class ProjectionDefinition(IRModel):
    name: str = Field(min_length=1)
    fields: dict[str, Value] = Field(min_length=1)

class NodeBindingDefinition(IRModel):
    kind: Literal["node"] = "node"
    symbol_id: str = Field(min_length=1)
    debug_name: str | None = None
    component: str
    build_key: Value
    properties: dict[str, Value] = Field(default_factory=dict)

class EdgeBindingDefinition(IRModel):
    kind: Literal["edge"] = "edge"
    symbol_id: str = Field(min_length=1)
    debug_name: str | None = None
    component: str
    build_key: Value
    source_build_key: Value
    target_build_key: Value
    properties: dict[str, Value] = Field(default_factory=dict)

BindingDefinition = Annotated[NodeBindingDefinition | EdgeBindingDefinition, Field(discriminator="kind")]

class PostProcessingDefinition(IRModel):
    """Portable graph normalisation semantics, declared on a blueprint."""
    operations: tuple[Literal["collapse_exact_duplicates", "merge_compatible_facts", "reject_conflicting_non_null_values", "validate_edge_endpoints"], ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_operations(self) -> Self:
        required = {
            "collapse_exact_duplicates", "merge_compatible_facts",
            "reject_conflicting_non_null_values", "validate_edge_endpoints",
        }
        if set(self.operations) != required or len(self.operations) != len(required):
            raise ValueError("the MVP normalisation pipeline must declare each supported operation exactly once")
        return self

class BlueprintSymbol(IRModel):
    id: str = Field(min_length=1)
    kind: Literal["component", "property", "table", "projection", "projection_field", "binding", "source", "post_processing"]
    path: str = Field(min_length=1)
    source_file: str | None = None
    source_line: int | None = Field(default=None, ge=1)

class BuildBlueprint(IRModel):
    """Complete, reusable graph definition independent of a concrete target."""
    components: tuple[ComponentDefinition, ...] = Field(min_length=1)
    projections: tuple[ProjectionDefinition, ...] = ()
    bindings: tuple[BindingDefinition, ...] = Field(min_length=1)
    default_sources: tuple[SourceDefinition, ...] = ()
    post_processing: PostProcessingDefinition
    symbols: tuple[BlueprintSymbol, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_references(self) -> Self:
        components = {component.name: component for component in self.components}
        if len(components) != len(self.components): raise ValueError("component names must be unique")
        for binding in self.bindings:
            component = components.get(binding.component)
            if component is None: raise ValueError(f"binding references unknown component {binding.component!r}")
            if component.kind != binding.kind: raise ValueError(f"binding kind does not match component {binding.component!r}")
            unknown = set(binding.properties) - {prop.name for prop in component.properties}
            if unknown: raise ValueError(f"binding has unknown properties: {sorted(unknown)}")
        binding_symbols = [binding.symbol_id for binding in self.bindings]
        if len(binding_symbols) != len(set(binding_symbols)): raise ValueError("binding symbol IDs must be unique")
        source_tables = [source.table for source in self.default_sources]
        if len(source_tables) != len(set(source_tables)): raise ValueError("a blueprint may bind each logical table only once")
        symbol_ids = [symbol.id for symbol in self.symbols]
        if len(symbol_ids) != len(set(symbol_ids)): raise ValueError("blueprint symbol IDs must be unique")
        return self

class SourceDefinition(IRModel):
    table: str = Field(min_length=1)
    location: str = Field(min_length=1)
    format: Literal["csv", "json", "parquet"]
    credential_reference: str | None = None
    version: str | None = None

class FileTargetDefinition(IRModel):
    kind: Literal["file"] = "file"
    location: str = Field(min_length=1)

class BindingExecutionPlan(IRModel):
    """A self-contained, target-specific record stream for one binding."""
    binding_index: int = Field(ge=0)
    binding_symbol: str = Field(min_length=1)
    component: str = Field(min_length=1)
    kind: Literal["node", "edge"]
    sql: str = Field(min_length=1)

class ComponentPostProcessPlan(IRModel):
    """DuckDB relations that normalise every record for one graph component."""
    component: str = Field(min_length=1)
    kind: Literal["node", "edge"]
    raw_view: str = Field(min_length=1)
    normalised_view: str = Field(min_length=1)
    raw_sql: str = Field(min_length=1)
    normalised_sql: str = Field(min_length=1)

class DiagnosticPlan(IRModel):
    """A query that yields structural graph-build failures."""
    code: Literal["null_build_key", "null_edge_endpoint", "conflicting_value", "missing_edge_endpoint"]
    sql: str = Field(min_length=1)

class DuckDBExecutionStep(IRModel):
    """One inspectable, composable DuckDB execution step in a build contract."""
    id: str = Field(min_length=1)
    kind: Literal["relation", "diagnostic"]
    stage: Literal["binding", "binding_aggregation", "post_processing", "validation"]
    inputs: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    sql: str = Field(min_length=1)
    relation: str | None = None
    component: str | None = None
    materialization: Literal["temporary_table", "view", "none"] = "none"
    symbols: tuple[str, ...] = Field(min_length=1)
    diagnostic_code: Literal["null_build_key", "null_edge_endpoint", "conflicting_value", "missing_edge_endpoint"] | None = None

    @model_validator(mode="after")
    def validate_step(self) -> Self:
        if self.kind == "relation" and not self.relation: raise ValueError("relation steps require a relation name")
        if self.kind == "diagnostic" and self.relation is not None: raise ValueError("diagnostic steps cannot define a relation")
        if self.kind == "relation" and self.materialization == "none": raise ValueError("relation steps require materialization")
        if self.kind == "diagnostic" and (self.materialization != "none" or self.diagnostic_code is None): raise ValueError("diagnostic steps require a code and no materialization")
        return self

class ContractOutput(IRModel):
    relation: str = Field(min_length=1)
    component: str = Field(min_length=1)
    kind: Literal["node", "edge"]

class BuildSettings(IRModel):
    """Permitted concrete composition overrides for one compilation."""
    source_overrides: tuple[SourceDefinition, ...] = ()
    duckdb_threads: int | None = Field(default=None, ge=1)

class DebugSymbolReference(IRModel):
    artifact: str = Field(min_length=1)
    symbols: tuple[str, ...] = Field(min_length=1)

class BuildContract(IRModel):
    """Target-specific, reproducible DuckDB execution artifact."""
    blueprint: BuildBlueprint
    blueprint_fingerprint: str = Field(min_length=1)
    sources: tuple[SourceDefinition, ...] = Field(min_length=1)
    target: FileTargetDefinition
    requested_settings: BuildSettings = Field(default_factory=BuildSettings)
    effective_settings: BuildSettings = Field(default_factory=BuildSettings)
    execution_plan_fingerprint: str = Field(min_length=1)
    execution_plan: tuple[DuckDBExecutionStep, ...] = Field(min_length=1)
    outputs: tuple[ContractOutput, ...] = Field(min_length=1)
    debug_symbols: tuple[DebugSymbolReference, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_sources(self) -> Self:
        tables = [source.table for source in self.sources]
        if len(set(tables)) != len(tables): raise ValueError("a build may bind each logical table only once")
        steps = {step.id: step for step in self.execution_plan}
        if len(steps) != len(self.execution_plan): raise ValueError("execution-step IDs must be unique")
        relations = {step.relation for step in self.execution_plan if step.relation}
        for step in self.execution_plan:
            if any(dependency not in steps for dependency in step.depends_on): raise ValueError("execution step references an unknown dependency")
            if any(relation not in relations for relation in step.inputs): raise ValueError("execution step references an unknown relation")
        binding_symbols = {binding.symbol_id for binding in self.blueprint.bindings}
        planned_symbols = {symbol for step in self.execution_plan if step.stage == "binding" for symbol in step.symbols}
        if binding_symbols != planned_symbols: raise ValueError("execution steps must cover every blueprint binding")
        components = {(output.component, output.kind) for output in self.outputs}
        expected = {(binding.component, binding.kind) for binding in self.blueprint.bindings}
        if components != expected:
            raise ValueError("post-processing plans must cover every bound component")
        return self
