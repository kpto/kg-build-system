"""Cross-declaration validation for build blueprints."""
from __future__ import annotations

from collections.abc import Iterable

from ..expressions.ir import (
    FieldReferenceExpressionIR as FieldReferenceExpression,
    OperationExpressionIR as OperationExpression,
    walk_expression_ir as walk_expression,
)
from ..types.ir import (
    ArrayTypeIR as ArrayType,
    NullableTypeIR as NullableType,
    StructTypeIR as StructType,
)
from ..binding.ir import EdgeBindingIR as EdgeBindingDefinition
from ..table.ir import struct_type_key
from .models import BLUEPRINT_SCHEMA_VERSION, BuildBlueprint


def _unique(values: Iterable[str], context: str) -> None:
    items = tuple(values)
    if len(items) != len(set(items)):
        raise ValueError(f"{context} must be unique")


def _base(value):
    return value.value if isinstance(value, NullableType) else value


def validate_blueprint(blueprint: BuildBlueprint) -> None:
    """Validate names, references, expression sources, and binding shapes."""
    if blueprint.schema_version != BLUEPRINT_SCHEMA_VERSION:
        raise ValueError(f"unsupported blueprint schema version {blueprint.schema_version!r}")
    if not blueprint.components:
        raise ValueError("blueprints require at least one graph component")
    if not blueprint.bindings:
        raise ValueError("blueprints require at least one graph binding")

    _unique((item.symbol_id for item in (*blueprint.structs, *blueprint.tables, *blueprint.components, *blueprint.projections, *blueprint.bindings, *blueprint.sources)), "blueprint symbol IDs")
    # Struct identity is (module, qualname) inside the symbol ID; the logical
    # name is display, so same-named structs from different modules are legal —
    # exactly what generated packages emit for per-file nested records. Only
    # same-module name collisions are ambiguous.
    _unique(
        (
            f"{key[0]}::{item.name}"
            for item in blueprint.structs
            if (key := struct_type_key(item)) is not None
        ),
        "struct names within a module",
    )
    _unique((item.name for item in blueprint.tables), "table names")
    _unique((item.name for item in blueprint.components), "component names")
    _unique((item.name for item in blueprint.projections), "projection names")
    _unique((item.name for item in (*blueprint.tables, *blueprint.projections)), "logical source names")
    _unique((item.module_id for item in blueprint.modules), "module IDs")

    for declaration in (*blueprint.structs, *blueprint.tables):
        _unique((field.name for field in declaration.fields), f"{declaration.name} field names")
    for component in blueprint.components:
        _unique((prop.name for prop in component.properties), f"{component.name} property names")
        if component.kind == "edge":
            if not component.source or not component.target:
                raise ValueError(f"edge {component.name!r} requires source and target components")
        elif component.source is not None or component.target is not None:
            raise ValueError(f"node {component.name!r} may not declare endpoints")
    component_by_name = {item.name: item for item in blueprint.components}
    component_by_symbol = {item.symbol_id: item for item in blueprint.components}
    for component in blueprint.components:
        if component.kind == "edge" and (component.source not in component_by_name or component.target not in component_by_name):
            raise ValueError(f"edge {component.name!r} references an unknown endpoint")
    for component in blueprint.components:
        if component.parent is None:
            continue
        parent = component_by_symbol.get(component.parent)
        if parent is None:
            raise ValueError(f"component {component.name!r} references an unknown parent")
        if not parent.abstract or parent.kind != component.kind:
            raise ValueError(
                f"component {component.name!r} parent must name an abstract "
                f"{component.kind} component"
            )

    def descend_or_self(name: str, ancestor: str) -> bool:
        seen: set[str] = set()
        current: str | None = name
        while current is not None and current not in seen:
            if current == ancestor:
                return True
            seen.add(current)
            parent_symbol = component_by_name[current].parent
            current = None if parent_symbol is None else component_by_symbol[parent_symbol].name
        return False

    for component in blueprint.components:
        seen: set[str] = set()
        current_symbol: str | None = component.parent
        while current_symbol is not None:
            if current_symbol == component.symbol_id or current_symbol in seen:
                raise ValueError(
                    "component parent chain cycle includes "
                    f"{component_by_symbol[current_symbol].name!r}"
                )
            seen.add(current_symbol)
            current_symbol = component_by_symbol[current_symbol].parent

    sources = {item.name for item in blueprint.tables} | {item.name for item in blueprint.projections}
    source_fields = {
        item.name: {field.name for field in item.fields}
        for item in (*blueprint.tables, *blueprint.projections)
    }
    projection_by_name = {item.name: item for item in blueprint.projections}
    dependencies: dict[str, set[str]] = {name: set() for name in projection_by_name}

    def validate_expression(expression, *, owner: str) -> None:
        nodes = tuple(walk_expression(expression))
        for node in nodes:
            if isinstance(node, OperationExpression) and node.operator == "expand":
                if len(node.arguments) != 1:
                    raise ValueError(f"{owner} expand operation requires one argument")
                input_type = _base(node.arguments[0].logical_type)
                if not isinstance(input_type, ArrayType):
                    raise ValueError(f"{owner} expand operation requires an array argument")
                if node.logical_type != input_type.item:
                    raise ValueError(f"{owner} expand operation has an incompatible result type")
            if not isinstance(node, FieldReferenceExpression):
                continue
            if node.source not in sources:
                raise ValueError(f"{owner} references unknown logical source {node.source!r}")
            if node.path[0] not in source_fields[node.source]:
                raise ValueError(
                    f"{owner} references unknown field {node.path[0]!r} "
                    f"on logical source {node.source!r}"
                )
            if node.source in projection_by_name and owner in dependencies:
                dependencies[owner].add(node.source)

    for projection in blueprint.projections:
        _unique((field.name for field in projection.fields), f"{projection.name} projection field names")
        for field in projection.fields:
            validate_expression(field.expression, owner=projection.name)

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

    table_names = {item.name for item in blueprint.tables}
    _unique((source.table for source in blueprint.sources), "source-bound table names")
    if any(source.table not in table_names for source in blueprint.sources):
        raise ValueError("a physical source references an unknown table")

    for binding in blueprint.bindings:
        component = component_by_name.get(binding.component)
        if component is None or component.kind != binding.kind:
            raise ValueError(f"{binding.kind} binding {binding.symbol_id!r} targets an incompatible component")
        if component.abstract:
            raise ValueError(
                f"{binding.kind} binding {binding.symbol_id!r} may not target "
                f"abstract component {component.name!r}"
            )
        if isinstance(binding, EdgeBindingDefinition):
            for side, declared, supplied in (
                ("source", component.source, binding.source_node),
                ("target", component.target, binding.target_node),
            ):
                # Edge components are validated to declare both endpoints.
                assert declared is not None
                resolved = supplied if supplied is not None else declared
                endpoint = component_by_name.get(resolved)
                if endpoint is None or endpoint.kind != "node" or endpoint.abstract:
                    raise ValueError(
                        f"edge binding {binding.symbol_id!r} {side} endpoint "
                        f"{resolved!r} must name a concrete node component"
                    )
                if not descend_or_self(resolved, declared):
                    raise ValueError(
                        f"edge binding {binding.symbol_id!r} {side} endpoint "
                        f"{resolved!r} must equal or descend from the declared "
                        f"endpoint {declared!r}"
                    )
        expressions = [
            binding.build_key,
            *(expression for _, expression in binding.properties),
        ]
        keys = [binding.build_key]
        if isinstance(binding, EdgeBindingDefinition):
            expressions.extend((binding.source_build_key, binding.target_build_key))
            keys.extend((binding.source_build_key, binding.target_build_key))
        for expression in expressions:
            validate_expression(expression, owner=binding.symbol_id)
        expected = {prop.name: prop.logical_type for prop in component.properties}
        actual = dict(binding.properties)
        if set(actual) != set(expected):
            raise ValueError(f"binding {binding.symbol_id!r} must map every declared component property exactly once")
        for name, expression in actual.items():
            expected_type = expected[name]
            if expected_type != expression.logical_type and not (
                isinstance(expected_type, NullableType) and expected_type.value == expression.logical_type
            ):
                raise ValueError(f"binding {binding.symbol_id!r} property {name!r} has an incompatible logical type")
        for key in keys:
            logical_type = _base(key.logical_type)
            if isinstance(key.logical_type, NullableType) or isinstance(logical_type, (ArrayType, StructType)):
                raise ValueError(f"binding {binding.symbol_id!r} keys must be non-null scalar expressions")


__all__ = ["validate_blueprint"]
