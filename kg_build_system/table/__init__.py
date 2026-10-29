"""Author-facing logical data-contract declarations.

A graph author writes ``Table``, ``Struct``, ``ComputedStruct``,
``Projection``, ``TableGroup`` and their fields here. The framework-internal
declaration and row-source interface is
:mod:`kg_build_system.table.interfaces`; the compilation IR is
:mod:`kg_build_system.table.ir`.
"""
from __future__ import annotations

from .declarations import bind_source
from .fields import Field, computed_field, field
from .models import (
    BoundSource,
    BoundTable,
    BoundTableGroup,
    ComputedStruct,
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
    TableGroupOptions,
    TableOptions,
)
from .rows import DerivedRowSource, RelationRowSource, RowSource

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
]
