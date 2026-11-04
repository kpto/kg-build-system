"""The data language: logical data declarations and row-source values.

The authoring model lives in
:mod:`kg_build_system.distribution.languages.data.model.public`; the authoring
functions live in
:mod:`kg_build_system.distribution.languages.data.service.public`.

Example:
    ```python
    from kg_build_system import Asset, AssetOptions, Field, Table, field

    class Estate(Asset):
        options = AssetOptions(...)

    class Site(Table[Estate]):
        site_id: Field[str] = field()
    ```
"""
from __future__ import annotations

from .model.public import (
    ComputedStruct, DerivedRowSource, Field, JoinHow, Projection, ProjectionMeta,
    ProjectionOptions, RelationRowSource, RowSource, ShapeField, Struct,
    StructOptions, StructOptionsTemplate, StructTemplate, Table, TableGroup,
    TableGroupOptions, TableOptions, is_concrete_table, is_table_group,
)
from .service.public import (
    computed_field, field, projection_base, projection_field,
    projection_row_source, shape_context,
)

__all__ = [
    "ComputedStruct", "DerivedRowSource", "Field", "JoinHow", "Projection",
    "ProjectionMeta", "ProjectionOptions", "RelationRowSource", "RowSource",
    "ShapeField", "Struct", "StructOptions", "StructOptionsTemplate",
    "StructTemplate", "Table", "TableGroup", "TableGroupOptions",
    "TableOptions", "computed_field", "field", "is_concrete_table",
    "is_table_group", "projection_base", "projection_field",
    "projection_row_source", "shape_context",
]
