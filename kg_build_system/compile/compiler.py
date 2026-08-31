"""Compile Python declarations into immutable workflow contracts."""
from __future__ import annotations

import asyncio
import importlib
import importlib.util
import json
import sys
from collections.abc import Iterable, Sequence
from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path
from types import ModuleType
from typing import Any, cast, overload

from ..annotations import Annotation
from ..annotations.ir import AnnotationIR as AnnotationDefinition
from ..binding import Binding, EdgeBinding, NodeBinding
from ..binding.ir import (
    EdgeBindingIR as EdgeBindingDefinition,
    NodeBindingIR as NodeBindingDefinition,
)
from .._frozen_json import freeze_json
from ..expressions import FieldReferenceExpression, ValueExpression, walk_expression
from ..expressions.codec import encode_expression
from ..expressions.mapping import expression_to_ir
from ..table import BoundSource, BoundTable, Projection, Struct, Table
from ..table.declarations import resolve_bound_source
from ..table.ir import (
    FieldIR as FieldDefinition,
    ProjectionIR as ProjectionDefinition,
    ProjectionFieldIR as ProjectionFieldDefinition,
    SourceIR as SourceDefinition,
    StructIR as StructDefinition,
    TableIR as TableDefinition,
)
from ..topology.ir import (
    ComponentIR as ComponentDefinition,
    PropertyIR as PropertyDefinition,
)
from ..types import ArrayType, NullableType, StructType
from ..types.mapping import type_to_ir
from ..workflow.ir import BlueprintModuleIR as BlueprintModule
from ..workflow.assembly import assemble_workflow
from ..workflow.contracts import create_workflow_contract
from ..workflow.ir import WorkflowContractIR
from .interfaces import (
    CompilableModule, CompilationContext, CompileModuleRegistration,
)
from .models import BuildBlueprint
from .validation import validate_blueprint


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
        metadata.name, type_to_ir(declaration._logical_type(owner)), metadata.description,
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
            prop.name or attribute, type_to_ir(prop.logical_type), prop.description,
            _annotations(prop.annotations),
        )
        for attribute, prop in declaration._properties.items()
    )
    metadata = declaration._metadata
    parent = declaration._component_parent_class
    return ComponentDefinition(
        _symbol(declaration._kind, declaration), declaration._component_name,
        declaration._kind, properties, metadata.get("description"),
        getattr(metadata.get("source"), "_component_name", None),
        getattr(metadata.get("target"), "_component_name", None),
        _annotations(declaration._component_annotations),
        bool(declaration._component_abstract),
        None if parent is None else _symbol(parent._kind, parent),
    )


def _projection(declaration: type[Projection]) -> ProjectionDefinition:
    fields = tuple(
        ProjectionFieldDefinition(
            field.metadata.name or attribute, expression_to_ir(field.expression.model),
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
        result.append((declaration.name or attribute, value.model))
    return tuple(sorted(result))


def _binding_symbol(binding: Binding) -> str:
    payload = {
        "kind": "edge" if isinstance(binding, EdgeBinding) else "node",
        "component": binding.target._component_name,
        "debug_name": binding.debug_name,
        "build_key": encode_expression(binding.build_key.model),
        "properties": {name: encode_expression(value) for name, value in _property_expressions(binding)},
    }
    if isinstance(binding, EdgeBinding):
        payload.update(
            source_build_key=encode_expression(binding.source_build_key.model),
            target_build_key=encode_expression(binding.target_build_key.model),
            source_node=None if binding.source_node is None else binding.source_node._component_name,
            target_node=None if binding.target_node is None else binding.target_node._component_name,
        )
    fingerprint = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:24]
    return f"binding:{payload['kind']}:{binding.target._component_name}:{fingerprint}"


def _binding(binding: Binding) -> NodeBindingDefinition | EdgeBindingDefinition:
    common = (
        _binding_symbol(binding), binding.target._component_name,
        expression_to_ir(binding.build_key.model),
    )
    properties = tuple(
        (name, expression_to_ir(expression))
        for name, expression in _property_expressions(binding)
    )
    rest = (properties, binding.debug_name, _annotations(binding.annotations))
    if isinstance(binding, EdgeBinding):
        return EdgeBindingDefinition(
            *common, expression_to_ir(binding.source_build_key.model),
            expression_to_ir(binding.target_build_key.model), *rest,
            source_node=(
                None if binding.source_node is None
                else binding.source_node._component_name
            ),
            target_node=(
                None if binding.target_node is None
                else binding.target_node._component_name
            ),
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


def _module(registration: CompileModuleRegistration[Any]) -> BlueprintModule:
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
    result = [binding.build_key.model, *(value for _, value in _property_expressions(binding))]
    if isinstance(binding, EdgeBinding):
        result.extend((binding.source_build_key.model, binding.target_build_key.model))
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
            required.update(_expression_sources(field.expression.model for field in declaration._projection_fields.values()))
    source_tables = {source.table._table_name: source.table for source in sources}
    tables: dict[str, type[Table]] = {}
    for name in required - projections.keys():
        if name in source_tables:
            tables[name] = source_tables[name]
        elif name in table_registry:
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
        for file in root.rglob("*.py"):
            relative = file.relative_to(root).with_suffix("")
            if file.name != "__init__.py" and all(
                part.isidentifier() for part in relative.parts
            ):
                names.add(f"{namespace}.{'.'.join(relative.parts)}")
        for folder in root.rglob("*"):
            relative = folder.relative_to(root)
            if (
                folder.is_dir()
                and (folder / "__init__.py").exists()
                and all(part.isidentifier() for part in relative.parts)
            ):
                names.add(f"{namespace}.{'.'.join(relative.parts)}")
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
def create_blueprint(*, bindings: Iterable[Binding], sources: Sequence[BoundSource] = (), modules: Sequence[CompileModuleRegistration[Any]] = ()) -> BuildBlueprint: ...
@overload
def create_blueprint(*, namespace_path: str | Path, bindings: Iterable[Binding] = (), sources: Sequence[BoundSource] = (), modules: Sequence[CompileModuleRegistration[Any]] = ()) -> BuildBlueprint: ...


def create_blueprint(
    *, bindings: Iterable[Binding] = (), sources: Sequence[BoundSource] = (),
    modules: Sequence[CompileModuleRegistration[Any]] = (), namespace_path: str | Path | None = None,
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
    required_tables = {table._table_name for table in tables}
    bound_tables = tuple(
        source for source in bound_tables
        if source.table._table_name in required_tables
    )
    component_classes: set[type[Any]] = set()
    component_queue: list[type[Any]] = [binding.target for binding in authoring_bindings]
    for binding in authoring_bindings:
        if isinstance(binding, EdgeBinding):
            component_queue.extend(
                item for item in (binding.source_node, binding.target_node)
                if item is not None
            )
    while component_queue:
        component = component_queue.pop()
        if component in component_classes:
            continue
        component_classes.add(component)
        parent = getattr(component, "_component_parent_class", None)
        if parent is not None:
            component_queue.append(parent)
        if component._kind == "edge":
            component_queue.extend(
                (component._metadata["source"], component._metadata["target"])
            )
    blueprint = BuildBlueprint(
        structs=tuple(sorted((_struct(item) for item in structs), key=lambda item: item.symbol_id)),
        tables=tuple(sorted((_table(item) for item in tables), key=lambda item: item.symbol_id)),
        components=tuple(sorted((_component(item) for item in component_classes), key=lambda item: item.symbol_id)),
        projections=tuple(sorted((_projection(item) for item in projections), key=lambda item: item.symbol_id)),
        bindings=tuple(sorted((_binding(item) for item in authoring_bindings), key=lambda item: item.symbol_id)),
        sources=tuple(sorted((_source(item) for item in bound_tables), key=lambda item: item.symbol_id)),
        modules=tuple(_module(item) for item in modules),
    )
    validate_blueprint(blueprint)
    return blueprint


def configure_blueprint_modules(
    blueprint: BuildBlueprint,
    modules: Sequence[CompileModuleRegistration[Any]],
) -> BuildBlueprint:
    """Replace a blueprint's module composition and validate the result."""
    configured = replace(
        blueprint,
        modules=tuple(_module(registration) for registration in modules),
    )
    validate_blueprint(configured)
    return configured


def _fingerprint(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode()
    return sha256(encoded).hexdigest()


def _blueprint_fingerprint(blueprint: BuildBlueprint) -> str:
    from .codec import encode_blueprint

    payload = encode_blueprint(blueprint)
    for binding in payload["bindings"]:
        binding.pop("debug_name", None)
    return _fingerprint(payload)


def _thaw(value: Any) -> Any:
    from ..expressions.models import FrozenObject
    if isinstance(value, FrozenObject):
        return {key: _thaw(item) for key, item in value.items}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _load_module(
    definition: BlueprintModule,
) -> tuple[type[CompilableModule], Any]:
    module_class: Any = importlib.import_module(definition.module_import)
    for part in definition.module_qualname.split("."):
        module_class = getattr(module_class, part)
    configuration_type = getattr(module_class, "CONFIGURATION_TYPE", None)
    configuration = _thaw(definition.configuration)
    if not isinstance(configuration_type, type) or not isinstance(configuration, dict):
        raise TypeError(
            f"workflow module {definition.module_id!r} cannot reconstruct its registration configuration"
        )
    if getattr(module_class, "ID", None) != definition.module_id:
        raise RuntimeError(
            f"blueprint module {definition.module_id!r} resolved to "
            f"{getattr(module_class, 'ID', None)!r}"
        )
    return cast(type[CompilableModule], module_class), configuration_type(**configuration)


async def _compile_workflow(
    *, blueprint: BuildBlueprint,
) -> WorkflowContractIR:
    validate_blueprint(blueprint)
    referenced_tables = {table.name for table in blueprint.tables}
    missing = referenced_tables - {source.table for source in blueprint.sources}
    if missing:
        raise ValueError("no source bound for: " + ", ".join(sorted(missing)))
    contributions = []
    for definition in blueprint.modules:
        module_class, configuration = _load_module(definition)
        context = CompilationContext(blueprint, definition.module_id, configuration)
        compiler = await module_class.create_compiler(context)
        contribution = await compiler.compile(context)
        if contribution.module.reference.module_id != definition.module_id:
            raise ValueError("module class ID does not match its compilation result")
        reference = replace(
            contribution.module.reference,
            import_module=module_class.__module__,
            class_qualname=module_class.__qualname__,
            implementation_version=str(module_class.VERSION),
        )
        contributions.append(type(contribution)(
            replace(contribution.module, reference=reference), contribution.steps,
        ))
    workflow = assemble_workflow(contributions)
    from .codec import encode_blueprint

    provenance = {
        "compile": {
            "blueprint": encode_blueprint(blueprint),
            "blueprint_fingerprint": _blueprint_fingerprint(blueprint),
        }
    }
    return create_workflow_contract(
        workflow,
        provenance=cast(Any, provenance),
    )


def compile_workflow(
    *, blueprint: BuildBlueprint,
) -> WorkflowContractIR:
    """Compile a blueprint into one frozen executable workflow contract."""
    return asyncio.run(_compile_workflow(blueprint=blueprint))


__all__ = ["compile_workflow", "create_blueprint"]
