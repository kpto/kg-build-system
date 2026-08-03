"""Lower authoring declarations into canonical Pydantic IR."""
# pyright: reportPrivateImportUsage=false
from __future__ import annotations
from collections.abc import Iterable, Sequence
import asyncio
import importlib
from dataclasses import asdict
from hashlib import sha256
import json
from typing import Any, Literal, cast, get_type_hints
from ..binding import EdgeBinding, ExpressionBinding, NodeBinding
from ..data import BoundTable
from .models import (
    BindingDefinition, BlueprintModule, BuildBlueprint, BuildContract, BuildSettings,
    BuildOverrides, ComponentDefinition, Connection, EdgeBindingDefinition, FieldReference, LiteralValue,
    NodeBindingDefinition, Operation,
    ProjectionDefinition, PropertyDefinition, SingleInputSlot, SourceDefinition,
    SourceOverride, Value, ValueType, WorkflowDefinition,
)
from ..expressions import Expression, FieldPath
from .._support.annotations import type_name, type_shape
from ..workflow.interfaces import ModuleRegistration, WorkflowStepDraft
from ..modules.core import CoreCompilationContext, CoreModule

def _property_expressions(binding: NodeBinding | EdgeBinding) -> dict[str, Expression[Any]]:
    values: dict[str, Expression[Any]] = {}
    for name in binding.target._properties:
        slot = getattr(binding.properties, name)
        if not isinstance(slot, ExpressionBinding) or slot.expression is None:
            raise TypeError(f"{binding.target.__name__}.{name} must be assigned with bind(...)")
        values[name] = slot.expression
    return values

def _value_type(annotation: Any, cardinality: str = "scalar") -> ValueType:
    shape = type_shape(annotation, cardinality)
    if annotation is Any or annotation is None: return ValueType(kind="unknown", name="unknown", nullable=shape.nullable)
    if shape.cardinality == "collection": return ValueType(kind="collection", name="list", item=type_name(shape.item_annotation), nullable=shape.nullable, item_nullable=shape.item_nullable)
    return ValueType(kind="scalar", name=type_name(shape.annotation), nullable=shape.nullable)

def _to_ir(value: Expression[Any] | FieldPath[Any] | Any) -> Value:
    if isinstance(value, FieldPath): return FieldReference(table=value.table.__name__, path=value.path, value_type=_value_type(value.type_hint, value.cardinality), collection_paths=value.collection_paths)
    if isinstance(value, Expression):
        if value.op == "field": return _to_ir(value.args[0])
        if value.op == "literal": return _to_ir(value.args[0])
        operation = cast(Literal["concat", "coalesce", "cast", "deterministic_uuid", "expand", "struct_field", "lookup_one"], {"uuid": "deterministic_uuid"}.get(value.op, value.op))
        skip_string = (value.op == "cast" or value.op == "struct_field")
        args = tuple(_to_ir(arg) for arg in value.args if not (skip_string and isinstance(arg, str)))
        return Operation(op=operation, args=args, value_type=_value_type(value.type_hint, value.cardinality), sql_type=value.args[1] if value.op == "cast" else None, field_name=value.args[1] if value.op == "struct_field" else None)
    return LiteralValue(value=value, value_type=_value_type(type(value)))

def _component(component: type) -> ComponentDefinition:
    metadata = component._metadata; properties = tuple(PropertyDefinition(name=prop.name or attr, value_type=_value_type(prop.type_hint), nullable=prop.nullable) for attr, prop in component._properties.items())
    return ComponentDefinition(name=component.__name__, kind=component._kind, properties=properties, source=getattr(metadata.get("source"), "__name__", None), target=getattr(metadata.get("target"), "__name__", None))

def _binding(binding: NodeBinding | EdgeBinding, *, symbol_id: str) -> BindingDefinition:
    properties = {name: _to_ir(value) for name, value in _property_expressions(binding).items()}
    if isinstance(binding, EdgeBinding):
        return EdgeBindingDefinition(symbol_id=symbol_id, debug_name=binding.debug_name, component=binding.target.__name__, build_key=_to_ir(binding.build_key), source_build_key=_to_ir(binding.source_build_key), target_build_key=_to_ir(binding.target_build_key), properties=properties)
    return NodeBindingDefinition(symbol_id=symbol_id, debug_name=binding.debug_name, component=binding.target.__name__, build_key=_to_ir(binding.build_key), properties=properties)

def _validate_authoring_binding(binding: NodeBinding | EdgeBinding) -> None:
    """Checks requiring declaration metadata, before it is discarded into IR."""
    for name, value in _property_expressions(binding).items():
        if getattr(value, "cardinality", "scalar") == "collection":
            raise TypeError(f"{binding.target.__name__}.{name} maps a collection; use collection.expand(...) explicitly")
        property_declaration = binding.target._properties[name]
        expected = _value_type(property_declaration.type_hint)
        actual = _value_type(getattr(value, "type_hint", Any), getattr(value, "cardinality", "scalar"))
        if expected.kind == "scalar" and actual.kind == "scalar" and expected.name != "unknown" and actual.name != "unknown" and expected.name != actual.name:
            raise TypeError(f"{binding.target.__name__}.{name} expects {expected.name}, but expression resolves to {actual.name}")
        if not property_declaration.nullable and actual.nullable:
            raise TypeError(f"{binding.target.__name__}.{name} is required but expression may be null")
    if getattr(binding.build_key, "cardinality", "scalar") == "collection":
        raise TypeError(f"{binding.target.__name__} build key maps a collection; use collection.expand(...) explicitly")
    key_type = _value_type(getattr(binding.build_key, "type_hint", Any), getattr(binding.build_key, "cardinality", "scalar"))
    if key_type.name not in {"str", "unknown"}: raise TypeError(f"{binding.target.__name__} build key must resolve to str, not {key_type.name}")
    if key_type.nullable: raise TypeError(f"{binding.target.__name__} build key may not be nullable")

def _source_definition(source: BoundTable) -> SourceDefinition:
    return SourceDefinition(table=source.table.__name__, location=source.config.location, format=source.config.format.value, credential_reference=source.config.credentials, version=source.config.version)

def _blueprint_module(registration: ModuleRegistration[Any]) -> BlueprintModule:
    module_class = registration.module_class
    module_id = getattr(module_class, "ID", None)
    if not isinstance(module_id, str):
        raise TypeError("workflow module classes must declare a string ID")
    if "<locals>" in module_class.__qualname__:
        raise ValueError("workflow modules must be importable top-level classes")
    return BlueprintModule(
        module_id=module_id,
        module_import=module_class.__module__,
        module_qualname=module_class.__qualname__,
        configuration=asdict(registration.configuration),
    )


def create_blueprint(*, bindings: Iterable[NodeBinding | EdgeBinding], projections: Sequence[type[Any]] = (), sources: Sequence[BoundTable] = (), modules: Sequence[ModuleRegistration[Any]]) -> BuildBlueprint:
    authoring_bindings = tuple(bindings)
    if not authoring_bindings: raise ValueError("a graph requires at least one binding")
    for binding in authoring_bindings: _validate_authoring_binding(binding)
    components = tuple(sorted({_binding.target for _binding in authoring_bindings}, key=lambda item: item.__name__))
    projection_ir = tuple(ProjectionDefinition(name=projection.__name__, fields={name: _to_ir(field.expression) for name, field in projection._projection_fields.items()}) for projection in projections)
    binding_definitions: list[BindingDefinition] = []
    occurrences: dict[str, int] = {}
    for binding in authoring_bindings:
        provisional = _binding(binding, symbol_id="binding")
        digest = sha256(provisional.model_dump_json(exclude={"symbol_id", "debug_name"}).encode()).hexdigest()[:16]
        occurrences[digest] = occurrences.get(digest, 0) + 1
        suffix = "" if occurrences[digest] == 1 else f":{occurrences[digest]}"
        binding_definitions.append(_binding(binding, symbol_id=f"binding:{digest}{suffix}"))
    module_definitions = tuple(_blueprint_module(module) for module in modules)
    if len({module.module_id for module in module_definitions}) != len(module_definitions):
        raise ValueError("blueprint module IDs must be unique")
    return BuildBlueprint(components=tuple(_component(component) for component in components), projections=projection_ir, bindings=tuple(binding_definitions), sources=tuple(_source_definition(source) for source in sources), modules=module_definitions)

def _compile_binding_sql(*, graph: BuildBlueprint, sources: tuple[SourceDefinition, ...], binding: BindingDefinition) -> str:
    """Lower exactly one binding, without leaking other bindings' semantics."""
    projections = {projection.name: projection for projection in graph.projections}
    binding_values = _binding_values(binding)
    used_projections = [
        projection for projection in graph.projections
        if any(reference.table == projection.name for value in binding_values for reference in _field_references(value))
    ]
    if len(used_projections) > 1:
        raise ValueError("a binding may reference fields from only one projection")
    # A projection's expressions establish the row context used by every one
    # of its fields, including expansions not present in the consuming binding.
    values = binding_values + [value for projection in used_projections for value in projection.fields.values()]
    required = set().union(*(_tables(value, projections) for value in values))
    available = {source.table: source for source in sources}
    missing = required - set(available)
    if missing: raise ValueError("no source bound for: " + ", ".join(sorted(missing)))
    aliases = {table: f"t{index}" for index, table in enumerate(sorted(required))}
    def scan(table: str) -> exp.Table:
        source = available[table]
        function = {"csv": "read_csv_auto", "json": "read_json_auto", "parquet": "read_parquet"}[source.format]
        return exp.Table(
            this=exp.Anonymous(this=function, expressions=[exp.Literal.string(source.location)]),
            alias=exp.TableAlias(this=_identifier(aliases[table], quoted=False)),
        )
    lookups = [lookup for value in values for lookup in _operations(value, "lookup_one")]
    lookup_tables = {lookup.args[1].table for lookup in lookups if isinstance(lookup.args[1], FieldReference)}
    base_tables = sorted(required - lookup_tables)
    if not base_tables: raise ValueError("a lookup requires a non-lookup source table")
    query = exp.select("*").from_(scan(base_tables[0]))
    for table in base_tables[1:]: query = query.join(scan(table), join_type="CROSS")
    for lookup in lookups:
        match = lookup.args[1]
        if not isinstance(match, FieldReference): raise ValueError("lookup match must be a field reference")
        query = query.join(scan(match.table), on=exp.EQ(this=_render(match, aliases, projections), expression=_render(lookup.args[0], aliases, projections)), join_type="LEFT")
    expands = list({expand.model_dump_json(): expand for value in values for expand in _operations(value, "expand")}.values())
    direct = [expand for expand in expands if isinstance(expand.args[0], FieldReference) and expand.args[0].collection_paths]
    steps, expand_aliases = _direct_expand_plan(direct, aliases)
    for alias, expression in steps:
        unnest = exp.Unnest(expressions=[expression], alias=exp.TableAlias(this=_identifier(alias, quoted=False), columns=[_identifier("item", quoted=False)]))
        query = query.join(unnest, join_type="CROSS")
    remaining = [expand for expand in expands if expand not in direct]
    offset = len(steps)
    for index, expand in enumerate(remaining, start=offset):
        alias = f"expanded{index}"
        expand_aliases[expand.model_dump_json()] = exp.Dot(this=_identifier(alias, quoted=False), expression=_identifier("item"))
        unnest = exp.Unnest(expressions=[_render(expand.args[0], aliases, projections, expand_aliases)], alias=exp.TableAlias(this=_identifier(alias, quoted=False), columns=[_identifier("item", quoted=False)]))
        query = query.join(unnest, join_type="CROSS")
    direct_fields = {
        # Retain a direct nested field's top-level struct in a projection CTE.
        # The executor evaluates the binding's original FieldReference path
        # against that CTE, so flattening it to only its leaf would make paths
        # such as Study.details.name invalid at execution time.
        (field.table, (field.path[0],)): field.model_copy(update={"path": (field.path[0],)})
        for value in binding_values
        for field in _field_references(value)
        if field.table not in projections
    }
    final_query: exp.Expression = query
    for projection in used_projections:
        select_parts = [exp.alias_(_render(value, aliases, projections, expand_aliases), name, quoted=True) for name, value in projection.fields.items()]
        projection_names = set(projection.fields)
        for field in direct_fields.values():
            name = field.path[-1]
            if name not in projection_names: select_parts.append(exp.alias_(_render(field, aliases, projections, expand_aliases), name, quoted=True))
        projection_query = query.copy().select(*select_parts, append=False)
        final_query = exp.select("*").from_(exp.Table(this=_identifier(projection.name.lower(), quoted=False), alias=exp.TableAlias(this=_identifier("p0", quoted=False)))).with_(projection.name.lower(), as_=projection_query)
    output_columns = [exp.alias_(_render_plan_value(binding.build_key), "build_key", quoted=True)]
    if isinstance(binding, EdgeBindingDefinition):
        output_columns.extend((
            exp.alias_(_render_plan_value(binding.source_build_key), "source_build_key", quoted=True),
            exp.alias_(_render_plan_value(binding.target_build_key), "target_build_key", quoted=True),
        ))
    output_columns.extend(exp.alias_(_render_plan_value(value), name, quoted=True) for name, value in binding.properties.items())
    return exp.select(*output_columns).from_(exp.Subquery(this=final_query, alias=exp.TableAlias(this=_identifier("plan", quoted=False)))).sql(dialect="duckdb")

def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'

def _fingerprint(value: object) -> str:
    def normalise(item: object) -> object:
        if hasattr(item, "model_dump"):
            return normalise(item.model_dump(mode="json"))  # type: ignore[union-attr]
        if isinstance(item, dict):
            return {str(key): normalise(entry) for key, entry in item.items()}
        if isinstance(item, tuple | list):
            return [normalise(entry) for entry in item]
        return item
    return sha256(json.dumps(normalise(value), sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def _blueprint_fingerprint(blueprint: BuildBlueprint) -> str:
    """Fingerprint graph semantics, deliberately excluding debug-only metadata."""
    payload = blueprint.model_dump(mode="json")
    for binding in payload["bindings"]:
        binding.pop("debug_name", None)
    return _fingerprint(payload)

def _effective_sources(*, blueprint: BuildBlueprint, overrides: Sequence[BoundTable]) -> tuple[SourceDefinition, ...]:
    sources = {source.table: source for source in blueprint.sources}
    for bound_source in overrides:
        source = _source_definition(bound_source)
        sources[source.table] = source
    return tuple(sources[name] for name in sorted(sources))

def _load_registration(definition: BlueprintModule) -> ModuleRegistration[Any]:
    module_class: Any = importlib.import_module(definition.module_import)
    for part in definition.module_qualname.split("."):
        module_class = getattr(module_class, part)
    configuration_type = get_type_hints(module_class).get("configuration")
    if configuration_type is None or not isinstance(definition.configuration, dict):
        raise TypeError(f"workflow module {definition.module_id!r} cannot reconstruct its registration configuration")
    registration = module_class(configuration_type(**definition.configuration))
    module_id = getattr(registration.module_class, "ID", None)
    if module_id != definition.module_id:
        raise RuntimeError(f"blueprint module {definition.module_id!r} resolved to {module_id!r}")
    return registration


async def _compile_blueprint(*, blueprint: BuildBlueprint, sources: Sequence[BoundTable] = (), settings: BuildSettings | None = None) -> BuildContract:
    """Compile core DuckDB work and contributor declarations into one workflow."""
    source_ir = _effective_sources(blueprint=blueprint, overrides=sources)
    overrides = BuildOverrides(sources=tuple(SourceOverride(table=item.table, original=next((old for old in blueprint.sources if old.table == item.table), None), override=item) for item in (_source_definition(source) for source in sources)))
    core_compiler = await CoreModule.create_compiler(None)
    core_declaration = await core_compiler.compile(CoreCompilationContext(
        blueprint=blueprint,
        sources=source_ir,
    ))
    declarations = [core_declaration]
    drafts: list[WorkflowStepDraft] = []
    for priority, registration in enumerate((_load_registration(module) for module in blueprint.modules), start=1):
        compiler = await registration.module_class.create_compiler(type("CompilationContext", (), {"registration": registration})())
        declaration = await compiler.compile(blueprint)
        module_class = registration.module_class
        module_id = getattr(module_class, "ID", None)
        if module_id != declaration.module.reference.module_id:
            raise ValueError("module class ID does not match its compilation result")
        if "<locals>" in module_class.__qualname__:
            raise ValueError("workflow module classes must be importable top-level classes")
        reference = declaration.module.reference.model_copy(update={
            "import_module": module_class.__module__,
            "class_qualname": module_class.__qualname__,
            "implementation_version": str(getattr(module_class, "VERSION", declaration.module.reference.implementation_version)),
            "priority": priority,
        })
        declarations.append(declaration.__class__(module=declaration.module.model_copy(update={"reference": reference}), steps=declaration.steps))
    for declaration in declarations:
        drafts.extend(declaration.steps)
    compiled_modules = [declaration.module for declaration in declarations]
    if len({module.reference.module_id for module in compiled_modules}) != len(compiled_modules): raise ValueError("workflow module IDs must be unique")
    outputs = [slot for draft in drafts for slot in draft.definition.outputs]
    output_order = {slot.slot_id: index for index, slot in enumerate(outputs)}
    output_module = {slot.slot_id: draft.definition.module_id for draft in drafts for slot in draft.definition.outputs}
    priorities = {module.reference.module_id: module.reference.priority for module in compiled_modules}
    connections: list[Connection] = []
    occupied_outputs: set[str] = set()
    for draft in sorted(drafts, key=lambda item: (0 if item.definition.assembly_preference == "eager" else 1, -priorities[item.definition.module_id] if item.definition.assembly_preference == "eager" else priorities[item.definition.module_id], item.definition.step_id)):
        for input_slot in draft.definition.inputs:
            predicate = draft.candidates.get(input_slot.slot_id)
            candidates = [slot for slot in outputs if predicate is not None and predicate(input_slot, slot)]
            if isinstance(input_slot, SingleInputSlot):
                if not candidates: raise ValueError(f"input {input_slot.slot_id} has no compatible output")
                available = [slot for slot in candidates if slot.slot_id not in occupied_outputs]
                selected = max(available or candidates, key=lambda slot: (priorities[output_module[slot.slot_id]], output_order[slot.slot_id], slot.slot_id))
                connections.append(Connection(input_slot_id=input_slot.slot_id, output_slot_id=selected.slot_id))
                occupied_outputs.add(selected.slot_id)
            else:
                connections.extend(Connection(input_slot_id=input_slot.slot_id, output_slot_id=slot.slot_id) for slot in candidates)
    workflow = WorkflowDefinition(modules=tuple(compiled_modules), steps=tuple(draft.definition for draft in drafts), connections=tuple(connections))
    return BuildContract(blueprint=blueprint, blueprint_fingerprint=_blueprint_fingerprint(blueprint), sources=source_ir, settings=settings or BuildSettings(), overrides=overrides, workflow_fingerprint=_fingerprint(workflow), workflow=workflow)


def compile_blueprint(*, blueprint: BuildBlueprint, sources: Sequence[BoundTable] = (), settings: BuildSettings | None = None) -> BuildContract:
    """Compile a complete semantic blueprint into its frozen workflow contract."""
    return asyncio.run(_compile_blueprint(blueprint=blueprint, sources=sources, settings=settings))
