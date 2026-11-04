"""Render the data language DTO back to authoring source."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from kg_build_system.distribution.languages.annotations.model.internal import AnnotationDTO
from kg_build_system.distribution.languages.expressions.service.internal import render_expression_source
from kg_build_system.kernel import SourceFragment
from kg_build_system.distribution.service.internal.rendering import class_name, member_name, render_annotation, render_logical_type
from kg_build_system.kernel.model.internal.types.dto import ArrayTypeDTO, CustomTypeDTO, LogicalTypeDTO, NullableTypeDTO, StructTypeDTO

from ...model.internal.dto.blueprint_dto import (
    ColumnDTO, DataPartDTO, ProjectionDTO, RelationDTO, RowDistinctDTO,
    RowFilterDTO, RowGroupByDTO, RowJoinDTO, RowOrderByDTO, RowScanDTO,
    RowSourcePlanDTO, RowUnionDTO, StructDTO,
)


def _type_source(
    value: LogicalTypeDTO,
    imports: set[str],
    type_names: Mapping[str, str],
) -> str:
    if isinstance(value, NullableTypeDTO):
        return f"{_type_source(value.value, imports, type_names)} | None"
    if isinstance(value, ArrayTypeDTO):
        imports.add("from kg_build_system import Array")
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
    asset_class: str | None = None,
) -> tuple[tuple[str, ...], set[str]]:
    imports: set[str] = {"from kg_build_system import Field, field"}
    imports.add(f"from kg_build_system import {base}, {option_class}")
    own_name = class_name(value.name, suffix)
    base_source = base if asset_class is None else f"{base}[{asset_class}]"
    lines = [f"class {own_name}({base_source}):"]
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
    return fragment.body


def _render_row_source(
    plan: RowSourcePlanDTO, *, class_names: Mapping[str, str], imports: set[str],
) -> str:
    if isinstance(plan, RowScanDTO):
        name = plan.relation.name
        owner = class_names.get(name, class_name(name, "Table"))
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


def render_data(
    data: DataPartDTO,
    context: Any = None,
    *,
    class_names: Mapping[str, str] | None = None,
) -> SourceFragment:
    """Render a data DTO as authoring source.

    The layer renders its own DTO and uses the expression and annotation
    renderers for inline parts.

    Example:
        ```python
        from kg_build_system.distribution.languages.data.model.internal.dto import (
            DataPartDTO,
        )
        from kg_build_system.distribution.languages.data.service.internal.source import (
            render_data,
        )

        fragment = render_data(DataPartDTO((), (), ()))
        assert fragment.body == ""
        ```
    """
    del context
    names = dict(class_names or {})
    for asset in data.relations:
        names.setdefault(asset.asset.name, class_name(asset.asset.name, "Asset"))
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
            asset_class=names[relation.asset.name],
        )
        imports.update(needed)
        chunks.append("\n".join(lines))
    for projection in data.projections:
        lines, needed = _projection_source(projection, class_names=names)
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
    """Render the data DTO to authoring source."""
    return render_data(data, context, class_names=class_names)


__all__ = [
    "SourceFragment", "data_to_fragment", "render", "render_data",
]
