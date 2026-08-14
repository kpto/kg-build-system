"""Compile Python declarations into the canonical version-2 blueprint IR."""
from __future__ import annotations

import importlib
import importlib.util
import json
import sys
from collections.abc import Iterable, Sequence
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from types import ModuleType
from typing import Any, overload

from ..annotations import Annotation
from ..binding import Binding, EdgeBinding, NodeBinding
from ..expressions import FieldReferenceExpression, ValueExpression, encode_expression, walk_expression
from ..expressions.base import freeze_json
from ..table import BoundSource, BoundTable, Projection, Struct, Table
from ..table.declarations import resolve_bound_source
from ..types import ArrayType, NullableType, StructType
from ..workflow.interfaces import ModuleRegistration
from .ir import (
    AnnotationDefinition, BlueprintModule, BuildBlueprint, ComponentDefinition,
    EdgeBindingDefinition, FieldDefinition, NodeBindingDefinition, ProjectionDefinition,
    ProjectionFieldDefinition, PropertyDefinition, SourceDefinition, StructDefinition,
    TableDefinition, validate_blueprint,
)


def _symbol(kind: str, declaration: type[Any]) -> str:
    return f"python:{kind}:{declaration.__module__}:{declaration.__qualname__}"


def _annotations(values: Sequence[Annotation]) -> tuple[AnnotationDefinition, ...]:
    return tuple(
        AnnotationDefinition(namespace, annotation_id, freeze_json(arguments))
        for namespace, annotation_id, arguments in (value.serialise() for value in values)
    )


def _field(owner: type[Any], declaration: Any) -> FieldDefinition:
    metadata = declaration.metadata
    assert metadata.name is not None
    return FieldDefinition(
        metadata.name, declaration._logical_type(owner), metadata.description,
        _annotations(metadata.annotations),
    )


def _struct(declaration: type[Struct]) -> StructDefinition:
    declared: Any = declaration
    return StructDefinition(
        _symbol("struct", declaration), declared._data_name,
        tuple(_field(declaration, field) for field in declared._fields.values()),
        declared._data_metadata.get("description"),
        _annotations(declared._data_annotations),
    )


def _table(declaration: type[Table]) -> TableDefinition:
    declared: Any = declaration
    return TableDefinition(
        _symbol("table", declaration), declaration._table_name,
        tuple(_field(declaration, field) for field in declared._fields.values()),
        declared._data_metadata.get("description"),
        _annotations(declared._data_annotations),
    )


def _component(declaration: type[Any]) -> ComponentDefinition:
    properties = tuple(
        PropertyDefinition(
            prop.name or attribute, prop.logical_type, prop.description,
            _annotations(prop.annotations),
        )
        for attribute, prop in declaration._properties.items()
    )
    metadata = declaration._metadata
    return ComponentDefinition(
        _symbol(declaration._kind, declaration), declaration._component_name,
        declaration._kind, properties, metadata.get("description"),
        getattr(metadata.get("source"), "_component_name", None),
        getattr(metadata.get("target"), "_component_name", None),
        _annotations(declaration._component_annotations),
    )


def _projection(declaration: type[Projection]) -> ProjectionDefinition:
    fields = tuple(
        ProjectionFieldDefinition(
            field.metadata.name or attribute, field.expression,
            field.metadata.description, _annotations(field.metadata.annotations),
        )
        for attribute, field in declaration._projection_fields.items()
    )
    return ProjectionDefinition(
        _symbol("projection", declaration), declaration._projection_name, fields,
        declaration._data_metadata.get("description"),
        _annotations(declaration._data_annotations),
    )


def _property_expressions(binding: Binding) -> tuple[tuple[str, Any], ...]:
    result = []
    for attribute, declaration in binding.target._properties.items():
        value = getattr(binding.properties, attribute)
        if not isinstance(value, ValueExpression):
            raise TypeError(f"{binding.target.__name__}.{attribute} must be a value expression")
        result.append((declaration.name or attribute, value.expression))
    return tuple(sorted(result))


def _binding_symbol(binding: Binding) -> str:
    payload = {
        "kind": "edge" if isinstance(binding, EdgeBinding) else "node",
        "component": binding.target._component_name,
        "debug_name": binding.debug_name,
        "build_key": encode_expression(binding.build_key.expression),
        "properties": {name: encode_expression(value) for name, value in _property_expressions(binding)},
    }
    if isinstance(binding, EdgeBinding):
        payload.update(
            source_build_key=encode_expression(binding.source_build_key.expression),
            target_build_key=encode_expression(binding.target_build_key.expression),
        )
    fingerprint = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:24]
    return f"binding:{payload['kind']}:{binding.target._component_name}:{fingerprint}"


def _binding(binding: Binding) -> NodeBindingDefinition | EdgeBindingDefinition:
    common = (
        _binding_symbol(binding), binding.target._component_name,
        binding.build_key.expression,
    )
    rest = (_property_expressions(binding), binding.debug_name, _annotations(binding.annotations))
    if isinstance(binding, EdgeBinding):
        return EdgeBindingDefinition(
            *common, binding.source_build_key.expression,
            binding.target_build_key.expression, *rest,
        )
    return NodeBindingDefinition(*common, *rest)


def _source(source: BoundTable) -> SourceDefinition:
    table: Any = source.table
    return SourceDefinition(
        f"source:{source.table._table_name}", source.table._table_name,
        source.config.location, source.config.format.value,
        source.config.credentials, source.config.version,
        _annotations((*table._data_annotations, *source.annotations)),
    )


def _module(registration: ModuleRegistration[Any]) -> BlueprintModule:
    cls = registration.module_class
    module_id = getattr(cls, "ID", None)
    if not isinstance(module_id, str) or not module_id:
        raise TypeError("workflow module classes must declare a non-empty string ID")
    if "<locals>" in cls.__qualname__:
        raise ValueError("workflow modules must be importable top-level classes")
    return BlueprintModule(module_id, cls.__module__, cls.__qualname__, freeze_json(asdict(registration.configuration)))


def _all_subclasses(cls: type[Any]) -> tuple[type[Any], ...]:
    result: list[type[Any]] = []
    for child in cls.__subclasses__():
        result.append(child)
        result.extend(_all_subclasses(child))
    return tuple(result)


def _expression_sources(expressions: Iterable[Any]) -> set[str]:
    return {
        node.source
        for expression in expressions
        for node in walk_expression(expression)
        if isinstance(node, FieldReferenceExpression)
    }


def _binding_expressions(binding: Binding) -> tuple[Any, ...]:
    result = [binding.build_key.expression, *(value for _, value in _property_expressions(binding))]
    if isinstance(binding, EdgeBinding):
        result.extend((binding.source_build_key.expression, binding.target_build_key.expression))
    return tuple(result)


def _resolve_declarations(bindings: tuple[Binding, ...], sources: tuple[BoundTable, ...]):
    table_registry = {
        declaration._table_name: declaration
        for declaration in _all_subclasses(Table)
        if vars(declaration).get("_data_declaration_kind") == "table"
    }
    projection_registry = {
        declaration._projection_name: declaration
        for declaration in _all_subclasses(Projection)
        if vars(declaration).get("_data_declaration_kind") == "projection"
    }
    required = _expression_sources(expression for binding in bindings for expression in _binding_expressions(binding))
    projections: dict[str, type[Projection]] = {}
    while True:
        pending = sorted(required & projection_registry.keys() - projections.keys())
        if not pending:
            break
        for name in pending:
            declaration = projection_registry[name]
            projections[name] = declaration
            required.update(_expression_sources(field.expression for field in declaration._projection_fields.values()))
    tables = {source.table._table_name: source.table for source in sources}
    for name in required - projections.keys():
        if name in table_registry:
            tables[name] = table_registry[name]
    missing = required - tables.keys() - projections.keys()
    if missing:
        raise ValueError("expressions reference undiscoverable logical sources: " + ", ".join(sorted(missing)))

    structs: dict[tuple[str, str], type[Struct]] = {}
    def include_type(logical_type) -> None:
        base = logical_type.value if isinstance(logical_type, NullableType) else logical_type
        if isinstance(base, ArrayType):
            include_type(base.item)
        elif isinstance(base, StructType):
            module = importlib.import_module(base.module)
            declaration: Any = module
            for part in base.qualname.split("."):
                declaration = getattr(declaration, part)
            key = (base.module, base.qualname)
            if key not in structs:
                structs[key] = declaration
                for field in declaration._fields.values():
                    include_type(field._logical_type(declaration))
    for table in tables.values():
        declared: Any = table
        for field in declared._fields.values():
            include_type(field._logical_type(table))
    return tuple(tables.values()), tuple(projections.values()), tuple(structs.values())


def _namespace_modules(namespace_path: str | Path) -> tuple[ModuleType, ...]:
    path = Path(namespace_path)
    inserted: str | None = None
    if path.exists():
        root = path.resolve()
        if not root.is_dir():
            raise ValueError("namespace_path must identify a Python namespace directory")
        namespace, roots, inserted = root.name, (root,), str(root.parent)
        if inserted not in sys.path:
            sys.path.insert(0, inserted)
        else:
            inserted = None
    else:
        namespace = str(namespace_path)
        spec = importlib.util.find_spec(namespace)
        if spec is None or spec.submodule_search_locations is None:
            raise ModuleNotFoundError(f"no importable namespace found for {namespace!r}")
        roots = tuple(Path(item) for item in spec.submodule_search_locations)
    names = {namespace}
    for root in roots:
        names.update(f"{namespace}.{file.relative_to(root).with_suffix('').as_posix().replace('/', '.')}" for file in root.rglob("*.py") if file.name != "__init__.py")
        names.update(f"{namespace}.{folder.relative_to(root).as_posix().replace('/', '.')}" for folder in root.rglob("*") if folder.is_dir() and (folder / "__init__.py").exists())
    try:
        return tuple(importlib.import_module(name) for name in sorted(names))
    finally:
        if inserted is not None:
            sys.path.remove(inserted)


def _discover_namespace(namespace_path: str | Path) -> tuple[tuple[Binding, ...], tuple[BoundSource, ...]]:
    bindings: dict[int, Binding] = {}
    sources: dict[int, BoundSource] = {}
    for module in _namespace_modules(namespace_path):
        for value in vars(module).values():
            if isinstance(value, (NodeBinding, EdgeBinding)):
                bindings[id(value)] = value
            elif isinstance(value, BoundSource):
                sources[id(value)] = value
    return tuple(bindings.values()), tuple(sources.values())


def _deduplicate_identity[T](values: Iterable[T]) -> tuple[T, ...]:
    return tuple({id(value): value for value in values}.values())


@overload
def create_blueprint(*, bindings: Iterable[Binding], sources: Sequence[BoundSource] = (), modules: Sequence[ModuleRegistration[Any]] = ()) -> BuildBlueprint: ...
@overload
def create_blueprint(*, namespace_path: str | Path, bindings: Iterable[Binding] = (), sources: Sequence[BoundSource] = (), modules: Sequence[ModuleRegistration[Any]] = ()) -> BuildBlueprint: ...


def create_blueprint(
    *, bindings: Iterable[Binding] = (), sources: Sequence[BoundSource] = (),
    modules: Sequence[ModuleRegistration[Any]] = (), namespace_path: str | Path | None = None,
) -> BuildBlueprint:
    discovered_bindings: tuple[Binding, ...] = ()
    discovered_sources: tuple[BoundSource, ...] = ()
    if namespace_path is not None:
        discovered_bindings, discovered_sources = _discover_namespace(namespace_path)
    authoring_bindings = _deduplicate_identity((*discovered_bindings, *bindings))
    bound_tables = tuple(
        item for source in (*discovered_sources, *sources) for item in resolve_bound_source(source)
    )
    tables, projections, structs = _resolve_declarations(authoring_bindings, bound_tables)
    component_classes = {binding.target for binding in authoring_bindings}
    for component in tuple(component_classes):
        if component._kind == "edge":
            component_classes.update((component._metadata["source"], component._metadata["target"]))
    blueprint = BuildBlueprint(
        structs=tuple(sorted((_struct(item) for item in structs), key=lambda item: item.symbol_id)),
        tables=tuple(sorted((_table(item) for item in tables), key=lambda item: item.symbol_id)),
        components=tuple(sorted((_component(item) for item in component_classes), key=lambda item: item.symbol_id)),
        projections=tuple(sorted((_projection(item) for item in projections), key=lambda item: item.symbol_id)),
        bindings=tuple(sorted((_binding(item) for item in authoring_bindings), key=lambda item: item.symbol_id)),
        sources=tuple(sorted((_source(item) for item in bound_tables), key=lambda item: item.symbol_id)),
        modules=tuple(sorted((_module(item) for item in modules), key=lambda item: item.module_id)),
    )
    validate_blueprint(blueprint)
    return blueprint


def compile_blueprint(
    *, blueprint: BuildBlueprint, sources: Sequence[BoundSource] = (),
    settings: Any = None,
) -> Any:
    raise NotImplementedError(
        "version-2 blueprint lowering is implemented by work package 10"
    )


__all__ = ["compile_blueprint", "create_blueprint"]
