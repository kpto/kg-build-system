"""Author-facing model of the table language."""
from __future__ import annotations

from .declarations import (
    ComputedStruct, Projection, ProjectionMeta, ProjectionOptions, Struct,
    StructOptions, StructOptionsTemplate, StructTemplate, Table, TableGroup,
    TableGroupOptions, TableOptions, is_concrete_table, is_table_group,
    projection_base, projection_row_source,
)
from .fields import Field, computed_field, field, projection_field
from .row_sources import (
    DerivedRowSource, JoinHow, RelationRowSource, RowSource, shape_context,
)
from .shapes import ShapeField
from .sources import (
    BoundSource, BoundTable, BoundTableGroup, DataSourceConfig, InputFormat,
    SourceBindingOptions, bind_source,
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
