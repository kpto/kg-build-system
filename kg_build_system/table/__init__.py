"""Author-facing logical data declarations and row-source values.

A graph author writes ``Table``, ``Struct``, ``ComputedStruct``, ``Projection``,
``TableGroup`` and their fields here. The framework-internal declaration and
row-source interface is :mod:`kg_build_system.table.interfaces`; the compilation
IR is :mod:`kg_build_system.table.ir`.

The public surface composes the declaration layer (``models``), the field
constructors (``fields``), source binding (``declarations``) and the row-source
algebra (``row_sources``). It is not a re-export of one implementation module.

Compatibility: ``Projection`` may be pinned with ``Projection(rows)`` or left
unpinned and declare outputs with ``projection_field(...)``. Both forms lower to
the same ``ProjectionIR``; the unpinned form derives its scan from its output
expressions.
"""
from __future__ import annotations

from .declarations import bind_source
from .fields import (
    Field, computed_field, field, projection_field,
)
from .models import (
    BoundSource, BoundTable, BoundTableGroup, ComputedStruct, DataSourceConfig,
    InputFormat, Projection, ProjectionOptions, SourceBindingOptions, Struct,
    StructOptions, StructOptionsTemplate, StructTemplate, Table, TableGroup,
    TableGroupOptions, TableOptions, projection_base,
)
from .row_sources import (
    DerivedRowSource, RelationRowSource, RowSource, ShapeField, as_row_source,
    declaration_source_name, derive_row_source, make_row_shape,
    plan_expressions, plan_fields, plan_inputs, plan_scan_sources,
    plan_shape_source_name, projection_attrs, record_shape, record_shape_type,
    retarget_expression_ir, row_source_key, row_source_plan_ir, shape_context,
    shape_fields, shape_source_name, shape_view, union_shape_fields,
)

__all__ = [
    "BoundSource", "BoundTable", "BoundTableGroup", "ComputedStruct",
    "DataSourceConfig", "DerivedRowSource", "Field", "InputFormat",
    "Projection", "ProjectionOptions", "RelationRowSource", "RowSource",
    "ShapeField", "SourceBindingOptions", "Struct", "StructOptions",
    "StructOptionsTemplate", "StructTemplate", "Table", "TableGroup",
    "TableGroupOptions", "TableOptions", "as_row_source", "bind_source",
    "computed_field", "declaration_source_name", "derive_row_source", "field",
    "make_row_shape", "plan_expressions", "plan_fields", "plan_inputs",
    "plan_scan_sources", "plan_shape_source_name", "projection_attrs",
    "projection_base", "projection_field", "record_shape", "record_shape_type",
    "retarget_expression_ir", "row_source_key", "row_source_plan_ir",
    "shape_context", "shape_fields", "shape_source_name", "shape_view",
    "union_shape_fields",
]
