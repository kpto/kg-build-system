"""Render the data language DTO back to authoring source."""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from hashlib import sha256
from typing import Any

from kg_build_system.distribution.languages.annotations.model.internal import AnnotationDTO
from kg_build_system.distribution.languages.expressions.model.internal.dto import (
    ExpressionDTO,
    FieldReferenceDTO,
    LiteralExpressionDTO,
    LookupExpressionDTO,
    OperationExpressionDTO,
    VariableExpressionDTO,
)
from kg_build_system.distribution.languages.expressions.model.internal.dto.operation_dto import (
    OperationDTO,
    RowEffectKind,
)
from kg_build_system.distribution.languages.expressions.service.internal import (
    DEFAULT_OPERATIONS,
    operation_dto,
    render_expression_source,
)
from kg_build_system.kernel import SourceFragment
from kg_build_system.distribution.service.internal.rendering import class_name, member_name, render_annotation, render_logical_type
from kg_build_system.kernel.model.internal.json import thaw_json
from kg_build_system.kernel.model.internal.types.dto import ArrayTypeDTO, CustomTypeDTO, LogicalTypeDTO, NullableTypeDTO, StructTypeDTO
from kg_build_system.kernel.model.public.types import LogicalType, NullableType
from kg_build_system.kernel.service.internal.types import type_from_dto, type_to_dto

from ...model.public.shapes import ShapeField
from .rows import plan_fields, row_source_key
from ...model.internal.dto.blueprint_dto import (
    ColumnDTO, DataPartDTO, DefinitionDTO, DerivedRelationDTO,
    FieldDefinitionDTO, SourceRelationDTO, RowDistinctDTO,
    RowFilterDTO, RowGroupByDTO, RowJoinDTO, RowOperationDTO, RowOrderByDTO,
    RowScanDTO, RowSourcePlanDTO, RowUnionDTO, RowUnnestDTO, StructDTO,
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


def _meaning_source(
    value: Any, imports: set[str], indent: str,
) -> list[str]:
    if value is None:
        imports.add("from kg_build_system import Omitted")
        return [f"{indent}meaning=Omitted,"]
    from kg_build_system.distribution.languages.meaning.service.internal import (
        render_meaning,
    )

    fragment = render_meaning(value)
    imports.update(fragment.imports)
    lines = fragment.body.strip().splitlines()
    result = [f"{indent}{lines[0]}"]
    result.extend(f"{indent}{line}" for line in lines[1:])
    if not result[-1].rstrip().endswith(","):
        result[-1] += ","
    return result


def _definition_source(
    definition: DefinitionDTO, imports: set[str], indent: str,
) -> list[str]:
    imports.add("from kg_build_system import Definition")
    return [
        f"{indent}definition=Definition(",
        f"{indent}    grain={definition.grain!r},",
        f"{indent}    identity={tuple(definition.identity)!r},",
        f"{indent}),",
    ]


def _contract_source(
    definition: DefinitionDTO, meaning: Any, imports: set[str], indent: str,
) -> list[str]:
    imports.add("from kg_build_system import Contract, Definition")
    result = [
        f"{indent}contract=Contract(",
        f"{indent}    definition=Definition(",
        f"{indent}        grain={definition.grain!r},",
        f"{indent}        identity={tuple(definition.identity)!r},",
        f"{indent}    ),",
    ]
    result.extend(_meaning_source(meaning, imports, f"{indent}    "))
    result.append(f"{indent}),")
    return result


def _field_definition_source(
    definition: FieldDefinitionDTO, imports: set[str], indent: str,
) -> list[str]:
    imports.add("from kg_build_system import FieldDefinition")
    result = [
        f"{indent}definition=FieldDefinition(",
        f"{indent}    value={definition.value!r},",
    ]
    if definition.unit is not None:
        result.append(f"{indent}    unit={definition.unit!r},")
    if definition.null_meaning is not None:
        result.append(
            f"{indent}    null_meaning={definition.null_meaning!r},"
        )
    result.append(f"{indent}),")
    return result


def _field_source(
    column: ColumnDTO,
    imports: set[str],
    type_names: Mapping[str, str],
) -> list[str]:
    attribute = member_name(column.name)
    type_source = _type_source(column.logical_type, imports, type_names)
    metadata: list[str] = []
    if column.definition is not None:
        metadata.extend(
            _field_definition_source(column.definition, imports, "        ")
        )
    if attribute != column.name:
        metadata.append(f"        name={column.name!r},")
    metadata.extend(_annotations_source(column.annotations, imports, "        "))
    metadata.extend(_meaning_source(column.meaning, imports, "        "))
    if not metadata:
        return [f"    {attribute}: Field[{type_source}] = field()"]
    return [
        f"    {attribute}: Field[{type_source}] = field(",
        *metadata,
        "    )",
    ]


def _declaration_source(
    value: StructDTO | SourceRelationDTO,
    *,
    base: str,
    suffix: str,
    option_class: str,
    type_names: Mapping[str, str],
    asset_class: str | None = None,
    contract: bool = False,
) -> tuple[tuple[str, ...], set[str]]:
    imports: set[str] = {"from kg_build_system import Field, field"}
    imports.add(f"from kg_build_system import {base}, {option_class}")
    own_name = class_name(value.name, suffix)
    base_source = base if asset_class is None else f"{base}[{asset_class}]"
    lines = [f"class {own_name}({base_source}):"]
    lines.append(f"    options = {option_class}(")
    lines.append(f"        name={value.name!r},")
    annotations = _annotations_source(value.annotations, imports, "        ")
    lines.extend(annotations)
    definition = getattr(value, "definition", None)
    if contract and definition is not None and value.meaning is not None:
        lines.extend(_contract_source(
            definition, value.meaning, imports, "        ",
        ))
    elif contract:
        imports.add("from kg_build_system import Omitted")
        lines.append("        contract=Omitted,")
    else:
        lines.extend(_meaning_source(value.meaning, imports, "        "))
    lines.append("    )")
    if value.columns:
        lines.append("")
        for index, column in enumerate(value.columns):
            if index:
                lines.append("")
            lines.extend(_field_source(column, imports, type_names))
    return tuple(lines), imports


def _row_effects(
    operations: Iterable[OperationDTO],
) -> dict[str, RowEffectKind]:
    """The declared row effect of every operation in the composition."""
    effects: dict[str, RowEffectKind] = {
        declaration.name: declaration.row_effect
        for declaration in map(operation_dto, DEFAULT_OPERATIONS)
    }
    effects.update((item.name, item.row_effect) for item in operations)
    return effects


def _render_plain(
    expression: ExpressionDTO,
    imports: set[str],
    row_effects: Mapping[str, RowEffectKind],
) -> str:
    """Render one expression in the canonical node form, as a Selection."""
    fragment = render_expression_source(expression, row_effects)
    imports.update(fragment.imports)
    return fragment.body


def _render_expression(
    expression: ExpressionDTO,
    imports: set[str],
    *,
    class_names: Mapping[str, str] | None = None,
    available: frozenset[str] | set[str] = frozenset(),
    row_variable: str = "row",
    row_source_name: str | None = None,
    row_effects: Mapping[str, RowEffectKind] | None = None,
) -> str:
    """Render an expression for a Selection slot, preferring its method form.

    A built-in operation whose fields resolve to a declaration renders as the
    authoring method chain. A plan-local read, a custom operation or an
    unresolved name falls back to the canonical expression form, which is still
    a Selection because its node is wrapped in ``select_expression``.
    """
    effects = row_effects or {}
    if class_names is not None:
        try:
            return _render_selection_expression(
                expression,
                class_names=class_names,
                available=available,
                row_variable=row_variable,
                row_source_name=row_source_name,
                row_effects=effects,
                imports=imports,
            )
        except TypeError:
            pass
    return _render_plain(expression, imports, effects)


_SELECTION_METHODS = {
    "add": "add",
    "subtract": "sub",
    "equals": "equals",
    "replace": "replace",
    "to_string": "to_string",
    "before_separator": "before_separator",
    "after_separator": "after_separator",
    "array_at": "at",
    "array_slice": "slice",
    "drop_null_items": "drop_null_items",
    "sort": "sort",
    "distinct": "unique",
    "join": "concat",
    "coalesce": "default_to",
    "not": "not_",
    "and": "and_",
    "or": "or_",
    "zip": "zip",
}

_SELECTION_SCALAR_ARGUMENTS = {
    "join": (1,),
    "replace": (1, 2),
    "before_separator": (1,),
    "after_separator": (1,),
}


def _selection_type_safe(logical_type: LogicalTypeDTO) -> bool:
    """A method chain re-derives a member type from its declaration class."""
    if isinstance(logical_type, NullableTypeDTO):
        return _selection_type_safe(logical_type.value)
    if isinstance(logical_type, ArrayTypeDTO):
        return _selection_type_safe(logical_type.item)
    return not isinstance(logical_type, (StructTypeDTO, CustomTypeDTO))


def _render_scalar_argument(expression: ExpressionDTO, operator: str) -> str:
    if isinstance(expression, LiteralExpressionDTO):
        value = thaw_json(expression.value)
        if isinstance(value, (str, int, float, bool)) or value is None:
            return repr(value)
    raise TypeError(
        f"operation {operator!r} requires a literal scalar in this position"
    )


def _render_selection_expression(
    expression: ExpressionDTO,
    *,
    class_names: Mapping[str, str],
    available: frozenset[str] | set[str],
    row_variable: str,
    row_source_name: str | None,
    row_effects: Mapping[str, RowEffectKind],
    imports: set[str],
) -> str:
    """Render an expression in the Selection authoring form.

    ``where`` evaluates its lambda and requires a ``Selection[bool]``, so a
    field read renders as a member access and a built-in operation as its
    authoring method. The canonical constructors produce bare expression nodes
    and are only valid after ``select_expression`` wraps them.
    """
    if isinstance(expression, LiteralExpressionDTO):
        return _render_plain(expression, imports, row_effects)
    if isinstance(expression, VariableExpressionDTO):
        return expression.name
    if isinstance(expression, FieldReferenceDTO):
        relation = expression.field.relation
        if (
            expression.path
            or not _selection_type_safe(expression.logical_type)
        ):
            return _render_plain(expression, imports, row_effects)
        if row_source_name is not None and relation == row_source_name:
            base = row_variable
        else:
            found = class_names.get(relation)
            if found is None or relation not in available:
                raise TypeError(
                    f"cannot render the field read from {relation!r} "
                    "as a selection"
                )
            base = found
        return f"{base}.{member_name(expression.field.field)}"
    if isinstance(expression, LookupExpressionDTO):
        # A lookup's struct type is the target declaration's identity. Naming
        # the generated class would rename it, so the canonical form keeps it.
        return _render_plain(expression, imports, row_effects)
    if isinstance(expression, OperationExpressionDTO):
        operator = expression.operator.name
        if operator in {"struct_field", "transform_items"}:
            # Both resolve a member declaration; the canonical form keeps the
            # declaration's own type identity.
            return _render_plain(expression, imports, row_effects)
        specials = {"concat", "append", "drop_null", "expand", "drop_if"}
        if operator not in _SELECTION_METHODS and operator not in specials:
            return _render_plain(expression, imports, row_effects)
        arguments = tuple(
            _render_selection_expression(
                argument, class_names=class_names, available=available,
                row_variable=row_variable, row_source_name=row_source_name,
                row_effects=row_effects, imports=imports,
            )
            for argument in expression.arguments
        )
        parameters = {
            parameter.name: thaw_json(parameter.value)
            for parameter in expression.parameters
        }
        if operator in {"concat", "append"}:
            result = arguments[0]
            for argument in arguments[1:]:
                result += f".append({argument})"
            return result
        if operator == "drop_null":
            return f"{arguments[0]}.alter_rows().drop_null()"
        if operator == "expand":
            return f"{arguments[0]}.alter_rows().expand()"
        if operator == "drop_if":
            return (
                f"{arguments[0]}.alter_rows().drop_if("
                f"lambda value: {arguments[1]})"
            )
        method = _SELECTION_METHODS.get(operator)
        if method is None:
            raise TypeError(
                f"cannot render operation {operator!r} as a selection"
            )
        if operator == "coalesce" and len(arguments) != 2:
            raise TypeError(
                "coalesce with more than two arguments has no Selection form"
            )
        scalar_positions = _SELECTION_SCALAR_ARGUMENTS.get(operator, ())
        rendered_arguments: list[str] = []
        for index, argument in enumerate(expression.arguments):
            if index in scalar_positions:
                rendered_arguments.append(
                    _render_scalar_argument(argument, operator)
                )
            else:
                rendered_arguments.append(arguments[index])
        suffix = "".join(
            f", {name}={value!r}" for name, value in parameters.items()
        )
        return (
            f"{arguments[0]}.{method}("
            f"{', '.join(rendered_arguments[1:])}{suffix})"
        )
    raise TypeError(f"unsupported expression DTO {expression!r}")


def _access_type(logical_type: LogicalType) -> LogicalType:
    if isinstance(logical_type, NullableType):
        return logical_type
    return NullableType(logical_type)


def _access_declarations(
    data: DataPartDTO,
) -> dict[str, tuple[ShapeField, ...]]:
    """Row shapes as authoring reads them: source members are nullable."""
    declarations: dict[str, tuple[ShapeField, ...]] = {}
    for source in data.source_relations:
        declarations[source.name] = tuple(
            ShapeField(
                member_name(column.name), column.name,
                _access_type(type_from_dto(column.logical_type)),
            )
            for column in source.columns
        )
    for derived in data.derived_relations:
        declarations[derived.name] = tuple(
            ShapeField(
                member_name(column.name), column.name,
                type_from_dto(column.logical_type),
            )
            for column in derived.columns
        )
    return declarations


def _helper_name(prefix: str, fields: tuple[ShapeField, ...]) -> str:
    signature = tuple(
        (field.attribute, field.name, field.logical_type) for field in fields
    )
    digest = sha256(repr(signature).encode("utf-8")).hexdigest()[:16]
    return f"_{prefix}{digest}"


def _shape_helper(
    prefix: str,
    fields: tuple[ShapeField, ...],
    imports: set[str],
    type_names: Mapping[str, str],
) -> str:
    name = _helper_name(prefix, fields)
    imports.add("from kg_build_system import Selection, Shape")
    lines = [f"class {name}(Shape):"]
    for field in fields:
        annotations = _type_source(
            type_to_dto(field.logical_type), imports, type_names,
        )
        lines.append(f"    {field.attribute}: Selection[{annotations}]")
    return "\n".join(lines)


def _operation_helper(
    plan: RowOperationDTO,
    imports: set[str],
    type_names: Mapping[str, str],
    helpers: dict[object, str],
) -> str:
    """Render one stable relation-operation value and return its name."""
    fields = tuple(plan.output)
    shape_name = _helper_name("RelationOperationOutput", fields)
    helpers.setdefault(
        shape_name,
        _shape_helper("RelationOperationOutput", fields, imports, type_names),
    )
    digest = sha256(repr(
        (plan.operation, shape_name, plan.grain)
    ).encode("utf-8")).hexdigest()[:16]
    spec_name = f"_relation_operation_spec_{digest}"
    operation_name = f"_relation_operation_{digest}"
    chunk = "\n".join((
        f"{spec_name} = RelationOperationSpec(",
        f"    name={plan.operation!r},",
        f"    output={shape_name},",
        f"    grain={plan.grain!r},",
        ")",
        f"{operation_name} = RelationOperation({spec_name})",
    ))
    imports.add(
        "from kg_build_system import RelationOperation, RelationOperationSpec"
    )
    helpers.setdefault(
        ("relation_operation", plan.operation, shape_name, plan.grain), chunk,
    )
    return operation_name


def _render_row_source(
    plan: RowSourcePlanDTO, *,
    class_names: Mapping[str, str],
    available: frozenset[str] | set[str],
    imports: set[str],
    type_names: Mapping[str, str],
    declarations: Mapping[str, tuple[ShapeField, ...]],
    helpers: dict[object, str],
    row_effects: Mapping[str, RowEffectKind],
) -> str:
    if isinstance(plan, RowScanDTO):
        name = plan.relation.name
        owner = class_names.get(name, class_name(name, "SourceRelation"))
        return f"{owner}.row_source()"
    if isinstance(plan, RowFilterDTO):
        inner = _render_row_source(
            plan.input, class_names=class_names, available=available,
            imports=imports, type_names=type_names,
            declarations=declarations, helpers=helpers,
            row_effects=row_effects,
        )
        predicate = _render_expression(
            plan.predicate,
            imports,
            class_names=class_names,
            available=available,
            row_variable="row",
            row_source_name=row_source_key(plan.input),
            row_effects=row_effects,
        )
        return f"{inner}.where(lambda row: {predicate})"
    if isinstance(plan, RowUnionDTO):
        left = _render_row_source(
            plan.left, class_names=class_names, available=available,
            imports=imports, type_names=type_names,
            declarations=declarations, helpers=helpers,
            row_effects=row_effects,
        )
        right = _render_row_source(
            plan.right, class_names=class_names, available=available,
            imports=imports, type_names=type_names,
            declarations=declarations, helpers=helpers,
            row_effects=row_effects,
        )
        return f"{left}.union({right}, all={plan.all!r})"
    if isinstance(plan, RowJoinDTO):
        left = _render_row_source(
            plan.left, class_names=class_names, available=available,
            imports=imports, type_names=type_names,
            declarations=declarations, helpers=helpers,
            row_effects=row_effects,
        )
        right = _render_row_source(
            plan.right, class_names=class_names, available=available,
            imports=imports, type_names=type_names,
            declarations=declarations, helpers=helpers,
            row_effects=row_effects,
        )
        left_key = _render_expression(
            plan.left_key, imports, class_names=class_names,
            available=available, row_variable="left",
            row_effects=row_effects,
        )
        right_key = _render_expression(
            plan.right_key, imports, class_names=class_names,
            available=available, row_variable="right",
            row_effects=row_effects,
        )
        return (
            f"{left}.join({right}, "
            f"on=lambda left, right: ({left_key}, {right_key}), how={plan.how!r})"
        )
    if isinstance(plan, RowGroupByDTO):
        inner = _render_row_source(
            plan.input, class_names=class_names, available=available,
            imports=imports, type_names=type_names,
            declarations=declarations, helpers=helpers,
            row_effects=row_effects,
        )
        fields = tuple(
            ShapeField(name, name, type_from_dto(expression.logical_type))
            for name, expression in plan.keys
        )
        helper = _shape_helper("KeyShape", fields, imports, type_names)
        helpers.setdefault(fields, helper)
        name = _helper_name("KeyShape", fields)
        rendered_keys: list[str] = []
        for key, expression in plan.keys:
            value = _render_expression(
                expression, imports, class_names=class_names,
                available=available, row_effects=row_effects,
            )
            rendered_keys.append(f"{key!r}: {value}")
        keys = ", ".join(rendered_keys)
        return f"{inner}.group_by(keys={name}, by=lambda row: {{{keys}}})"
    if isinstance(plan, RowDistinctDTO):
        inner = _render_row_source(
            plan.input, class_names=class_names, available=available,
            imports=imports, type_names=type_names,
            declarations=declarations, helpers=helpers,
            row_effects=row_effects,
        )
        return f"{inner}.distinct()"
    if isinstance(plan, RowOrderByDTO):
        inner = _render_row_source(
            plan.input, class_names=class_names, available=available,
            imports=imports, type_names=type_names,
            declarations=declarations, helpers=helpers,
            row_effects=row_effects,
        )
        keys = ", ".join(
            _render_expression(
                expression, imports, class_names=class_names,
                available=available, row_effects=row_effects,
            )
            for expression, _ in plan.keys
        )
        ascending = plan.keys[0][1] if plan.keys else True
        return f"{inner}.order_by({keys}, ascending={ascending!r})"
    if isinstance(plan, RowUnnestDTO):
        inner = _render_row_source(
            plan.input, class_names=class_names, available=available,
            imports=imports, type_names=type_names,
            declarations=declarations, helpers=helpers,
            row_effects=row_effects,
        )
        expression = _render_expression(
            plan.expression, imports, class_names=class_names,
            available=available, row_effects=row_effects,
        )
        fields = plan_fields(plan, declarations)
        helper = _shape_helper("UnnestShape", fields, imports, type_names)
        helpers.setdefault(fields, helper)
        name = _helper_name("UnnestShape", fields)
        return f"{inner}.unnest(lambda row: {expression}, out={name})"
    if isinstance(plan, RowOperationDTO):
        inner = _render_row_source(
            plan.input, class_names=class_names, available=available,
            imports=imports, type_names=type_names,
            declarations=declarations, helpers=helpers,
            row_effects=row_effects,
        )
        operation = _operation_helper(plan, imports, type_names, helpers)
        if not plan.parameters:
            return f"{inner}.custom_op({operation})"
        parameters = ", ".join(
            f"{parameter.name!r}: {thaw_json(parameter.value)!r}"
            for parameter in plan.parameters
        )
        return f"{inner}.custom_op({operation}, **{{{parameters}}})"
    raise TypeError(f"unsupported row-source plan {plan!r}")


def _derived_relation_source(
    value: DerivedRelationDTO,
    *,
    class_names: Mapping[str, str],
    available: frozenset[str] | set[str],
    type_names: Mapping[str, str],
    declarations: Mapping[str, tuple[ShapeField, ...]],
    helpers: dict[object, str],
    row_effects: Mapping[str, RowEffectKind],
) -> tuple[tuple[str, ...], set[str]]:
    internal = value.visibility == "internal"
    base = "Stage" if internal else "DerivedRelation"
    option_class = "StageOptions" if internal else "DerivedRelationOptions"
    imports: set[str] = {
        f"from kg_build_system import {base}, computed_field",
        f"from kg_build_system import {option_class}",
    }
    source = _render_row_source(
        value.row_source, class_names=class_names, available=available,
        imports=imports, type_names=type_names,
        declarations=declarations, helpers=helpers,
        row_effects=row_effects,
    )
    own_name = class_name(value.name, "")
    lines = [f"class {own_name}({base}({source})):"]
    lines.append(f"    options = {option_class}(")
    lines.append(f"        name={value.name!r},")
    lines.extend(_annotations_source(value.annotations, imports, "        "))
    if internal:
        lines.extend(_definition_source(value.definition, imports, "        "))
    elif value.meaning is not None:
        lines.extend(_contract_source(
            value.definition, value.meaning, imports, "        ",
        ))
    lines.append("    )")
    if value.columns:
        lines.append("")
        for index, column in enumerate(value.columns):
            if index:
                lines.append("")
            attribute = member_name(column.name)
            expression = (
                _render_expression(
                    column.expression, imports, class_names=class_names,
                    available=available, row_effects=row_effects,
                )
                if column.expression is not None else "None"
            )
            lines.append(f"    {attribute} = computed_field(")
            lines.append(f"        {expression},")
            if column.definition is not None:
                lines.extend(_field_definition_source(
                    column.definition, imports, "        ",
                ))
            if attribute != column.name:
                lines.append(f"        name={column.name!r},")
            lines.extend(_annotations_source(column.annotations, imports, "        "))
            lines.extend(_meaning_source(column.meaning, imports, "        "))
            lines.append("    )")
    return tuple(lines), imports


def render_data(
    data: DataPartDTO,
    context: Any = None,
    *,
    class_names: Mapping[str, str] | None = None,
    operations: Iterable[OperationDTO] = (),
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
    row_effects = _row_effects(operations)
    names = dict(class_names or {})
    for asset in data.source_relations:
        names.setdefault(asset.asset.name, class_name(asset.asset.name, "Asset"))
    for struct in data.structs:
        names.setdefault(struct.name, class_name(struct.name, "Struct"))
    for relation in data.source_relations:
        names.setdefault(relation.name, class_name(relation.name, "SourceRelation"))
    for derived_relation in data.derived_relations:
        names.setdefault(
            derived_relation.name,
            class_name(derived_relation.name, ""),
        )

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
    for relation in data.source_relations:
        lines, needed = _declaration_source(
            relation, base="SourceRelation", suffix="SourceRelation",
            option_class="SourceRelationOptions",
            type_names=type_names,
            asset_class=names[relation.asset.name],
            contract=True,
        )
        imports.update(needed)
        chunks.append("\n".join(lines))
    declarations = _access_declarations(data)
    helpers: dict[object, str] = {}
    derived_chunks: list[str] = []
    available: set[str] = {
        source.name for source in data.source_relations
    }
    for derived_relation in data.derived_relations:
        lines, needed = _derived_relation_source(
            derived_relation, class_names=names, available=available,
            type_names=type_names, declarations=declarations,
            helpers=helpers, row_effects=row_effects,
        )
        imports.update(needed)
        derived_chunks.append("\n".join(lines))
        available.add(derived_relation.name)
    chunks.extend(helpers.values())
    chunks.extend(derived_chunks)
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
    operations: Iterable[OperationDTO] = (),
) -> SourceFragment:
    """Alias of :func:`render_data` named for the DTO-to-fragment direction."""
    return render_data(
        data, context, class_names=class_names, operations=operations,
    )


def render(
    data: DataPartDTO,
    context: Any = None,
    *,
    class_names: Mapping[str, str] | None = None,
    operations: Iterable[OperationDTO] = (),
) -> SourceFragment:
    """Render the data DTO to authoring source."""
    return render_data(
        data, context, class_names=class_names, operations=operations,
    )


__all__ = [
    "SourceFragment", "data_to_fragment", "render", "render_data",
]
