"""Author-facing model of the data language."""
from __future__ import annotations

from .contract import Contract, Definition
from .declarations import (
    ComputedStruct, DerivedRelation, DerivedRelationMeta, DerivedRelationOptions, Struct,
    StructOptions, StructOptionsTemplate, StructTemplate, SourceRelation, SourceRelationGroup,
    SourceRelationGroupOptions, SourceRelationOptions, Stage, StageMeta, StageOptions,
    is_concrete_source_relation, is_source_relation_group,
)
from .fields import (
    DeclaredValue, Field, FieldDefinition, NullableComputedField, ScalarValue,
)
from .row_sources import (
    DerivedRowSource, JoinHow, RelationRowSource, RowSource, RowSourceProvider,
    StageRowSource,
)
from .shapes import ShapeField

__all__ = [
    "ComputedStruct", "Contract", "DeclaredValue", "Definition",
    "DerivedRowSource", "Field", "FieldDefinition", "JoinHow",
    "NullableComputedField", "ScalarValue", "DerivedRelation", "DerivedRelationMeta",
    "DerivedRelationOptions", "RelationRowSource", "RowSource",
    "RowSourceProvider", "ShapeField", "Stage", "StageMeta", "StageOptions",
    "StageRowSource", "Struct", "StructOptions", "StructOptionsTemplate",
    "StructTemplate", "SourceRelation", "SourceRelationGroup",
    "SourceRelationGroupOptions", "SourceRelationOptions",
    "is_concrete_source_relation", "is_source_relation_group",
]
