"""The data language: logical data declarations and row-source values.

Example:
    ```python
    from kg_build_system import Asset, AssetOptions, Field, SourceRelation, field

    class Estate(Asset):
        options = AssetOptions(...)

    class Site(SourceRelation[Estate]):
        site_id: Field[str] = field()
    ```
"""
from __future__ import annotations

from .model.public import (
    ComputedStruct, Contract, Definition, DerivedRowSource, Field,
    FieldDefinition, JoinHow, DerivedRelation, DerivedRelationMeta,
    DerivedRelationOptions, RelationRowSource, RowSource, RowSourceProvider,
    ShapeField, Stage, StageMeta, StageOptions, StageRowSource, Struct,
    StructOptions, StructOptionsTemplate, StructTemplate, SourceRelation,
    SourceRelationGroup, SourceRelationGroupOptions, SourceRelationOptions,
    is_concrete_source_relation, is_source_relation_group,
)
from .service.public import computed_field, field, derived_relation_row_source

__all__ = [
    "ComputedStruct", "Contract", "Definition", "DerivedRowSource", "Field",
    "FieldDefinition", "JoinHow", "DerivedRelation", "DerivedRelationMeta",
    "DerivedRelationOptions", "RelationRowSource", "RowSource",
    "RowSourceProvider", "ShapeField", "Stage", "StageMeta", "StageOptions",
    "StageRowSource", "Struct", "StructOptions", "StructOptionsTemplate",
    "StructTemplate", "SourceRelation", "SourceRelationGroup",
    "SourceRelationGroupOptions", "SourceRelationOptions", "computed_field",
    "field", "is_concrete_source_relation", "is_source_relation_group",
    "derived_relation_row_source",
]
