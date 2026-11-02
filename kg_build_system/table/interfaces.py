"""Framework-internal interface of the data-contract domain.

Other subpackages import declaration values, source bindings, row-source values
and plan helpers, the data IR codec and the ``data`` language here. A graph
author writes the names re-exported by :mod:`kg_build_system.table`.
"""
from __future__ import annotations

from .declarations import bind_source, group_tables, resolve_bound_source
from .fields import (
    AuthoringDataType, Field, FieldMetadata, FieldSpec, computed_field,
    declared_fields, field, projection_field, resolve_field_specs,
)
from .ir import (
    DataIR, FieldIR, JoinHow, ProjectionFieldIR, ProjectionIR, RowDistinctIR,
    RowFilterIR, RowGroupByIR, RowJoinIR, RowOrderByIR, RowOrderKeyIR,
    RowScanIR, RowSourcePlanIR, RowUnionIR, SourceIR, StructIR, TableIR,
    decode_data_part, decode_row_source_plan, encode_data_part,
    encode_row_source_plan,
)
from .language import TableLanguage
from .models import (
    BoundSource, BoundTable, BoundTableGroup, ComputedStruct, DataSourceConfig,
    DeclarationSpec, InputFormat, Projection, ProjectionMeta, ProjectionOptions,
    SourceBindingOptions, Struct, StructOptions, StructOptionsTemplate,
    StructTemplate, Table, TableGroup, TableGroupOptions, TableOptions,
    is_concrete_table, is_table_group, projection_base, projection_row_source,
)
from .row_sources import (
    DerivedRowSource, RelationRowSource, RowSource, ShapeField, as_row_source,
    declaration_source_name, derive_row_source, make_row_shape,
    plan_expressions, plan_fields, plan_inputs, plan_scan_sources,
    plan_shape_source_name, projection_attrs, record_shape, record_shape_type,
    retarget_expression_ir, row_source_key, row_source_plan_ir, shape_context,
    shape_fields, shape_source_name, shape_view, union_shape_fields,
)


def struct_type_key(struct: StructIR) -> tuple[str, str] | None:
    """Recover the ``(module, qualname)`` identity a struct type refers to."""
    prefix = "python:struct:"
    if not struct.symbol_id.startswith(prefix):
        return None
    module, _, qualname = struct.symbol_id[len(prefix):].partition(":")
    return (module, qualname) if module and qualname else None


__all__ = [
    "AuthoringDataType", "BoundSource", "BoundTable", "BoundTableGroup",
    "ComputedStruct", "DataIR", "DataSourceConfig", "DeclarationSpec",
    "DerivedRowSource", "Field", "FieldIR", "FieldMetadata", "FieldSpec",
    "InputFormat", "JoinHow", "Projection", "ProjectionFieldIR",
    "ProjectionIR", "ProjectionMeta", "ProjectionOptions", "RelationRowSource",
    "RowDistinctIR", "RowFilterIR", "RowGroupByIR", "RowJoinIR",
    "RowOrderByIR", "RowOrderKeyIR", "RowScanIR", "RowSource",
    "RowSourcePlanIR", "RowUnionIR", "ShapeField", "SourceBindingOptions",
    "SourceIR", "Struct", "StructIR", "StructOptions", "StructOptionsTemplate",
    "StructTemplate", "Table", "TableGroup", "TableGroupOptions", "TableIR",
    "TableLanguage", "TableOptions", "as_row_source", "bind_source",
    "computed_field", "declaration_source_name", "declared_fields",
    "decode_data_part", "decode_row_source_plan", "derive_row_source",
    "encode_data_part", "encode_row_source_plan", "field", "group_tables",
    "is_concrete_table", "is_table_group", "make_row_shape",
    "plan_expressions", "plan_fields", "plan_inputs", "plan_scan_sources",
    "plan_shape_source_name", "projection_attrs", "projection_base",
    "projection_field", "projection_row_source", "record_shape",
    "record_shape_type", "resolve_bound_source", "resolve_field_specs",
    "retarget_expression_ir", "row_source_key", "row_source_plan_ir",
    "shape_context", "shape_fields", "shape_source_name", "shape_view",
    "struct_type_key", "union_shape_fields",
]
