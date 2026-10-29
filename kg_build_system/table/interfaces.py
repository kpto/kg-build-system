"""Framework-internal interface of the data-contract domain.

Other subpackages import the declaration types they must inspect, the bound
source values they must resolve, the row-source values and plan helpers, and the
IR codecs here. A graph author writes the names re-exported by
:mod:`kg_build_system.table`; the compilation IR is
:mod:`kg_build_system.table.ir`.
"""
from __future__ import annotations

from .declarations import (
    bind_source,
    group_tables,
    resolve_bound_source,
)
from .fields import (
    AuthoringDataType,
    Field,
    FieldMetadata,
    computed_field,
    declared_fields,
    field,
)
from .ir import StructIR
from .ir_codec import decode_row_source_plan, encode_row_source_plan
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
    is_concrete_table,
    is_table_group,
)
from .rows import (
    DerivedRowSource,
    RelationRowSource,
    RowSource,
    ShapeField,
    as_row_source,
    declaration_source_name,
    derive_row_source,
    make_row_shape,
    plan_expressions,
    plan_fields,
    plan_inputs,
    plan_scan_sources,
    plan_shape_source_name,
    record_shape,
    record_shape_type,
    retarget_expression_ir,
    row_source_key,
    row_source_plan_ir,
    shape_context,
    shape_fields,
    shape_source_name,
    union_shape_fields,
)


def struct_type_key(struct: StructIR) -> tuple[str, str] | None:
    """Recover the ``(module, qualname)`` identity a struct type refers to.

    A ``StructTypeIR`` names a struct by module and qualified name, and the
    blueprint stores that same identity only inside the struct's symbol ID.
    Two modules may declare same-named structs — names are display, identity is
    this pair — so struct declarations are never resolved by name alone.
    """
    prefix = "python:struct:"
    if not struct.symbol_id.startswith(prefix):
        return None
    module, _, qualname = struct.symbol_id[len(prefix):].partition(":")
    return (module, qualname) if module and qualname else None


__all__ = [
    "AuthoringDataType",
    "BoundSource",
    "BoundTable",
    "BoundTableGroup",
    "ComputedStruct",
    "DataSourceConfig",
    "DerivedRowSource",
    "Field",
    "FieldMetadata",
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
    "as_row_source",
    "bind_source",
    "computed_field",
    "declaration_source_name",
    "declared_fields",
    "decode_row_source_plan",
    "derive_row_source",
    "encode_row_source_plan",
    "field",
    "group_tables",
    "is_concrete_table",
    "is_table_group",
    "make_row_shape",
    "plan_expressions",
    "plan_fields",
    "plan_inputs",
    "plan_scan_sources",
    "plan_shape_source_name",
    "record_shape",
    "record_shape_type",
    "resolve_bound_source",
    "retarget_expression_ir",
    "row_source_key",
    "row_source_plan_ir",
    "shape_context",
    "shape_fields",
    "shape_source_name",
    "struct_type_key",
    "union_shape_fields",
]
