"""Render the binding blueprint DTO as authoring source."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from kg_build_system.declaration.foundations.annotations.model.internal.dto import (
    AnnotationDTO,
)
from kg_build_system.declaration.foundations.expressions.model.internal.dto import (
    ExpressionDTO,
    FieldReferenceDTO,
    LiteralExpressionDTO,
    OperationExpressionDTO,
    VariableExpressionDTO,
)
from kg_build_system.declaration.service.internal.rendering import class_name, member_name, render_annotation
from kg_build_system.declaration.languages.table.model.internal.dto.blueprint_dto import (
    RowDistinctDTO,
    RowFilterDTO,
    RowGroupByDTO,
    RowJoinDTO,
    RowOrderByDTO,
    RowScanDTO,
    RowUnionDTO,
)
from kg_build_system.kernel import SourceFragment
from kg_build_system.kernel.model.internal.types.dto import (
    ArrayTypeDTO,
    CustomTypeDTO,
    LogicalTypeDTO,
    NullableTypeDTO,
    StructTypeDTO,
    UnitTypeDTO,
)

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
_BIND_REFERENCE_IMPORT = (
    "from kg_build_system.declaration.languages.binding.service.internal.source "
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
        from kg_build_system.declaration.languages.binding.service.internal.source import (
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
    row_variable: str = "row",
) -> str:
    if isinstance(value, LiteralExpressionDTO):
        return (
            f"value_expression({_render_value(value.value)}, "
            f"logical_type={_render_type(value.logical_type)})"
        )
    if isinstance(value, VariableExpressionDTO):
        return value.name
    if isinstance(value, FieldReferenceDTO):
        owner = class_names.get(value.source)
        base = owner if owner is not None else row_variable
        if not value.path:
            return base
        result = f"{base}.{value.path[0]}"
        for member in value.path[1:]:
            result += f".extract(lambda value: value.{member})"
        return result
    if isinstance(value, OperationExpressionDTO):
        arguments = [
            _render_expression(
                item, class_names=class_names, row_variable=row_variable,
            )
            for item in value.arguments
        ]
        parameters = ", ".join(
            f"{item.name}={_render_value(item.value)}"
            for item in value.parameters
        )
        if arguments:
            suffix = f", {parameters}" if parameters else ""
            return (
                f"{arguments[0]}.{value.operator}("
                f"{', '.join(arguments[1:])}{suffix})"
            )
        return f"{row_variable}.{value.operator}({parameters})"
    raise TypeError(f"unsupported expression DTO {value!r}")


def _render_plan(
    value: RowPlanDTO,
    *,
    class_names: Mapping[str, str],
) -> str:
    if isinstance(value, RowScanDTO):
        return f"{class_names.get(value.source, value.source)}.row_source()"
    if isinstance(value, RowFilterDTO):
        inner = _render_plan(value.input, class_names=class_names)
        predicate = _render_expression(value.predicate, class_names=class_names)
        return f"{inner}.where(lambda row: {predicate})"
    if isinstance(value, RowUnionDTO):
        left = _render_plan(value.left, class_names=class_names)
        right = _render_plan(value.right, class_names=class_names)
        return f"{left}.union({right}, all={value.all!r})"
    if isinstance(value, RowJoinDTO):
        left = _render_plan(value.left, class_names=class_names)
        right = _render_plan(value.right, class_names=class_names)
        left_key = _render_expression(
            value.left_key, class_names=class_names, row_variable="left",
        )
        right_key = _render_expression(
            value.right_key, class_names=class_names, row_variable="right",
        )
        return (
            f"{left}.join({right}, on=lambda left, right: "
            f"({left_key}, {right_key}), how={value.how!r})"
        )
    if isinstance(value, RowGroupByDTO):
        inner = _render_plan(value.input, class_names=class_names)
        keys = ", ".join(
            f"{name!r}: {_render_expression(expression, class_names=class_names)}"
            for name, expression in value.keys
        )
        return f"{inner}.group_by(by=lambda row: {{{keys}}})"
    if isinstance(value, RowDistinctDTO):
        inner = _render_plan(value.input, class_names=class_names)
        return f"{inner}.distinct()"
    if isinstance(value, RowOrderByDTO):
        inner = _render_plan(value.input, class_names=class_names)
        keys = ", ".join(
            _render_expression(expression, class_names=class_names)
            for expression, _ in value.keys
        )
        ascending = value.keys[0][1] if value.keys else True
        return f"{inner}.order_by({keys}, ascending={ascending!r})"
    raise TypeError(f"unsupported row plan {value!r}")


def _plan_sources(value: RowPlanDTO) -> tuple[str, ...]:
    if isinstance(value, RowScanDTO):
        return (value.source,)
    if isinstance(value, (RowFilterDTO, RowDistinctDTO, RowOrderByDTO)):
        return _plan_sources(value.input)
    if isinstance(value, (RowUnionDTO, RowJoinDTO)):
        return (*_plan_sources(value.left), *_plan_sources(value.right))
    if isinstance(value, RowGroupByDTO):
        return _plan_sources(value.input)
    return ()


def _expression_sources(value: ExpressionDTO) -> tuple[str, ...]:
    if isinstance(value, FieldReferenceDTO):
        return (value.source,)
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
    indent: str = "        ",
) -> list[str]:
    target = class_name(
        binding.component,
        "Node" if isinstance(binding, NodeBindingDTO) else "Edge",
    )
    if isinstance(binding, EdgeBindingDTO):
        values = [
            f"{indent}build_key={_render_expression(binding.identity, class_names=class_names)},",
            f"{indent}source_build_key={_render_expression(binding.source_identity, class_names=class_names)},",
            f"{indent}target_build_key={_render_expression(binding.target_identity, class_names=class_names)},",
        ]
    else:
        values = [
            f"{indent}build_key={_render_expression(binding.identity, class_names=class_names)},",
        ]
    values.append(f"{indent}properties={target}(")
    for property_name, expression in binding.properties:
        values.append(
            f"{indent}    {member_name(property_name)}="
            f"{_render_expression(expression, class_names=class_names)},"
        )
    values.append(f"{indent}),")
    return values


def _binding_source(
    binding: BindingDTO,
    *,
    name: str,
    class_names: Mapping[str, str],
    imports: set[str],
) -> list[str]:
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
            lines.append(
                f"    rows={_render_plan(binding.rows, class_names=class_names)},"
            )
        if binding.python_ref is not None:
            imports.add(_BIND_REFERENCE_IMPORT)
            reference = binding.python_ref
            lines.append("    bind=bind_reference(")
            lines.append(f"        lambda row: {values_type}(")
            lines.extend(_python_values_lines(
                binding, class_names=class_names, indent="            ",
            ))
            lines.append("        ),")
            lines.append(f"        module={reference.module!r},")
            lines.append(f"        qualname={reference.qualname!r},")
            lines.append(f"        signature={reference.signature!r},")
            lines.append("    ),")
        else:
            lines.append(f"    bind=lambda row: {values_type}(")
            lines.extend(_python_values_lines(binding, class_names=class_names))
            lines.append("    ),")
    else:
        lines.append(
            f"    build_key={_render_expression(binding.identity, class_names=class_names)},"
        )
        if isinstance(binding, EdgeBindingDTO):
            lines.append(
                f"    source_build_key={_render_expression(binding.source_identity, class_names=class_names)},"
            )
            lines.append(
                f"    target_build_key={_render_expression(binding.target_identity, class_names=class_names)},"
            )
        lines.append(f"    properties={target}(")
        for property_name, expression in binding.properties:
            lines.append(
                f"        {member_name(property_name)}="
                f"{_render_expression(expression, class_names=class_names)},"
            )
        lines.append("    ),")
    if isinstance(binding, EdgeBindingDTO):
        if binding.source_node is not None:
            imports.add("from kg_build_system import endpoint")
            lines.append(
                f"    source_node=endpoint({class_name(binding.source_node, 'Node')}),"
            )
        if binding.target_node is not None:
            imports.add("from kg_build_system import endpoint")
            lines.append(
                f"    target_node=endpoint({class_name(binding.target_node, 'Node')}),"
            )
    if binding.debug_name is not None:
        lines.append(f"    debug_name={binding.debug_name!r},")
    annotations = _annotations_source(binding.annotations, imports)
    if annotations is not None:
        imports.add("from kg_build_system import BindingOptions")
        lines.append(f"    options=BindingOptions({annotations}),")
    lines.append(")")
    return lines


def render_binding_source(
    bindings: Sequence[BindingDTO], context: Any = None,
) -> SourceFragment:
    """Render binding DTOs as authoring source.

    Direct bindings render as ``node_binding(build_key=..., properties=...)``;
    Python bindings render with their row plan and a ``bind`` lambda that
    returns ``NodeValues`` or ``EdgeValues``. The target is always named by its
    logical graph name, never by a Python symbol.

    Example:
        ```python
        from kg_build_system.declaration.languages.binding.service.internal import (
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
                class_names.setdefault(source, class_name(source, "Table"))
        for source in _binding_expression_sources(binding):
            class_names.setdefault(source, class_name(source, "Table"))
    imports: set[str] = {
        "from kg_build_system import value_expression",
        _TYPE_IMPORT,
        _TYPE_INTERNAL_IMPORT,
    }
    chunks: list[str] = []
    used: set[str] = set()
    for index, binding in enumerate(bindings):
        base = f"{member_name(binding.component)}_binding"
        name = base if base not in used else f"{base}_{index}"
        used.add(name)
        chunks.append("\n".join(_binding_source(
            binding, name=name, class_names=class_names, imports=imports,
        )))
    body = "\n\n\n".join(chunks)
    if body:
        body += "\n"
    return SourceFragment(
        kind="declaration", body=body, imports=tuple(sorted(imports)),
    )


__all__ = ["render_binding_source"]
