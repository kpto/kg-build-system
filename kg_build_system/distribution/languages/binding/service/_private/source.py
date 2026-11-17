"""Render the binding blueprint DTO as authoring source."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from hashlib import sha256
from typing import Any

from kg_build_system.distribution.languages.annotations.model.internal.dto import (
    AnnotationDTO,
)
from kg_build_system.distribution.languages.data.model.public import ShapeField
from kg_build_system.distribution.languages.data.service.internal.rows import (
    plan_fields, plan_shape_source_name,
)
from kg_build_system.distribution.languages.expressions.model.internal.dto import (
    ExpressionDTO,
    FieldReferenceDTO,
    LiteralExpressionDTO,
    LookupExpressionDTO,
    OperationExpressionDTO,
    VariableExpressionDTO,
)
from kg_build_system.distribution.languages.expressions.service.internal import (
    DEFAULT_OPERATIONS,
)
from kg_build_system.distribution.languages.meaning.service.internal import (
    render_meaning,
    render_meaning_expression,
)
from kg_build_system.distribution.service.internal.rendering import (
    class_name,
    member_name,
    render_annotation,
    render_logical_type,
)
from kg_build_system.distribution.languages.data.model.internal.dto.blueprint_dto import (
    DataPartDTO,
    RowDistinctDTO,
    RowFilterDTO,
    RowGroupByDTO,
    RowJoinDTO,
    RowOperationDTO,
    RowOrderByDTO,
    RowScanDTO,
    RowUnionDTO,
    RowUnnestDTO,
)
from kg_build_system.kernel import SourceFragment
from kg_build_system.kernel.model.internal.json import thaw_json
from kg_build_system.kernel.model.internal.types.dto import (
    ArrayTypeDTO,
    CustomTypeDTO,
    LogicalTypeDTO,
    NullableTypeDTO,
    StructTypeDTO,
    UnitTypeDTO,
)
from kg_build_system.kernel.model.public.types import LogicalType, NullableType
from kg_build_system.kernel.service.internal.types import type_from_dto, type_to_dto

from ...model.internal.dto.blueprint_dto import (
    BindingDTO,
    EdgeBindingDTO,
    NodeBindingDTO,
    RowPlanDTO,
)

_UNIT_NAMES = {
    "bool": "BOOL",
    "int": "INT",
    "float": "FLOAT",
    "str": "STR",
    "date": "DATE",
    "time": "TIME",
    "timestamp": "TIMESTAMP",
    "uuid": "UUID",
}

_TYPE_IMPORT = (
    "from kg_build_system import "
    "ArrayType, NullableType, "
    "BOOL, DATE, FLOAT, INT, STR, TIME, TIMESTAMP, UUID"
)
_TYPE_INTERNAL_IMPORT = (
    "from kg_build_system.kernel.model.public.types import CustomType, StructType"
)
_BUILTIN_OPERATIONS = frozenset(spec.name for spec in DEFAULT_OPERATIONS)
_BIND_REFERENCE_IMPORT = (
    "from kg_build_system.distribution.languages.binding.service.internal.source "
    "import bind_reference"
)


def bind_reference(
    function: Any, *, module: str, qualname: str, signature: str,
) -> Any:
    """Attach the original Python reference to a generated ``bind`` callable.

    The generated lambda evaluates the already-transcribed values, but the
    blueprint needs the original module, qualified name and signature to stay
    stable across the source round trip. The helper returns the same callable.

    Example:
        ```python
        from kg_build_system.distribution.languages.binding.service.internal.source import (
            bind_reference,
        )

        function = bind_reference(
            lambda row: row,
            module="example.bindings",
            qualname="build_unit",
            signature="(row)",
        )
        assert function.__module__ == "example.bindings"
        ```
    """
    function.__module__ = module
    function.__qualname__ = qualname
    function.__kbs_signature__ = signature
    return function


def _render_type(value: LogicalTypeDTO) -> str:
    if isinstance(value, UnitTypeDTO):
        return _UNIT_NAMES.get(value.name, value.name)
    if isinstance(value, NullableTypeDTO):
        return f"NullableType({_render_type(value.value)})"
    if isinstance(value, ArrayTypeDTO):
        return f"ArrayType({_render_type(value.item)})"
    if isinstance(value, CustomTypeDTO):
        return f"CustomType({value.module!r}, {value.qualname!r})"
    if isinstance(value, StructTypeDTO):
        return f"StructType({value.module!r}, {value.qualname!r})"
    raise TypeError(f"unsupported logical type {value!r}")


def _base_type(value: LogicalTypeDTO) -> LogicalTypeDTO:
    if isinstance(value, NullableTypeDTO):
        return value.value
    return value


def _access_type(value: LogicalType) -> LogicalType:
    if isinstance(value, NullableType):
        return value
    return NullableType(value)


def _access_declarations(
    data: DataPartDTO,
) -> dict[str, tuple[ShapeField, ...]]:
    """Row shapes as the data language reads them: source members are nullable."""
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


def _type_names(data: DataPartDTO) -> dict[str, str]:
    """The generated class name of every declared struct, by every alias."""
    names: dict[str, str] = {}
    for struct in data.structs:
        own_name = class_name(struct.name, "Struct")
        names[struct.name] = own_name
        names[struct.name[:1].upper() + struct.name[1:]] = own_name
        names[own_name] = own_name
        names[own_name.removesuffix("Struct")] = own_name
    return names


def _shape_type_source(
    value: LogicalTypeDTO,
    imports: set[str],
    type_names: Mapping[str, str],
) -> str:
    if isinstance(value, NullableTypeDTO):
        return f"{_shape_type_source(value.value, imports, type_names)} | None"
    if isinstance(value, ArrayTypeDTO):
        imports.add("from kg_build_system import Array")
        return f"Array[{_shape_type_source(value.item, imports, type_names)}]"
    if isinstance(value, StructTypeDTO):
        return type_names.get(
            value.qualname,
            type_names.get(value.qualname.removesuffix("Struct"), value.qualname),
        )
    if isinstance(value, CustomTypeDTO):
        if value.module and value.module != "builtins":
            imports.add(f"import {value.module}")
            return f"{value.module}.{value.qualname}"
        return value.qualname
    return render_logical_type(value, imports)


def _shape_name(prefix: str, fields: tuple[ShapeField, ...]) -> str:
    signature = tuple(
        (field.attribute, field.name, field.logical_type) for field in fields
    )
    digest = sha256(repr(signature).encode("utf-8")).hexdigest()[:16]
    return f"_{prefix}{digest}"


def _shape_helper_source(
    prefix: str,
    fields: tuple[ShapeField, ...],
    imports: set[str],
    type_names: Mapping[str, str],
) -> str:
    name = _shape_name(prefix, fields)
    imports.add("from kg_build_system import Selection, Shape")
    lines = [f"class {name}(Shape):"]
    for field in fields:
        annotation = _shape_type_source(
            type_to_dto(field.logical_type), imports, type_names,
        )
        lines.append(f"    {field.attribute}: Selection[{annotation}]")
    return "\n".join(lines)


def _shape_reference(
    prefix: str,
    fields: tuple[ShapeField, ...],
    imports: set[str],
    type_names: Mapping[str, str],
    helpers: dict[object, str],
) -> str:
    key = (prefix, fields)
    helpers.setdefault(
        key, _shape_helper_source(prefix, fields, imports, type_names),
    )
    return _shape_name(prefix, fields)


def _render_value(value: Any) -> str:
    if isinstance(value, tuple):
        return "[" + ", ".join(_render_value(item) for item in value) + "]"
    if isinstance(value, Mapping):
        return "{" + ", ".join(
            f"{key!r}: {_render_value(item)}" for key, item in value.items()
        ) + "}"
    return repr(value)


def _render_expression(
    value: ExpressionDTO,
    *,
    class_names: Mapping[str, str],
    imports: set[str],
    row_variable: str = "row",
    row_source_name: str | None = None,
    row_effects: Mapping[str, str] | None = None,
) -> str:
    if isinstance(value, LiteralExpressionDTO):
        return (
            f"value_expression({_render_value(value.value)}, "
            f"logical_type={_render_type(value.logical_type)})"
        )
    if isinstance(value, VariableExpressionDTO):
        return value.name
    if isinstance(value, FieldReferenceDTO):
        if row_source_name is not None and value.field.relation == row_source_name:
            base = row_variable
        else:
            owner = class_names.get(value.field.relation)
            base = owner if owner is not None else row_variable
        result = f"{base}.{value.field.field}"
        for member in value.path:
            result += f".extract(lambda value: value.{member})"
        return result
    if isinstance(value, LookupExpressionDTO):
        target = class_names.get(value.relation.name, value.relation.name)
        key = _render_expression(
            value.key, class_names=class_names, imports=imports, row_variable=row_variable,
            row_source_name=row_source_name, row_effects=row_effects,
        )
        return (
            f"{key}.lookup({target}, {key}, "
            f"target_key={value.target_field!r})"
        )
    if isinstance(value, OperationExpressionDTO):
        arguments = [
            _render_expression(
                item, class_names=class_names, imports=imports, row_variable=row_variable,
                row_source_name=row_source_name, row_effects=row_effects,
            )
            for item in value.arguments
        ]
        parameters = ", ".join(
            f"{item.name}={_render_value(item.value)}"
            for item in value.parameters
        )
        operator = value.operator.name
        if operator == "drop_null" and arguments:
            return f"{arguments[0]}.alter_rows().drop_null()"
        if operator == "expand" and arguments:
            return f"{arguments[0]}.alter_rows().expand()"
        if operator == "drop_if" and len(arguments) >= 2:
            suffix = f", {parameters}" if parameters else ""
            return (
                f"{arguments[0]}.alter_rows().drop_if("
                f"lambda value: {arguments[1]}{suffix})"
            )
        if operator == "struct_field" and arguments:
            name = next(
                (item.value for item in value.parameters if item.name == "name"),
                None,
            )
            return (
                f"{arguments[0]}.extract(lambda value: value.{name})"
                if isinstance(name, str) and name else arguments[0]
            )
        if operator not in _BUILTIN_OPERATIONS:
            effect = (row_effects or {}).get(operator, "preserve")
            if effect == "expand":
                raise TypeError(
                    "cannot render a project expand operation in binding source"
                )
            imports.add(
                "from kg_build_system.distribution.languages.expressions.service.internal "
                "import as_expression, operation, select_expression"
            )
            node_arguments = ", ".join(
                f"as_expression({argument}).model" for argument in arguments
            )
            suffix = f", {parameters}" if parameters else ""
            semantics = ""
            if effect == "filter":
                imports.add(
                    "from kg_build_system.distribution.languages.expressions.model.internal "
                    "import RowSemantics"
                )
                semantics = ", row_semantics=RowSemantics('filter')"
            return (
                f"select_expression(operation({operator!r}, {node_arguments}"
                f"{suffix}, logical_type={_render_type(value.logical_type)}"
                f"{semantics}))"
            )
        methods = {
            "distinct": "unique", "join": "concat", "array_at": "at",
            "array_slice": "slice", "subtract": "sub", "not": "not_",
            "and": "and_", "or": "or_", "coalesce": "default_to",
        }
        method = methods.get(operator, operator)
        if arguments:
            suffix = f", {parameters}" if parameters else ""
            return (
                f"{arguments[0]}.{method}("
                f"{', '.join(arguments[1:])}{suffix})"
            )
        return f"{row_variable}.{method}({parameters})"
    raise TypeError(f"unsupported expression DTO {value!r}")


def _render_plan(
    value: RowPlanDTO,
    *,
    class_names: Mapping[str, str],
    imports: set[str],
    declarations: Mapping[str, tuple[ShapeField, ...]],
    type_names: Mapping[str, str],
    helpers: dict[object, str],
) -> str:
    def child(plan: RowPlanDTO) -> str:
        return _render_plan(
            plan, class_names=class_names, imports=imports,
            declarations=declarations, type_names=type_names, helpers=helpers,
        )

    if isinstance(value, RowScanDTO):
        name = value.relation.name
        return f"{class_names.get(name, name)}.row_source()"
    if isinstance(value, RowFilterDTO):
        inner = child(value.input)
        predicate = _render_expression(value.predicate, class_names=class_names, imports=imports)
        return f"{inner}.where(lambda row: {predicate})"
    if isinstance(value, RowUnionDTO):
        left = child(value.left)
        right = child(value.right)
        return f"{left}.union({right}, all={value.all!r})"
    if isinstance(value, RowJoinDTO):
        left = child(value.left)
        right = child(value.right)
        left_key = _render_expression(
            value.left_key, class_names=class_names, imports=imports, row_variable="left",
        )
        right_key = _render_expression(
            value.right_key, class_names=class_names, imports=imports, row_variable="right",
        )
        return (
            f"{left}.join({right}, on=lambda left, right: "
            f"({left_key}, {right_key}), how={value.how!r})"
        )
    if isinstance(value, RowGroupByDTO):
        inner = child(value.input)
        fields = tuple(
            ShapeField(
                name, name, type_from_dto(_base_type(expression.logical_type)),
            )
            for name, expression in value.keys
        )
        if not fields:
            raise ValueError("group_by requires at least one key")
        keys_shape = _shape_reference(
            "KeyShape", fields, imports, type_names, helpers,
        )
        keys = ", ".join(
            f"{name!r}: {_render_expression(expression, class_names=class_names, imports=imports)}"
            for name, expression in value.keys
        )
        return (
            f"{inner}.group_by(keys={keys_shape}, "
            f"by=lambda row: {{{keys}}})"
        )
    if isinstance(value, RowDistinctDTO):
        inner = child(value.input)
        return f"{inner}.distinct()"
    if isinstance(value, RowOrderByDTO):
        inner = child(value.input)
        keys = ", ".join(
            _render_expression(expression, class_names=class_names, imports=imports)
            for expression, _ in value.keys
        )
        ascending = value.keys[0][1] if value.keys else True
        return f"{inner}.order_by({keys}, ascending={ascending!r})"
    if isinstance(value, RowUnnestDTO):
        if not declarations:
            raise ValueError(
                "rendering an unnested binding row source requires the data part"
            )
        inner = child(value.input)
        expression = _render_expression(
            value.expression, class_names=class_names, imports=imports,
        )
        fields = plan_fields(value, declarations)
        out_shape = _shape_reference(
            "UnnestShape", fields, imports, type_names, helpers,
        )
        return f"{inner}.unnest(lambda row: {expression}, out={out_shape})"
    if isinstance(value, RowOperationDTO):
        inner = child(value.input)
        fields = tuple(value.output)
        shape_name = _shape_reference(
            "RelationOperationOutput", fields, imports, type_names, helpers,
        )
        digest = sha256(repr(
            (value.operation, shape_name, value.grain)
        ).encode("utf-8")).hexdigest()[:16]
        spec_name = f"_relation_operation_spec_{digest}"
        operation_name = f"_relation_operation_{digest}"
        helpers.setdefault(
            ("relation_operation", digest),
            "\n".join((
                f"{spec_name} = RelationOperationSpec(",
                f"    name={value.operation!r},",
                f"    output={shape_name},",
                f"    grain={value.grain!r},",
                ")",
                f"{operation_name} = RelationOperation({spec_name})",
            )),
        )
        imports.add(
            "from kg_build_system import RelationOperation, RelationOperationSpec"
        )
        if not value.parameters:
            return f"{inner}.custom_op({operation_name})"
        parameters = ", ".join(
            f"{parameter.name!r}: {_render_value(thaw_json(parameter.value))}"
            for parameter in value.parameters
        )
        return f"{inner}.custom_op({operation_name}, **{{{parameters}}})"
    raise TypeError(f"unsupported row plan {value!r}")


def _plan_sources(value: RowPlanDTO) -> tuple[str, ...]:
    if isinstance(value, RowScanDTO):
        return (value.relation.name,)
    if isinstance(value, (
        RowFilterDTO, RowDistinctDTO, RowOrderByDTO, RowGroupByDTO,
        RowUnnestDTO, RowOperationDTO,
    )):
        return _plan_sources(value.input)
    if isinstance(value, (RowUnionDTO, RowJoinDTO)):
        return (*_plan_sources(value.left), *_plan_sources(value.right))
    return ()


def _expression_sources(value: ExpressionDTO) -> tuple[str, ...]:
    if isinstance(value, FieldReferenceDTO):
        return (value.field.relation,)
    if isinstance(value, LookupExpressionDTO):
        return (value.relation.name, *_expression_sources(value.key))
    if isinstance(value, OperationExpressionDTO):
        return tuple(
            source
            for argument in value.arguments
            for source in _expression_sources(argument)
        )
    return ()


def _binding_expression_sources(binding: BindingDTO) -> tuple[str, ...]:
    values: list[ExpressionDTO] = [binding.identity, *(
        expression for _, expression in binding.properties
    )]
    if isinstance(binding, EdgeBindingDTO):
        values.extend((binding.source_identity, binding.target_identity))
    return tuple(
        source for value in values for source in _expression_sources(value)
    )


def _annotations_source(
    annotations: tuple[AnnotationDTO, ...],
    imports: set[str],
) -> str | None:
    if not annotations:
        return None
    rendered = ", ".join(render_annotation(item, imports) for item in annotations)
    return f"annotations=({rendered},)"


def _python_values_lines(
    binding: BindingDTO,
    *,
    class_names: Mapping[str, str],
    imports: set[str],
    row_source_name: str | None = None,
    row_effects: Mapping[str, str] | None = None,
    indent: str = "        ",
) -> list[str]:
    target = class_name(
        binding.component,
        "Node" if isinstance(binding, NodeBindingDTO) else "Edge",
    )
    if isinstance(binding, EdgeBindingDTO):
        values = [
            f"{indent}build_key={_render_expression(binding.identity, class_names=class_names, imports=imports, row_source_name=row_source_name, row_effects=row_effects)},",
            f"{indent}source_build_key={_render_expression(binding.source_identity, class_names=class_names, imports=imports, row_source_name=row_source_name, row_effects=row_effects)},",
            f"{indent}target_build_key={_render_expression(binding.target_identity, class_names=class_names, imports=imports, row_source_name=row_source_name, row_effects=row_effects)},",
        ]
    else:
        values = [
            f"{indent}build_key={_render_expression(binding.identity, class_names=class_names, imports=imports, row_source_name=row_source_name, row_effects=row_effects)},",
        ]
    values.append(f"{indent}properties={target}(")
    for property_name, expression in binding.properties:
        values.append(
            f"{indent}    {member_name(property_name)}="
            f"{_render_expression(expression, class_names=class_names, imports=imports, row_source_name=row_source_name, row_effects=row_effects)},"
        )
    values.append(f"{indent}),")
    return values


def _binding_source(
    binding: BindingDTO,
    *,
    name: str,
    class_names: Mapping[str, str],
    imports: set[str],
    declarations: Mapping[str, tuple[ShapeField, ...]],
    type_names: Mapping[str, str],
    helpers: dict[object, str],
    row_effects: Mapping[str, str] | None = None,
) -> list[str]:
    row_source_name = (
        None if binding.rows is None
        else plan_shape_source_name(binding.rows)
    )
    target = class_name(
        binding.component,
        "Node" if isinstance(binding, NodeBindingDTO) else "Edge",
    )
    factory = "node_binding" if isinstance(binding, NodeBindingDTO) else "edge_binding"
    imports.add(f"from kg_build_system import {factory}")
    lines = [f"{name} = {factory}(", f"    target={target},"]
    if binding.mode == "python":
        values_type = (
            "EdgeValues" if isinstance(binding, EdgeBindingDTO) else "NodeValues"
        )
        imports.add(f"from kg_build_system import {values_type}")
        if binding.rows is not None:
            rows = _render_plan(
                binding.rows, class_names=class_names, imports=imports,
                declarations=declarations, type_names=type_names,
                helpers=helpers,
            )
            lines.append(f"    rows={rows},")
        if binding.python_ref is not None:
            imports.add(_BIND_REFERENCE_IMPORT)
            reference = binding.python_ref
            lines.append("    bind=bind_reference(")
            lines.append(f"        lambda row: {values_type}(")
            lines.extend(_python_values_lines(
                binding, class_names=class_names, imports=imports,
                row_source_name=row_source_name, row_effects=row_effects,
                indent="            ",
            ))
            lines.append("        ),")
            lines.append(f"        module={reference.module!r},")
            lines.append(f"        qualname={reference.qualname!r},")
            lines.append(f"        signature={reference.signature!r},")
            lines.append("    ),")
        else:
            lines.append(f"    bind=lambda row: {values_type}(")
            lines.extend(_python_values_lines(
                binding, class_names=class_names, imports=imports,
                row_source_name=row_source_name, row_effects=row_effects,
            ))
            lines.append("    ),")
    else:
        lines.append(
            f"    build_key={_render_expression(binding.identity, class_names=class_names, imports=imports, row_source_name=row_source_name, row_effects=row_effects)},"
        )
        if isinstance(binding, EdgeBindingDTO):
            lines.append(
                f"    source_build_key={_render_expression(binding.source_identity, class_names=class_names, imports=imports, row_source_name=row_source_name, row_effects=row_effects)},"
            )
            lines.append(
                f"    target_build_key={_render_expression(binding.target_identity, class_names=class_names, imports=imports, row_source_name=row_source_name, row_effects=row_effects)},"
            )
        lines.append(f"    properties={target}(")
        for property_name, expression in binding.properties:
            lines.append(
                f"        {member_name(property_name)}="
                f"{_render_expression(expression, class_names=class_names, imports=imports, row_source_name=row_source_name, row_effects=row_effects)},"
            )
        lines.append("    ),")
    annotations = _annotations_source(binding.annotations, imports)
    if binding.meaning is not None and annotations is None:
        meaning = render_meaning(binding.meaning)
        imports.update(meaning.imports)
        lines.extend(f"    {line}" for line in meaning.body.splitlines())
    if isinstance(binding, EdgeBindingDTO):
        if binding.source_node is not None:
            imports.add("from kg_build_system import endpoint")
            lines.append(
                "    source_node=endpoint("
                f"{class_name(binding.source_node.name, 'Node')}),"
            )
        if binding.target_node is not None:
            imports.add("from kg_build_system import endpoint")
            lines.append(
                "    target_node=endpoint("
                f"{class_name(binding.target_node.name, 'Node')}),"
            )
    if binding.name is not None:
        lines.append(f"    name={binding.name!r},")
    if annotations is not None:
        if binding.meaning is None:
            raise ValueError("a binding annotation requires a binding meaning")
        meaning = render_meaning(binding.meaning)
        imports.update(meaning.imports)
        expression = render_meaning_expression(binding.meaning)
        expression_lines = expression.splitlines()
        imports.add("from kg_build_system import BindingOptions")
        lines.append("    options=BindingOptions(")
        lines.append(f"        meaning={expression_lines[0]}")
        tail = expression_lines[1:]
        for index, line in enumerate(tail):
            comma = "," if index == len(tail) - 1 else ""
            lines.append(f"        {line}{comma}")
        lines.append(f"        {annotations},")
        lines.append("    ),")
    lines.append(")")
    return lines


def render_binding_source(
    bindings: Sequence[BindingDTO],
    context: Any = None,
    *,
    data: DataPartDTO | None = None,
    operations: Any = None,
) -> SourceFragment:
    """Render binding DTOs as authoring source.

    Direct bindings render as ``node_binding(build_key=..., properties=...)``;
    Python bindings render with their row plan and a ``bind`` lambda that
    returns ``NodeValues`` or ``EdgeValues``. The target is always named by its
    logical graph name, never by a Python symbol. A grouped or unnested row
    plan emits a generated ``Shape`` class beside the binding; an unnested plan
    reads the row members from ``data``.

    Example:
        ```python
        from kg_build_system.distribution.languages.binding.service.internal import (
            render_binding_source,
        )

        fragment = render_binding_source(())
        assert fragment.body == ""
        ```
    """
    del context
    class_names: dict[str, str] = {}
    for binding in bindings:
        if binding.rows is not None:
            for source in _plan_sources(binding.rows):
                class_names.setdefault(source, class_name(source, "SourceRelation"))
        for source in _binding_expression_sources(binding):
            class_names.setdefault(source, class_name(source, "SourceRelation"))
    declarations = (
        _access_declarations(data) if data is not None else {}
    )
    type_names = _type_names(data) if data is not None else {}
    imports: set[str] = {
        "from kg_build_system import value_expression",
        _TYPE_IMPORT,
        _TYPE_INTERNAL_IMPORT,
    }
    helpers: dict[object, str] = {}
    row_effects = (
        {item.name: item.row_effect for item in operations.operations}
        if operations is not None else {}
    )
    chunks: list[str] = []
    used: set[str] = set()
    for index, binding in enumerate(bindings):
        base = f"{member_name(binding.component)}_binding"
        name = base if base not in used else f"{base}_{index}"
        used.add(name)
        chunks.append("\n".join(_binding_source(
            binding, name=name, class_names=class_names, imports=imports,
            declarations=declarations, type_names=type_names,
            helpers=helpers, row_effects=row_effects,
        )))
    body = "\n\n\n".join((*helpers.values(), *chunks))
    if body:
        body += "\n"
    return SourceFragment(
        kind="declaration", body=body, imports=tuple(sorted(imports)),
    )


__all__ = ["render_binding_source"]
