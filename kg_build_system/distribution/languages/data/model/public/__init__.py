"""Author-facing model of the data language."""
from __future__ import annotations

from .declarations import (
    ComputedStruct, Projection, ProjectionMeta, ProjectionOptions, Struct,
    StructOptions, StructOptionsTemplate, StructTemplate, Table, TableGroup,
    TableGroupOptions, TableOptions, is_concrete_table, is_table_group,
)
from .fields import Field
from .row_sources import (
    DerivedRowSource, JoinHow, RelationRowSource, RowSource,
)
from .shapes import ShapeField
from .sources import (
    BoundSource, BoundTable, BoundTableGroup, DataSourceConfig, InputFormat,
    SourceBindingOptions,
)

__all__ = [
    "BoundSource", "BoundTable", "BoundTableGroup", "ComputedStruct",
    "DataSourceConfig", "DerivedRowSource", "Field", "InputFormat", "JoinHow",
    "Projection", "ProjectionMeta", "ProjectionOptions", "RelationRowSource",
    "RowSource", "ShapeField", "SourceBindingOptions", "Struct", "StructOptions",
    "StructOptionsTemplate", "StructTemplate", "Table", "TableGroup",
    "TableGroupOptions", "TableOptions", "is_concrete_table", "is_table_group",
]
