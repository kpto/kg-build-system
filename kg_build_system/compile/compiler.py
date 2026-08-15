"""Compile Python declarations into immutable blueprints and build contracts."""
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
from typing import Any, get_type_hints, overload

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
from ..workflow.interfaces import ModuleRegistration
from .blueprint import BuildBlueprint
from .validation import validate_blueprint
from ..workflow.mapping import workflow_to_ir
from ..workflow.models import (
    ArtifactRole, Connection, OutputSlot, SingleInputSlot, WorkflowDefinition,
)
from ..workflow.validation import validate_workflow
from .contracts import BuildContract, BuildOverrides, BuildSettings, SourceOverride
from ..modules.core.core import CoreModule
from ..workflow.interfaces import (
    CompilationContext, ModuleRegistrationConfiguration, WorkflowStepDraft,
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
            field.metadata.name or attribute, expression_to_ir(field.expression),
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
        expression_to_ir(binding.build_key.expression),
    )
    properties = tuple(
        (name, expression_to_ir(expression))
        for name, expression in _property_expressions(binding)
    )
    rest = (properties, binding.debug_name, _annotations(binding.annotations))
    if isinstance(binding, EdgeBinding):
        return EdgeBindingDefinition(
            *common, expression_to_ir(binding.source_build_key.expression),
            expression_to_ir(binding.target_build_key.expression), *rest,
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
        modules=tuple(_module(item) for item in modules),
    )
    validate_blueprint(blueprint)
    return blueprint


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


def _effective_sources(
    blueprint: BuildBlueprint, overrides: Sequence[BoundSource],
) -> tuple[SourceDefinition, ...]:
    result = {source.table: source for source in blueprint.sources}
    for bound in (item for source in overrides for item in resolve_bound_source(source)):
        replacement = _source(bound)
        result[replacement.table] = replacement
    return tuple(result[name] for name in sorted(result))


def _thaw(value: Any) -> Any:
    from ..expressions.models import FrozenObject
    if isinstance(value, FrozenObject):
        return {key: _thaw(item) for key, item in value.items}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _load_registration(definition: BlueprintModule) -> ModuleRegistration[Any]:
    module_class: Any = importlib.import_module(definition.module_import)
    for part in definition.module_qualname.split("."):
        module_class = getattr(module_class, part)
    configuration_type = get_type_hints(module_class).get("configuration")
    configuration = _thaw(definition.configuration)
    if configuration_type is None or not isinstance(configuration, dict):
        raise TypeError(
            f"workflow module {definition.module_id!r} cannot reconstruct its registration configuration"
        )
    registration = module_class(configuration_type(**configuration))
    if registration.module_class.ID != definition.module_id:
        raise RuntimeError(
            f"blueprint module {definition.module_id!r} resolved to {registration.module_class.ID!r}"
        )
    return registration


async def _compile_blueprint(
    *, blueprint: BuildBlueprint, sources: Sequence[BoundSource] = (),
    settings: BuildSettings | None = None,
) -> BuildContract:
    validate_blueprint(blueprint)
    effective_sources = _effective_sources(blueprint, sources)
    referenced_tables = {table.name for table in blueprint.tables}
    missing = referenced_tables - {source.table for source in effective_sources}
    if missing:
        raise ValueError("no source bound for: " + ", ".join(sorted(missing)))
    override_sources = tuple(
        _source(item) for source in sources for item in resolve_bound_source(source)
    )
    overrides = BuildOverrides(sources=tuple(
        SourceOverride(
            table=item.table,
            original=next((source for source in blueprint.sources if source.table == item.table), None),
            override=item,
        )
        for item in override_sources
    ))
    compilation_settings = settings or BuildSettings()
    declarations = []
    core_context = CompilationContext(
        blueprint, compilation_settings, overrides, CoreModule.ID, 0,
        ModuleRegistrationConfiguration(),
    )
    core_compiler = await CoreModule.create_compiler(core_context)
    declarations.append(await core_compiler.compile(core_context))
    for priority, definition in enumerate(blueprint.modules, start=1):
        registration = _load_registration(definition)
        context = CompilationContext(
            blueprint, compilation_settings, overrides, definition.module_id,
            priority, registration.configuration,
        )
        compiler = await registration.module_class.create_compiler(context)
        declaration = await compiler.compile(context)
        if declaration.module.reference.module_id != definition.module_id:
            raise ValueError("module class ID does not match its compilation result")
        cls = registration.module_class
        reference = replace(
            declaration.module.reference,
            import_module=cls.__module__,
            class_qualname=cls.__qualname__,
            implementation_version=str(getattr(cls, "VERSION", declaration.module.reference.implementation_version)),
            priority=priority,
        )
        declarations.append(type(declaration)(
            replace(declaration.module, reference=reference), declaration.steps,
        ))

    drafts = [draft for declaration in declarations for draft in declaration.steps]
    modules = tuple(declaration.module for declaration in declarations)
    if len({module.reference.module_id for module in modules}) != len(modules):
        raise ValueError("workflow module IDs must be unique")
    priorities = {module.reference.module_id: module.reference.priority for module in modules}
    declaration_order = {draft.definition.step_id: index for index, draft in enumerate(drafts)}
    output_step = {
        slot.slot_id: draft.definition.step_id
        for draft in drafts for slot in draft.definition.outputs
    }
    outputs = [slot for draft in drafts for slot in draft.definition.outputs]
    output_order = {slot.slot_id: index for index, slot in enumerate(outputs)}
    output_module = {
        slot.slot_id: draft.definition.module_id
        for draft in drafts for slot in draft.definition.outputs
    }
    dependencies: dict[str, set[str]] = {
        draft.definition.step_id: set() for draft in drafts
    }

    def creates_cycle(producer: str, consumer: str) -> bool:
        if producer == consumer:
            return True
        pending = [consumer]
        visited: set[str] = set()
        while pending:
            step_id = pending.pop()
            if step_id == producer:
                return True
            if step_id in visited:
                continue
            visited.add(step_id)
            pending.extend(dependencies[step_id])
        return False

    def candidate_order(output: OutputSlot) -> tuple[int, int, str]:
        return (
            priorities[output_module[output.slot_id]],
            output_order[output.slot_id],
            output.slot_id,
        )

    claims = sorted(
        drafts,
        key=lambda draft: (
            0 if draft.definition.assembly_preference == "eager" else 1,
            -priorities[draft.definition.module_id]
            if draft.definition.assembly_preference == "eager"
            else priorities[draft.definition.module_id],
            declaration_order[draft.definition.step_id],
        ),
    )
    connections: list[Connection] = []
    uses: dict[str, int] = {}
    for draft in claims:
        for input_slot in draft.definition.inputs:
            predicate = draft.candidates.get(input_slot.slot_id)
            candidates = [
                output for output in outputs
                if output_step[output.slot_id] != draft.definition.step_id
                and predicate is not None and predicate(input_slot, output)
            ]
            candidates = [
                output for output in candidates
                if not creates_cycle(
                    output_step[output.slot_id], draft.definition.step_id,
                )
            ]
            if isinstance(input_slot, SingleInputSlot):
                if not candidates:
                    raise ValueError(f"input {input_slot.slot_id} has no compatible output")
                open_candidates = [
                    output for output in candidates
                    if uses.get(output.slot_id, 0) == 0
                ]
                selected = max(open_candidates or candidates, key=candidate_order)
                connections.append(Connection(input_slot_id=input_slot.slot_id, output_slot_id=selected.slot_id))
                uses[selected.slot_id] = uses.get(selected.slot_id, 0) + 1
                dependencies[output_step[selected.slot_id]].add(
                    draft.definition.step_id,
                )
            else:
                by_role: dict[tuple[str, str], list[OutputSlot]] = {}
                for output in candidates:
                    role = output.artifact_role
                    by_role.setdefault((role.namespace, role.name), []).append(output)
                selected_outputs: list[OutputSlot] = []
                for role_candidates in by_role.values():
                    open_candidates = [
                        output for output in role_candidates
                        if uses.get(output.slot_id, 0) == 0
                    ]
                    selected_outputs.extend(
                        open_candidates or (max(role_candidates, key=candidate_order),)
                    )
                if not selected_outputs:
                    raise ValueError(f"input {input_slot.slot_id} has no compatible output")
                for output in sorted(selected_outputs, key=candidate_order):
                    connections.append(Connection(input_slot_id=input_slot.slot_id, output_slot_id=output.slot_id))
                    uses[output.slot_id] = uses.get(output.slot_id, 0) + 1
                    dependencies[output_step[output.slot_id]].add(
                        draft.definition.step_id,
                    )
    workflow = WorkflowDefinition(
        modules=modules,
        steps=tuple(draft.definition for draft in drafts),
        connections=tuple(connections),
    )
    validate_workflow(workflow)
    workflow_ir = workflow_to_ir(workflow)
    return BuildContract(
        blueprint=blueprint,
        blueprint_fingerprint=_blueprint_fingerprint(blueprint),
        settings=compilation_settings,
        workflow_fingerprint=_fingerprint(workflow_ir.model_dump(mode="json")),
        workflow=workflow_ir,
    )


def compile_blueprint(
    *, blueprint: BuildBlueprint, sources: Sequence[BoundSource] = (),
    settings: BuildSettings | None = None,
) -> BuildContract:
    """Compile a blueprint into one frozen executable workflow contract."""
    return asyncio.run(_compile_blueprint(
        blueprint=blueprint, sources=sources, settings=settings,
    ))


__all__ = ["compile_blueprint", "create_blueprint"]
