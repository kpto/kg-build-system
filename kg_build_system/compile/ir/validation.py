"""Cross-declaration validation for version-2 blueprints."""
from __future__ import annotations

from collections.abc import Iterable

from ...expressions import FieldReferenceExpression, walk_expression
from ...types import ArrayType, NullableType, StructType
from .models import BuildBlueprint, EdgeBindingDefinition


def _unique(values: Iterable[str], context: str) -> None:
    items = tuple(values)
    if len(items) != len(set(items)):
        raise ValueError(f"{context} must be unique")


def _base(value):
    return value.value if isinstance(value, NullableType) else value


def validate_blueprint(blueprint: BuildBlueprint) -> None:
    """Validate names, references, expression sources, and binding shapes."""
    if blueprint.schema_version != 2:
        raise ValueError(f"unsupported blueprint schema version {blueprint.schema_version!r}")
    if not blueprint.components:
        raise ValueError("blueprints require at least one graph component")
    if not blueprint.bindings:
        raise ValueError("blueprints require at least one graph binding")

    _unique((item.symbol_id for item in (*blueprint.structs, *blueprint.tables, *blueprint.components, *blueprint.projections, *blueprint.bindings, *blueprint.sources)), "blueprint symbol IDs")
    _unique((item.name for item in blueprint.structs), "struct names")
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
    for component in blueprint.components:
        if component.kind == "edge" and (component.source not in component_by_name or component.target not in component_by_name):
            raise ValueError(f"edge {component.name!r} references an unknown endpoint")

    sources = {item.name for item in blueprint.tables} | {item.name for item in blueprint.projections}
    source_fields = {
        item.name: {field.name for field in item.fields}
        for item in (*blueprint.tables, *blueprint.projections)
    }
    projection_by_name = {item.name: item for item in blueprint.projections}
    dependencies: dict[str, set[str]] = {name: set() for name in projection_by_name}

    def validate_expression(expression, *, owner: str) -> None:
        nodes = tuple(walk_expression(expression))
        array_paths = {
            (node.source, *traversal.path)
            for node in nodes
            if isinstance(node, FieldReferenceExpression)
            for traversal in node.traversals
            if traversal.kind == "array"
        }
        for node in nodes:
            for effect in node.row_semantics.effects:
                if effect.mode == "expand" and effect.scope not in array_paths:
                    raise ValueError(f"{owner} expands undeclared array traversal {effect.scope!r}")
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
        expressions = [binding.build_key, *(expression for _, expression in binding.properties)]
        if isinstance(binding, EdgeBindingDefinition):
            expressions.extend((binding.source_build_key, binding.target_build_key))
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
        for key in expressions[:1] + (expressions[-2:] if isinstance(binding, EdgeBindingDefinition) else []):
            logical_type = _base(key.logical_type)
            if isinstance(key.logical_type, NullableType) or isinstance(logical_type, (ArrayType, StructType)):
                raise ValueError(f"binding {binding.symbol_id!r} keys must be non-null scalar expressions")


__all__ = ["validate_blueprint"]
