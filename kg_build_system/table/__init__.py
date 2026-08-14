"""Logical data-contract authoring surface."""

from ..types import Array, CustomDataType, Nullable
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
    Table,
    TableGroup,
    TableGroupOptions,
    TableOptions,
    TableTemplate,
    TableTemplateOptions,
)
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
    "Field",
    "FieldMetadata",
    "InputFormat",
    "Nullable",
    "Projection",
    "ProjectionField",
    "ProjectionFieldMetadata",
    "ProjectionOptions",
    "SourceBindingOptions",
    "Struct",
    "StructOptions",
    "Table",
    "TableGroup",
    "TableGroupOptions",
    "TableOptions",
    "TableTemplate",
    "TableTemplateOptions",
    "bind_source",
    "declared_fields",
    "declared_projection_fields",
    "field",
    "projection_field",
]
