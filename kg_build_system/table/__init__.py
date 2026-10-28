"""Logical data-contract authoring surface."""

from ..types import Array, CustomDataType, Nullable, Shape
from .declarations import bind_source, field, projection_field
from .fields import AuthoringDataType, Field, FieldMetadata, declared_fields
from .models import (
    BoundSource,
    BoundTable,
    BoundTableGroup,
    DataSourceConfig,
    InputFormat,
    Projection,
    ProjectionOptions,
    SourceBindingOptions,
    Struct,
    StructOptions,
    StructOptionsTemplate,
    StructTemplate,
    Table,
    TableGroup,
    RowSource,
    TableGroupOptions,
    TableOptions,
)
from .rows import DerivedRowSource
from .projections import (
    ProjectionField,
    ProjectionFieldMetadata,
    declared_projection_fields,
)

__all__ = [
    "Array",
    "AuthoringDataType",
    "BoundSource",
    "BoundTable",
    "BoundTableGroup",
    "CustomDataType",
    "DataSourceConfig",
    "DerivedRowSource",
    "Field",
    "FieldMetadata",
    "InputFormat",
    "Nullable",
    "Projection",
    "ProjectionField",
    "ProjectionFieldMetadata",
    "ProjectionOptions",
    "RowSource",
    "Shape",
    "SourceBindingOptions",
    "Struct",
    "StructOptions",
    "StructOptionsTemplate",
    "StructTemplate",
    "Table",
    "TableGroup",
    "TableGroupOptions",
    "TableOptions",
    "bind_source",
    "declared_fields",
    "declared_projection_fields",
    "field",
    "projection_field",
]
