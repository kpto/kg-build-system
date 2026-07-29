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

class LiteralValue(IRModel):
    kind: Literal["literal"] = "literal"
    value: str | int | float | bool | None
    value_type: ValueType

class Operation(IRModel):
    kind: Literal["operation"] = "operation"
    op: Literal["concat", "coalesce", "cast", "deterministic_uuid", "expand"]
    args: tuple["Value", ...] = Field(min_length=1)
    value_type: ValueType
    sql_type: str | None = None

    @model_validator(mode="after")
    def validate_operation(self) -> Self:
        if self.op == "cast" and not self.sql_type: raise ValueError("cast requires sql_type")
        if self.op != "cast" and self.sql_type is not None: raise ValueError("sql_type is only valid for cast")
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
    component: str
    build_key: Value
    properties: dict[str, Value] = Field(default_factory=dict)

class EdgeBindingDefinition(IRModel):
    kind: Literal["edge"] = "edge"
    component: str
    build_key: Value
    source_build_key: Value
    target_build_key: Value
    properties: dict[str, Value] = Field(default_factory=dict)

BindingDefinition = Annotated[NodeBindingDefinition | EdgeBindingDefinition, Field(discriminator="kind")]

class CompiledGraphDefinition(IRModel):
    components: tuple[ComponentDefinition, ...] = Field(min_length=1)
    projections: tuple[ProjectionDefinition, ...] = ()
    bindings: tuple[BindingDefinition, ...] = Field(min_length=1)

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
        return self

class SourceDefinition(IRModel):
    table: str = Field(min_length=1)
    location: str = Field(min_length=1)
    format: Literal["csv", "parquet"]
    credential_reference: str | None = None
    version: str | None = None

class FileTargetDefinition(IRModel):
    kind: Literal["file"] = "file"
    location: str = Field(min_length=1)

class BuildPolicy(IRModel):
    null_key: Literal["error", "skip"] = "skip"
    duplicate_key: Literal["error", "skip"] = "skip"
    node_property_conflict: Literal["error", "first_wins", "last_wins"] = "error"
    edge_deduplication: Literal["error", "skip"] = "skip"
    generated_identity_namespace: str = Field(default="kg-build-system", min_length=1)

class CompiledBuildDefinition(IRModel):
    graph: CompiledGraphDefinition
    sources: tuple[SourceDefinition, ...] = Field(min_length=1)
    target: FileTargetDefinition
    policy: BuildPolicy = Field(default_factory=BuildPolicy)
    sql: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_sources(self) -> Self:
        tables = [source.table for source in self.sources]
        if len(set(tables)) != len(tables): raise ValueError("a build may bind each logical table only once")
        return self
