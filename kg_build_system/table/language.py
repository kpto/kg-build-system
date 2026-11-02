"""The ``data`` language: collect declarations, lower them to ``DataIR``.

``collect`` gathers only what the authoring namespace actually exposes. There is
no process-global declaration registry; two builds in one process do not leak
declarations into each other.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

from .._frozen_json import freeze_json
from ..annotations.interfaces import annotation_irs
from ..annotations.ir import AnnotationIR
from ..expressions.interfaces import expression_to_ir
from ..kernel import LanguageContext, Namespace
from ..types.interfaces import type_to_ir
from .declarations import group_tables, resolve_bound_source
from .ir import (
    DataIR, FieldIR, ProjectionFieldIR, ProjectionIR, RowSourcePlanIR,
    SourceIR, StructIR, TableIR, decode_data_part, encode_data_part,
)
from .models import (
    BoundSource, BoundTable, DeclarationSpec, is_table_group,
    projection_row_source,
)
from .row_sources import RowSource, plan_scan_sources, row_source_plan_ir

_DECLARATION_KINDS = {"table", "struct", "computed_struct", "projection"}


def _spec(value: Any) -> DeclarationSpec | None:
    if not isinstance(value, type):
        return None
    spec = vars(value).get("_kg_declaration_spec")
    return spec if isinstance(spec, DeclarationSpec) else None


def _symbol(kind: str, declaration: type[Any]) -> str:
    return f"python:{kind}:{declaration.__module__}:{declaration.__qualname__}"


def _walk(value: Any, found: dict[int, Any], structs: dict[int, Any], seen: set[int]) -> None:
    marker = id(value)
    if marker in seen:
        return
    seen.add(marker)
    if isinstance(value, type):
        spec = _spec(value)
        if spec is None:
            return
        if spec.kind in _DECLARATION_KINDS and spec.final:
            found[marker] = value
            for item in spec.fields:
                _walk(item.declaration, found, structs, seen)
            _walk(spec.row_source, found, structs, seen)
        elif spec.kind == "table_group" and spec.final:
            for member in spec.members:
                _walk(member, found, structs, seen)
        return
    if isinstance(value, BoundSource):
        target = value.table if isinstance(value, BoundTable) else value.group
        _walk(target, found, structs, seen)
        return
    if isinstance(value, RowSource):
        _walk(getattr(value, "source", None), found, structs, seen)
        return
    rows = getattr(value, "rows", None)
    if rows is not None:
        _walk(rows, found, structs, seen)


def _collect_declarations(values: Sequence[Any]) -> tuple[dict[int, Any], dict[int, Any]]:
    found: dict[int, Any] = {}
    structs: dict[int, Any] = {}
    seen: set[int] = set()
    for value in values:
        _walk(value, found, structs, seen)
    return found, structs


def _plan_of(value: Any) -> RowSourcePlanIR | None:
    """Convert a pinned row source value or a plan into plan IR."""
    from .ir import (
        RowDistinctIR, RowFilterIR, RowGroupByIR, RowJoinIR, RowOrderByIR,
        RowScanIR, RowUnionIR,
    )

    plan_types = (
        RowScanIR, RowFilterIR, RowUnionIR, RowJoinIR,
        RowGroupByIR, RowDistinctIR, RowOrderByIR,
    )
    if value is None:
        return None
    if isinstance(value, plan_types):
        return value
    return row_source_plan_ir(value)


def _data_annotations(values: Sequence[Any]) -> tuple[AnnotationIR, ...]:
    return tuple(
        AnnotationIR(item.namespace, item.annotation_id, freeze_json(item.arguments))
        for item in annotation_irs(values)
    )


def _field_ir(item: Any) -> FieldIR:
    return FieldIR(
        name=item.name,
        logical_type=type_to_ir(item.logical_type),
        description=item.description,
        annotations=_data_annotations(item.annotations),
    )


def _struct_ir(declaration: type[Any], spec: DeclarationSpec) -> StructIR:
    return StructIR(
        symbol_id=_symbol("struct", declaration),
        name=spec.name or declaration.__name__,
        fields=tuple(_field_ir(item) for item in spec.fields),
        description=spec.description,
        annotations=_data_annotations(spec.annotations),
    )


def _table_ir(declaration: type[Any], spec: DeclarationSpec) -> TableIR:
    return TableIR(
        symbol_id=_symbol("table", declaration),
        name=spec.name or declaration.__name__,
        fields=tuple(_field_ir(item) for item in spec.fields),
        description=spec.description,
        annotations=_data_annotations(spec.annotations),
    )


def _projection_ir(declaration: type[Any], spec: DeclarationSpec) -> ProjectionIR:
    fields = []
    for item in spec.fields:
        expression = item.descriptor.expression
        if expression is None:
            raise TypeError("projection outputs require computed_field()")
        fields.append(ProjectionFieldIR(
            name=item.name,
            expression=expression_to_ir(expression.model),
            description=item.description,
            annotations=_data_annotations(item.annotations),
        ))
    return ProjectionIR(
        symbol_id=_symbol("projection", declaration),
        name=spec.name or declaration.__name__,
        fields=tuple(fields),
        description=spec.description,
        annotations=_data_annotations(spec.annotations),
        row_source=_plan_of(projection_row_source(declaration)),
    )


def _source_ir(source: BoundTable) -> SourceIR:
    table = source.table
    spec = _spec(table)
    name = spec.name if spec is not None and spec.name else table.__name__
    annotations = tuple(spec.annotations if spec is not None else ())
    return SourceIR(
        symbol_id=f"source:{name}",
        table=name,
        location=source.config.location,
        format=source.config.format.value,
        credential_reference=source.config.credentials,
        version=source.config.version,
        annotations=_data_annotations((*annotations, *source.annotations)),
    )


def _nested_declarations(field: Any) -> tuple[type[Any], ...]:
    declaration = field.declaration
    return (declaration,) if isinstance(declaration, type) else ()


def _add_struct_closure(
    roots: Sequence[type[Any]], structs: dict[int, type[Any]],
) -> None:
    queue = list(roots)
    seen: set[int] = set()
    while queue:
        declaration = queue.pop()
        marker = id(declaration)
        if marker in seen:
            continue
        seen.add(marker)
        spec = _spec(declaration)
        if spec is None or not spec.final:
            continue
        if spec.kind in {"struct", "computed_struct"}:
            structs[marker] = declaration
        for item in spec.fields:
            for nested in _nested_declarations(item):
                nested_spec = _spec(nested)
                if nested_spec is not None and nested_spec.kind in {
                    "struct", "computed_struct",
                }:
                    queue.append(nested)


def _validate(data: DataIR) -> None:
    symbol_ids = (
        *(item.symbol_id for item in data.structs),
        *(item.symbol_id for item in data.tables),
        *(item.symbol_id for item in data.projections),
        *(item.symbol_id for item in data.sources),
    )
    if len(symbol_ids) != len(set(symbol_ids)):
        raise ValueError("data symbol IDs must be unique")
    table_names = tuple(item.name for item in data.tables)
    projection_names = tuple(item.name for item in data.projections)
    if len(table_names) != len(set(table_names)):
        raise ValueError("table names must be unique")
    if len(projection_names) != len(set(projection_names)):
        raise ValueError("projection names must be unique")
    if len(set(table_names) | set(projection_names)) != len(table_names) + len(projection_names):
        raise ValueError("table and projection names must be unique")
    for declaration in (*data.structs, *data.tables, *data.projections):
        names = tuple(field.name for field in declaration.fields)
        if len(names) != len(set(names)):
            raise ValueError(f"{declaration.name} field names must be unique")
    projection_by_name = {item.name: item for item in data.projections}
    dependencies: dict[str, set[str]] = {
        name: set() for name in projection_names
    }
    for projection in data.projections:
        if projection.row_source is None:
            raise ValueError("projections require a row source")
        known = set(table_names) | set(projection_names)
        scanned = set(plan_scan_sources(projection.row_source))
        unknown = scanned - known
        if unknown:
            raise ValueError(
                "projection row source reads unknown logical source "
                + ", ".join(sorted(unknown))
            )
        dependencies[projection.name].update(scanned & set(projection_names))
        for field in projection.fields:
            from ..expressions.interfaces import walk_expression_ir

            for node in walk_expression_ir(field.expression):
                source = getattr(node, "source", None)
                if isinstance(source, str) and source in projection_by_name:
                    dependencies[projection.name].add(source)

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str) -> None:
        if name in visiting:
            raise ValueError(f"projection dependency cycle includes {name!r}")
        if name in visited:
            return
        visiting.add(name)
        for dependency in dependencies[name]:
            visit(dependency)
        visiting.remove(name)
        visited.add(name)

    for name in dependencies:
        visit(name)

    source_tables = tuple(item.table for item in data.sources)
    if len(source_tables) != len(set(source_tables)):
        raise ValueError("source-bound table names must be unique")
    unknown_sources = set(source_tables) - set(table_names)
    if unknown_sources:
        raise ValueError(
            "a physical source references an unknown table: "
            + ", ".join(sorted(unknown_sources))
        )


class TableLanguage:
    """The ``data`` language part of the build."""

    name = "data"
    requires: tuple[str, ...] = ()

    def collect(self, namespace: Namespace) -> Sequence[object]:
        values = tuple(namespace.values())
        found, _ = _collect_declarations(values)
        sources = tuple(
            value for value in values if isinstance(value, BoundSource)
        )
        result: list[object] = []
        seen: set[int] = set()
        for value in (*found.values(), *sources):
            if id(value) in seen:
                continue
            seen.add(id(value))
            result.append(value)
        return tuple(result)

    def lower(
        self, declarations: Sequence[object], context: LanguageContext,
    ) -> DataIR:
        found, _ = _collect_declarations(tuple(declarations))
        bound_tables: list[BoundTable] = []
        for value in declarations:
            if isinstance(value, BoundSource):
                bound_tables.extend(resolve_bound_source(value))
            elif isinstance(value, type) and is_table_group(value):
                for table, _ in group_tables(value):
                    found.setdefault(id(table), table)
        for source in bound_tables:
            found.setdefault(id(source.table), source.table)

        tables: dict[int, type[Any]] = {}
        projections: dict[int, type[Any]] = {}
        struct_roots: list[type[Any]] = []
        for declaration in found.values():
            spec = _spec(declaration)
            if spec is None or not spec.final:
                continue
            if spec.kind == "table":
                tables[id(declaration)] = declaration
            elif spec.kind == "projection":
                projections[id(declaration)] = declaration
            elif spec.kind in {"struct", "computed_struct"}:
                struct_roots.append(declaration)
        structs: dict[int, type[Any]] = {id(item): item for item in struct_roots}
        _add_struct_closure(
            (*tables.values(), *projections.values(), *struct_roots), structs,
        )

        data = DataIR(
            structs=tuple(sorted(
                (
                    _struct_ir(item, cast(DeclarationSpec, _spec(item)))
                    for item in structs.values()
                ),
                key=lambda item: item.symbol_id,
            )),
            tables=tuple(sorted(
                (
                    _table_ir(item, cast(DeclarationSpec, _spec(item)))
                    for item in tables.values()
                ),
                key=lambda item: item.symbol_id,
            )),
            projections=tuple(sorted(
                (
                    _projection_ir(item, cast(DeclarationSpec, _spec(item)))
                    for item in projections.values()
                ),
                key=lambda item: item.symbol_id,
            )),
            sources=tuple(sorted(
                (_source_ir(item) for item in bound_tables),
                key=lambda item: item.symbol_id,
            )),
        )
        return data

    def validate(self, ir: Any) -> None:
        if not isinstance(ir, DataIR):
            raise TypeError("the data language lowers to DataIR")
        _validate(ir)

    def encode(self, ir: Any) -> Any:
        if not isinstance(ir, DataIR):
            raise TypeError("the data language encodes DataIR")
        return encode_data_part(ir)

    def decode(self, value: Any) -> Any:
        if not isinstance(value, Mapping):
            raise ValueError("the encoded data part must be an object")
        return decode_data_part(value)


__all__ = ["TableLanguage"]
