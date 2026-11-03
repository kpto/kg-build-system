"""The table language: logical data declarations and row-source values.

The public surface is :mod:`kg_build_system.declaration.languages.table.public`.
The language adapter, DTO, transcription and rendering live under ``internal``.

Example:
    ```python
    from kg_build_system import Field, Table, field

    class Site(Table):
        site_id: Field[str] = field()
    ```
"""
from __future__ import annotations

from .public import (
    BoundSource, BoundTable, BoundTableGroup, ComputedStruct, DataSourceConfig,
    DerivedRowSource, Field, InputFormat, JoinHow, Projection, ProjectionMeta,
    ProjectionOptions, RelationRowSource, RowSource, ShapeField,
    SourceBindingOptions, Struct, StructOptions, StructOptionsTemplate,
    StructTemplate, Table, TableGroup, TableGroupOptions, TableOptions,
    bind_source, computed_field, field, is_concrete_table, is_table_group,
    projection_base, projection_field, projection_row_source, shape_context,
)

__all__ = [
    "BoundSource", "BoundTable", "BoundTableGroup", "ComputedStruct",
    "DataSourceConfig", "DerivedRowSource", "Field", "InputFormat", "JoinHow",
    "Projection", "ProjectionMeta", "ProjectionOptions", "RelationRowSource",
    "RowSource", "ShapeField", "SourceBindingOptions", "Struct", "StructOptions",
    "StructOptionsTemplate", "StructTemplate", "Table", "TableGroup",
    "TableGroupOptions", "TableOptions", "bind_source", "computed_field",
    "field", "is_concrete_table", "is_table_group", "projection_base",
    "projection_field", "projection_row_source", "shape_context",
]
