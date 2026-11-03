"""Render the table language DTO back to authoring source."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from kg_build_system.declaration.foundations.annotations.internal import AnnotationDTO
from kg_build_system.declaration.foundations.expressions.internal import (
    render_expression_source,
)
from kg_build_system.declaration.internal import SourceFragment
from kg_build_system.declaration.internal.rendering import (
    class_name,
    member_name,
    render_annotation,
    render_logical_type,
)
from kg_build_system.kernel.internal.types.dto import (
    ArrayTypeDTO, CustomTypeDTO, LogicalTypeDTO, NullableTypeDTO, StructTypeDTO,
)

from ..dto.blueprint_dto import (
    ColumnDTO, DataPartDTO, ProjectionDTO, RelationDTO, RowDistinctDTO,
    RowFilterDTO, RowGroupByDTO, RowJoinDTO, RowOrderByDTO, RowScanDTO,
    RowSourcePlanDTO, RowUnionDTO, SourceDTO, StructDTO,
)


def _type_source(
    value: LogicalTypeDTO,
    imports: set[str],
    type_names: Mapping[str, str],
) -> str:
    if isinstance(value, NullableTypeDTO):
        return f"{_type_source(value.value, imports, type_names)} | None"
    if isinstance(value, ArrayTypeDTO):
        imports.add("from kg_build_system.types import Array")
        return f"Array[{_type_source(value.item, imports, type_names)}]"
    if isinstance(value, StructTypeDTO):
        return type_names.get(
            value.qualname,
            type_names.get(value.qualname.removesuffix("Struct"), value.qualname),
        )
    if isinstance(value, CustomTypeDTO):
        imports.add(f"import {value.module}")
        return f"{value.module}.{value.qualname}"
    return render_logical_type(value, imports)


def _annotations_source(
    values: Sequence[AnnotationDTO], imports: set[str], indent: str,
) -> tuple[str, ...]:
    if not values:
        return ()
    return (
        f"{indent}annotations=(",
        *(f"{indent}    {render_annotation(item, imports)}," for item in values),
        f"{indent}),",
    )


def _field_source(
    column: ColumnDTO,
    imports: set[str],
    type_names: Mapping[str, str],
) -> list[str]:
    attribute = member_name(column.name)
    type_source = _type_source(column.logical_type, imports, type_names)
    metadata: list[str] = []
    if attribute != column.name:
        metadata.append(f"        name={column.name!r},")
    if column.description is not None:
        metadata.append(f"        description={column.description!r},")
    metadata.extend(_annotations_source(column.annotations, imports, "        "))
    if not metadata:
        return [f"    {attribute}: Field[{type_source}] = field()"]
    return [
        f"    {attribute}: Field[{type_source}] = field(",
        *metadata,
        "    )",
    ]


def _declaration_source(
    value: StructDTO | RelationDTO,
    *,
    base: str,
    suffix: str,
    option_class: str,
    type_names: Mapping[str, str],
) -> tuple[tuple[str, ...], set[str]]:
    imports: set[str] = {"from kg_build_system import Field, field"}
    imports.add(f"from kg_build_system import {base}, {option_class}")
    own_name = class_name(value.name, suffix)
    lines = [f"class {own_name}({base}):"]
    lines.append(f"    options = {option_class}(")
    lines.append(f"        name={value.name!r},")
    if value.description is not None:
        lines.append(f"        description={value.description!r},")
    annotations = _annotations_source(value.annotations, imports, "        ")
    lines.extend(annotations)
    lines.append("    )")
    if value.columns:
        lines.append("")
        for index, column in enumerate(value.columns):
            if index:
                lines.append("")
            lines.extend(_field_source(column, imports, type_names))
    return tuple(lines), imports


def _render_expression(expression: Any, imports: set[str]) -> str:
    fragment = render_expression_source(expression)
    imports.update(fragment.imports)
    return fragment.text


def _render_row_source(
    plan: RowSourcePlanDTO, *, class_names: Mapping[str, str], imports: set[str],
) -> str:
    if isinstance(plan, RowScanDTO):
        owner = class_names.get(plan.source, class_name(plan.source, "Table"))
        return f"{owner}.row_source()"
    if isinstance(plan, RowFilterDTO):
        inner = _render_row_source(plan.input, class_names=class_names, imports=imports)
        predicate = _render_expression(plan.predicate, imports)
        return f"{inner}.where(lambda row: {predicate})"
    if isinstance(plan, RowUnionDTO):
        left = _render_row_source(plan.left, class_names=class_names, imports=imports)
        right = _render_row_source(plan.right, class_names=class_names, imports=imports)
        return f"{left}.union({right}, all={plan.all!r})"
    if isinstance(plan, RowJoinDTO):
        left = _render_row_source(plan.left, class_names=class_names, imports=imports)
        right = _render_row_source(plan.right, class_names=class_names, imports=imports)
        left_key = _render_expression(plan.left_key, imports)
        right_key = _render_expression(plan.right_key, imports)
        return (
            f"{left}.join({right}, "
            f"on=lambda left, right: ({left_key}, {right_key}), how={plan.how!r})"
        )
    if isinstance(plan, RowGroupByDTO):
        inner = _render_row_source(plan.input, class_names=class_names, imports=imports)
        keys = ", ".join(
            f"{name!r}: {_render_expression(expression, imports)}"
            for name, expression in plan.keys
        )
        return f"{inner}.group_by(by=lambda row: {{{keys}}})"
    if isinstance(plan, RowDistinctDTO):
        inner = _render_row_source(plan.input, class_names=class_names, imports=imports)
        return f"{inner}.distinct()"
    if isinstance(plan, RowOrderByDTO):
        inner = _render_row_source(plan.input, class_names=class_names, imports=imports)
        keys = ", ".join(
            _render_expression(expression, imports) for expression, _ in plan.keys
        )
        ascending = plan.keys[0][1] if plan.keys else True
        return f"{inner}.order_by({keys}, ascending={ascending!r})"
    raise TypeError(f"unsupported row-source plan {plan!r}")


def _projection_source(
    value: ProjectionDTO,
    *,
    class_names: Mapping[str, str],
) -> tuple[tuple[str, ...], set[str]]:
    imports: set[str] = {
        "from kg_build_system import Field, Projection, computed_field",
        "from kg_build_system import ProjectionOptions",
    }
    source = _render_row_source(
        value.row_source, class_names=class_names, imports=imports,
    )
    own_name = class_name(value.name, "Projection")
    lines = [f"class {own_name}(Projection({source})):"]
    lines.append("    options = ProjectionOptions(")
    lines.append(f"        name={value.name!r},")
    if value.description is not None:
        lines.append(f"        description={value.description!r},")
    lines.extend(_annotations_source(value.annotations, imports, "        "))
    lines.append("    )")
    if value.columns:
        lines.append("")
        for index, column in enumerate(value.columns):
            if index:
                lines.append("")
            attribute = member_name(column.name)
            expression = (
                _render_expression(column.expression, imports)
                if column.expression is not None else "None"
            )
            lines.append(f"    {attribute} = computed_field(")
            lines.append(f"        {expression},")
            if attribute != column.name:
                lines.append(f"        name={column.name!r},")
            if column.description is not None:
                lines.append(f"        description={column.description!r},")
            lines.extend(_annotations_source(column.annotations, imports, "        "))
            lines.append("    )")
    return tuple(lines), imports


def _source_source(
    value: SourceDTO, *, class_names: Mapping[str, str],
) -> tuple[tuple[str, ...], set[str]]:
    imports = {
        "from kg_build_system import DataSourceConfig, InputFormat, bind_source",
    }
    target = class_names.get(value.table, class_name(value.table, "Table"))
    arguments = [repr(value.location)]
    if value.format != "csv":
        arguments.append(f"format=InputFormat.{value.format.upper()}")
    if value.version is not None:
        arguments.append(f"version={value.version!r}")
    if value.credential_reference is not None:
        arguments.append(f"credentials={value.credential_reference!r}")
    lines = [
        f"{member_name(value.table)}_source = bind_source(",
        f"    target={target},",
        f"    config=DataSourceConfig({', '.join(arguments)}),",
        ")",
    ]
    return tuple(lines), imports


def render_data(
    data: DataPartDTO,
    context: Any = None,
    *,
    class_names: Mapping[str, str] | None = None,
) -> SourceFragment:
    """Render a table DTO as authoring source.

    The layer renders its own DTO and uses the expression and annotation
    renderers for inline parts.

    Example:
        ```python
        from kg_build_system.declaration.languages.table.internal.dto import (
            DataPartDTO,
        )
        from kg_build_system.declaration.languages.table.internal.service.source import (
            render_data,
        )

        fragment = render_data(DataPartDTO((), (), (), ()))
        assert fragment.body == ""
        ```
    """
    del context
    names = dict(class_names or {})
    for struct in data.structs:
        names.setdefault(struct.name, class_name(struct.name, "Struct"))
    for relation in data.relations:
        names.setdefault(relation.name, class_name(relation.name, "Table"))
    for projection in data.projections:
        names.setdefault(projection.name, class_name(projection.name, "Projection"))

    type_names: dict[str, str] = {}
    for struct in data.structs:
        own_name = class_name(struct.name, "Struct")
        type_names[struct.name] = own_name
        type_names[struct.name[:1].upper() + struct.name[1:]] = own_name
        type_names[own_name] = own_name
        type_names[own_name.removesuffix("Struct")] = own_name

    imports: set[str] = set()
    chunks: list[str] = []
    for struct in data.structs:
        lines, needed = _declaration_source(
            struct, base="Struct", suffix="Struct", option_class="StructOptions",
            type_names=type_names,
        )
        imports.update(needed)
        chunks.append("\n".join(lines))
    for relation in data.relations:
        lines, needed = _declaration_source(
            relation, base="Table", suffix="Table", option_class="TableOptions",
            type_names=type_names,
        )
        imports.update(needed)
        chunks.append("\n".join(lines))
    for projection in data.projections:
        lines, needed = _projection_source(projection, class_names=names)
        imports.update(needed)
        chunks.append("\n".join(lines))
    for source in data.sources:
        lines, needed = _source_source(source, class_names=names)
        imports.update(needed)
        chunks.append("\n".join(lines))

    body = "\n\n\n".join(chunks)
    if body:
        body += "\n"
    return SourceFragment(
        kind="declaration",
        body=body,
        imports=tuple(sorted(imports)),
    )


def data_to_fragment(
    data: DataPartDTO,
    context: Any = None,
    *,
    class_names: Mapping[str, str] | None = None,
) -> SourceFragment:
    """Alias of :func:`render_data` named for the DTO-to-fragment direction."""
    return render_data(data, context, class_names=class_names)


def render(
    data: DataPartDTO,
    context: Any = None,
    *,
    class_names: Mapping[str, str] | None = None,
) -> SourceFragment:
    """Render the table DTO to authoring source."""
    return render_data(data, context, class_names=class_names)


__all__ = [
    "SourceFragment", "data_to_fragment", "render", "render_data",
]
