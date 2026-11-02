"""Framework-internal interface of the data-contract domain.

Other subpackages import declaration values, source bindings, row-source values
and plan helpers, the data IR codec and the ``data`` language here. A graph
author writes the names re-exported by :mod:`kg_build_system.table`.

The wrapper functions carry the reviewed interface: their signature, docstring
and example. Data classes, options and IR values are re-exported as data.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, TypeVar

from ...expressions.internal import BoolExpression
from ...expressions.internal.ir import ExpressionIR
from ...types.internal import Shape, Struct as StructDeclaration
from .._private.declarations import (
    DeclarationSpec,
    is_concrete_table as _is_concrete_table,
    is_table_group as _is_table_group,
    projection_base as _projection_base,
    projection_row_source as _projection_row_source,
)
from .._private.descriptors import (
    AuthoringDataType, FieldMetadata, FieldSpec,
    declared_fields as _declared_fields,
    resolve_field_specs as _resolve_field_specs,
)
from .._private.plans import (
    as_row_source as _as_row_source,
    declaration_source_name as _declaration_source_name,
    derive_row_source as _derive_row_source,
    plan_expressions as _plan_expressions,
    plan_fields as _plan_fields,
    plan_inputs as _plan_inputs,
    plan_scan_sources as _plan_scan_sources,
    plan_shape_source_name as _plan_shape_source_name,
    retarget_expression_ir as _retarget_expression_ir,
    row_source_key as _row_source_key,
    row_source_plan_ir as _row_source_plan_ir,
)
from .._private.shapes import (
    make_row_shape as _make_row_shape,
    projection_attrs as _projection_attrs,
    record_shape as _record_shape,
    record_shape_type as _record_shape_type,
    shape_fields as _shape_fields,
    shape_source_name as _shape_source_name,
    shape_view as _shape_view,
    union_shape_fields as _union_shape_fields,
)
from .._private.sources import (
    group_tables as _group_tables,
    resolve_bound_source as _resolve_bound_source,
)
from .ir import (
    DataIR, FieldIR, JoinHow, ProjectionFieldIR, ProjectionIR, RowDistinctIR,
    RowFilterIR, RowGroupByIR, RowJoinIR, RowOrderByIR, RowOrderKeyIR,
    RowScanIR, RowSourcePlanIR, RowUnionIR, SourceIR, StructIR, TableIR,
    decode_data_part as _decode_data_part,
    decode_row_source_plan as _decode_row_source_plan,
    encode_data_part as _encode_data_part,
    encode_row_source_plan as _encode_row_source_plan,
)

if TYPE_CHECKING:
    from ..public.declarations import (
        ComputedStruct, Projection, ProjectionMeta, ProjectionOptions, Struct,
        StructOptions, StructOptionsTemplate, StructTemplate, Table, TableGroup,
        TableGroupOptions, TableOptions,
    )
    from ..public.fields import Field
    from ..public.row_sources import DerivedRowSource, RelationRowSource, RowSource
    from ..public.shapes import ShapeField
    from ..public.sources import (
        BoundSource, BoundTable, BoundTableGroup, DataSourceConfig, InputFormat,
        SourceBindingOptions,
    )

S = TypeVar("S", bound=Shape)


# ---------------------------------------------------------------------------
# Fields


def declared_fields(owner: type[Any]) -> dict[str, Any]:
    """Return a declaration's resolved member descriptors keyed by attribute.

    The values are ``Field`` descriptors; the declaration is resolved once,
    while the class is created.

    Example:
        ```python
        from kg_build_system.table import Field, Table, field
        from kg_build_system.table.internal import declared_fields

        class Site(Table):
            site_id: Field[str] = field()

        assert set(declared_fields(Site)) == {"site_id"}
        ```
    """
    return _declared_fields(owner)


def resolve_field_specs(owner: type[Any], kind: str | None) -> tuple[FieldSpec, ...]:
    """Resolve a declaration class into its frozen ``FieldSpec`` values.

    ``kind`` is ``"source"`` for a table or source struct, ``"computed"`` for a
    projection or computed struct, or ``None`` for an unclassified owner.

    Example:
        ```python
        from kg_build_system.table import Field, Table, field
        from kg_build_system.table.internal import resolve_field_specs

        class Site(Table):
            site_id: Field[str] = field()

        specs = resolve_field_specs(Site, "source")
        ```
    """
    return _resolve_field_specs(owner, kind)


# ---------------------------------------------------------------------------
# Source binding


def group_tables(
    group: type,
    prefix: tuple[str, ...] = (),
    visited: tuple[type, ...] = (),
) -> tuple[tuple[type, tuple[str, ...]], ...]:
    """Flatten a group into concrete tables and canonical catalog paths.

    Each member is returned with the chain of group names above it followed by
    its own logical name. A repeated table or path is rejected.

    Example:
        ```python
        from kg_build_system.table.internal import group_tables

        members = group_tables(EstateGroup)
        ```
    """
    return _group_tables(group, prefix, visited)


def resolve_bound_source(source: BoundSource) -> tuple[BoundTable, ...]:
    """Expand one bound source into one ``BoundTable`` per concrete table.

    A direct table binding expands to itself; a group binding resolves its
    ``layout`` for every member.

    Example:
        ```python
        from kg_build_system import DataSourceConfig, bind_source
        from kg_build_system.table.internal import resolve_bound_source

        bound = bind_source(
            target=EstateGroup,
            config=DataSourceConfig(
                location="data", layout="{group_path}/{table_name}.json",
            ),
        )
        tables = resolve_bound_source(bound)
        ```
    """
    return _resolve_bound_source(source)


# ---------------------------------------------------------------------------
# Declarations and projections


def projection_base(row_source: Any) -> type["Projection"]:
    """Return a dynamic projection base carrying a row source and its fields.

    The base is not a final projection and does not enter the build by itself.
    Finish it with a named subclass and declare additional outputs normally.

    Example:
        ```python
        from kg_build_system import computed_field

        class SiteLabels(SiteTable.projection_base()):
            label = computed_field(SiteTable.name)
        ```
    """
    return _projection_base(row_source)


def projection_row_source(declaration: type["Projection"]) -> Any | None:
    """Return the plan a pinned projection owns, or derive one for old output.

    An unpinned projection derives its scan from the single logical source its
    output expressions read; several unrelated sources yield ``None``.

    Example:
        ```python
        from kg_build_system.table.internal import projection_row_source

        plan = projection_row_source(SiteProjection)
        ```
    """
    return _projection_row_source(declaration)


def is_concrete_table(cls: type[Any]) -> bool:
    """Return whether a class is a final, source-bindable ``Table``.

    A template, a base class or a projection is not a concrete table.

    Example:
        ```python
        from kg_build_system.table.internal import is_concrete_table

        assert is_concrete_table(SiteTable)
        ```
    """
    return _is_concrete_table(cls)


def is_table_group(cls: type[Any]) -> bool:
    """Return whether a class is a final ``TableGroup``.

    A ``TableGroup`` is a catalog, not a shape and not a row source.

    Example:
        ```python
        from kg_build_system.table.internal import is_table_group

        assert is_table_group(EstateGroup)
        ```
    """
    return _is_table_group(cls)


# ---------------------------------------------------------------------------
# Data IR codec


def encode_data_part(data: DataIR) -> dict[str, Any]:
    """Encode the data part into its canonical JSON-compatible mapping.

    The argument is usually a :class:`DataIR`; any value with the same four
    attributes accepted by the implementation works as well.

    Example:
        ```python
        from kg_build_system.table.internal import encode_data_part

        payload = encode_data_part(data)
        ```
    """
    return _encode_data_part(data)


def decode_data_part(value: Mapping[str, Any]) -> DataIR:
    """Decode the data part from its canonical JSON-compatible mapping.

    Unknown source formats and malformed members are rejected.

    Example:
        ```python
        from kg_build_system.table.internal import decode_data_part

        data = decode_data_part(payload)
        ```
    """
    return _decode_data_part(value)


def encode_row_source_plan(plan: RowSourcePlanIR) -> dict[str, Any]:
    """Encode one row-source plan into its canonical JSON-compatible mapping.

    The encoding is keyed by ``kind`` and is stable for equal plans.

    Example:
        ```python
        from kg_build_system.table import row_source_plan_ir
        from kg_build_system.table.internal import encode_row_source_plan

        document = encode_row_source_plan(
            row_source_plan_ir(SiteTable.row_source())
        )
        ```
    """
    return _encode_row_source_plan(plan)


def decode_row_source_plan(value: Mapping[str, Any]) -> RowSourcePlanIR:
    """Decode one row-source plan from its canonical JSON-compatible mapping.

    An unknown plan kind or join mode is rejected.

    Example:
        ```python
        from kg_build_system.table.internal import (
            decode_row_source_plan, encode_row_source_plan,
        )
        from kg_build_system.table.internal.ir import RowScanIR

        plan = decode_row_source_plan(encode_row_source_plan(RowScanIR("sites")))
        ```
    """
    return _decode_row_source_plan(value)


# ---------------------------------------------------------------------------
# Row-source values


def as_row_source(value: Any) -> Any:
    """Require and return a row-source value; declaration classes are rejected.

    Use ``Table.row_source()`` or ``Projection.row_source()`` to obtain a value
    from a declaration.

    Example:
        ```python
        from kg_build_system.table import as_row_source

        sites = as_row_source(SiteTable.row_source())
        ```
    """
    return _as_row_source(value)


def declaration_source_name(source: Any) -> str:
    """Return the logical relation name a table or projection writes.

    Example:
        ```python
        from kg_build_system.table import declaration_source_name

        name = declaration_source_name(SiteTable)
        ```
    """
    return _declaration_source_name(source)


def derive_row_source(
    parent: Any, predicate: BoolExpression, *, shape: Any | None = None,
) -> Any:
    """Add one filter predicate to a row source, preserving its shape.

    ``shape`` overrides the result shape when the predicate changes the row.

    Example:
        ```python
        from kg_build_system.table import derive_row_source

        active = derive_row_source(
            SiteTable.row_source(),
            SiteTable.name.alter_rows().drop_null().expression.equals("Depot"),
        )
        ```
    """
    return _derive_row_source(parent, predicate, shape=shape)


def shape_context(shape: type[S]) -> S:
    """Return a symbolic shape instance for use in an authoring lambda.

    The instance is not a data row; reading its fields produces selections.

    Example:
        ```python
        from kg_build_system.table import shape_context

        site = shape_context(SiteTable)
        ```
    """
    from ..public.row_sources import shape_context as implementation

    return implementation(shape)


# ---------------------------------------------------------------------------
# Shapes


def shape_fields(shape: type[Shape]) -> tuple[ShapeField, ...]:
    """Return a shape's members as ``ShapeField`` values.

    Declared and generated shapes both resolve their fields here.

    Example:
        ```python
        from kg_build_system.table import shape_fields

        fields = shape_fields(SiteTable)
        ```
    """
    return _shape_fields(shape)


def make_row_shape(
    source_name: str,
    fields: Sequence[ShapeField],
    *,
    allow_empty: bool = False,
) -> type[Shape]:
    """Create a generated row shape whose fields read one row-source key.

    ``source_name`` is the logical key the shape's fields reference.

    Example:
        ```python
        from kg_build_system.table import ShapeField, make_row_shape

        shape = make_row_shape(
            "sites",
            (ShapeField("site_id", "site_id", SiteTable.site_id.logical_type),),
        )
        ```
    """
    return _make_row_shape(source_name, fields, allow_empty=allow_empty)


def projection_attrs(shape: type[Shape]) -> dict[str, Any]:
    """Build projection-field descriptors for every member of a shape.

    The returned attributes name each field and reference the shape's logical
    source key, so they can seed a dynamic projection base.

    Example:
        ```python
        from kg_build_system.table import projection_attrs

        attrs = projection_attrs(SiteTable.shape)
        ```
    """
    return _projection_attrs(shape)


def record_shape(fields: Sequence[ShapeField]) -> type[StructDeclaration]:
    """Create a ``Struct`` mirror of a row shape, named from its members.

    The generated record identity is a pure function of the members, so a
    decoded plan produces the same identity without the authoring class.

    Example:
        ```python
        from kg_build_system.table import ShapeField, record_shape

        record = record_shape((
            ShapeField("site_id", "site_id", SiteTable.site_id.logical_type),
        ))
        ```
    """
    return _record_shape(fields)


def record_shape_type(fields: Sequence[ShapeField]) -> Any:
    """Return the struct type identity of a generated row shape.

    The identity is a ``StructType`` or ``StructTypeIR`` matching the member
    types.

    Example:
        ```python
        from kg_build_system.table import record_shape_type, shape_fields

        identity = record_shape_type(shape_fields(SiteTable))
        ```
    """
    return _record_shape_type(fields)


def shape_source_name(shape: type[Shape]) -> str:
    """Return the expression source a shape's own fields read.

    Example:
        ```python
        from kg_build_system.table import shape_source_name

        name = shape_source_name(SiteTable)
        ```
    """
    return _shape_source_name(shape)


def shape_view(source: type[Shape]) -> type[Shape]:
    """Create a row shape carrying a declaration's fields under its own name.

    A view has the same members and logical source as the input shape but no
    declaration identity of its own.

    Example:
        ```python
        from kg_build_system.table import shape_view

        view = shape_view(SiteTable)
        ```
    """
    return _shape_view(source)


def union_shape_fields(
    left: type[Shape], right: type[Shape],
) -> tuple[ShapeField, ...]:
    """Validate two union operands and return their shared shape.

    Shapes are compared by external name and full logical type, including
    nullability.

    Example:
        ```python
        from kg_build_system.table import union_shape_fields

        fields = union_shape_fields(SiteTable, ArchivedSiteTable)
        ```
    """
    return _union_shape_fields(left, right)


# ---------------------------------------------------------------------------
# Plans


def row_source_plan_ir(value: Any) -> RowSourcePlanIR:
    """Return the canonical plan IR a value row source authors.

    Example:
        ```python
        from kg_build_system.table import row_source_plan_ir

        plan = row_source_plan_ir(SiteTable.row_source())
        ```
    """
    return _row_source_plan_ir(value)


def row_source_key(plan: RowSourcePlanIR) -> str:
    """Return the stable logical key one plan's rows are read through.

    A scan uses its source name; a derived plan uses a content hash.

    Example:
        ```python
        from kg_build_system.table import row_source_key, row_source_plan_ir

        key = row_source_key(row_source_plan_ir(SiteTable.row_source()))
        ```
    """
    return _row_source_key(plan)


def plan_shape_source_name(plan: RowSourcePlanIR) -> str:
    """Return the source key the authoring shape's own fields refer to.

    Example:
        ```python
        from kg_build_system.table import plan_shape_source_name

        name = plan_shape_source_name(plan)
        ```
    """
    return _plan_shape_source_name(plan)


def plan_inputs(plan: RowSourcePlanIR) -> tuple[RowSourcePlanIR, ...]:
    """Return the direct child plans a plan reads.

    Example:
        ```python
        from kg_build_system.table import plan_inputs, row_source_plan_ir

        children = plan_inputs(row_source_plan_ir(SiteTable.row_source()))
        ```
    """
    return _plan_inputs(plan)


def plan_scan_sources(plan: RowSourcePlanIR) -> tuple[str, ...]:
    """Return every table or projection name a plan reads, in traversal order.

    Example:
        ```python
        from kg_build_system.table import plan_scan_sources

        names = plan_scan_sources(plan)
        ```
    """
    return _plan_scan_sources(plan)


def plan_expressions(plan: RowSourcePlanIR) -> tuple[ExpressionIR, ...]:
    """Return the expressions one plan node itself evaluates.

    A filter returns its predicate, a join its two keys, a group its keys and
    an order its order keys.

    Example:
        ```python
        from kg_build_system.table import plan_expressions

        expressions = plan_expressions(plan)
        ```
    """
    return _plan_expressions(plan)


def plan_fields(
    plan: RowSourcePlanIR,
    declarations: Mapping[str, Any],
) -> tuple[ShapeField, ...]:
    """Derive the row shape a plan produces from its IR and declarations.

    A scan must name a known logical source, union operands must agree and join
    keys must have the same base type.

    Example:
        ```python
        from kg_build_system.table import (
            plan_fields, row_source_plan_ir, shape_fields,
        )

        plan = row_source_plan_ir(SiteTable.row_source())
        fields = plan_fields(plan, {"sites": shape_fields(SiteTable)})
        ```
    """
    return _plan_fields(plan, declarations)


def retarget_expression_ir(
    expression: ExpressionIR, mapping: Mapping[str, str],
) -> ExpressionIR:
    """Rewrite field references from one logical source key to another.

    Example:
        ```python
        from kg_build_system.table import retarget_expression_ir

        moved = retarget_expression_ir(expression, {"sites": "sites_active"})
        ```
    """
    return _retarget_expression_ir(expression, mapping)


# ---------------------------------------------------------------------------
# Struct identity


def _struct_type_key(struct: StructIR) -> tuple[str, str] | None:
    prefix = "python:struct:"
    if not struct.symbol_id.startswith(prefix):
        return None
    module, _, qualname = struct.symbol_id[len(prefix):].partition(":")
    return (module, qualname) if module and qualname else None


def struct_type_key(struct: StructIR) -> tuple[str, str] | None:
    """Recover the ``(module, qualname)`` identity a struct type refers to.

    A symbol that is not a ``python:struct:`` identity yields ``None``.

    Example:
        ```python
        from kg_build_system.table.internal import struct_type_key
        from kg_build_system.table.internal.ir import StructIR

        key = struct_type_key(
            StructIR("python:struct:estate.site:Site", "Site", ())
        )
        ```
    """
    return _struct_type_key(struct)


__all__ = [
    "AuthoringDataType",
    "DataIR",
    "DeclarationSpec",
    "FieldIR",
    "FieldMetadata",
    "FieldSpec",
    "JoinHow",
    "ProjectionFieldIR",
    "ProjectionIR",
    "RowDistinctIR",
    "RowFilterIR",
    "RowGroupByIR",
    "RowJoinIR",
    "RowOrderByIR",
    "RowOrderKeyIR",
    "RowScanIR",
    "RowSourcePlanIR", "ShapeField",
    "RowUnionIR",
    "SourceIR",
    "StructIR",
    "TableIR",
    "TableLanguage",
    "as_row_source",
    "declared_fields",
    "decode_data_part",
    "decode_row_source_plan",
    "derive_row_source",
    "encode_data_part",
    "encode_row_source_plan",
    "group_tables",
    "is_concrete_table",
    "is_table_group",
    "make_row_shape",
    "plan_expressions",
    "plan_fields",
    "plan_inputs",
    "plan_scan_sources",
    "plan_shape_source_name",
    "projection_attrs",
    "projection_base",
    "projection_row_source",
    "record_shape",
    "record_shape_type",
    "resolve_bound_source",
    "resolve_field_specs",
    "retarget_expression_ir",
    "row_source_key",
    "row_source_plan_ir",
    "shape_context",
    "shape_fields",
    "shape_source_name",
    "shape_view",
    "struct_type_key",
    "union_shape_fields",
]


def __getattr__(name: str) -> Any:
    if name == "TableLanguage":
        from .adapters.kernel_language import TableLanguage

        return TableLanguage
    if name == "ShapeField":
        from ..public.shapes import ShapeField

        return ShapeField
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
