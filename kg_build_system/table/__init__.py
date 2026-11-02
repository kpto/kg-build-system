"""Author-facing logical data declarations and row-source values.

A graph author writes ``Table``, ``Struct``, ``ComputedStruct``, ``Projection``,
``TableGroup`` and their fields here. The public surface is
:mod:`kg_build_system.table.public`; the framework-internal interface and the
compilation IR are internal.

Example:
    ```python
    from kg_build_system import Field, Table, field

    class Site(Table):
        site_id: Field[str] = field()
    ```
"""
from __future__ import annotations

from .public import (
    BoundSource,
    BoundTable,
    BoundTableGroup,
    ComputedStruct,
    DataSourceConfig,
    DerivedRowSource,
    Field,
    InputFormat,
    Projection,
    ProjectionOptions,
    RelationRowSource,
    RowSource,
    ShapeField,
    SourceBindingOptions,
    Struct,
    StructOptions,
    StructOptionsTemplate,
    StructTemplate,
    Table,
    TableGroup,
    TableGroupOptions,
    TableOptions,
    bind_source,
    computed_field,
    field,
    projection_field,
)


__all__ = [
    "BoundSource",
    "BoundTable",
    "BoundTableGroup",
    "ComputedStruct",
    "DataSourceConfig",
    "DerivedRowSource",
    "Field",
    "InputFormat",
    "Projection",
    "ProjectionOptions",
    "RelationRowSource",
    "RowSource",
    "ShapeField",
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
    "computed_field",
    "field",
    "projection_field",
]
