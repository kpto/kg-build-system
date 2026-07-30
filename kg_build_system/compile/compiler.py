"""Lower authoring declarations into canonical Pydantic IR."""
# pyright: reportPrivateImportUsage=false
from __future__ import annotations
from collections.abc import Iterable, Sequence
from hashlib import sha256
import json
from typing import Any, Literal, cast
from sqlglot import exp
from ..binding import EdgeBinding, ExpressionBinding, NodeBinding
from ..data import BoundTable
from ..definition.ir import (
    BindingDefinition, BindingExecutionPlan, BlueprintSymbol, BuildBlueprint, BuildContract, BuildSettings,
    ComponentPostProcessPlan, DebugSymbolReference, DiagnosticPlan,
    ComponentDefinition, EdgeBindingDefinition, FieldReference, FileTargetDefinition,
    LiteralValue, NodeBindingDefinition, Operation, PostProcessingDefinition, ProjectionDefinition,
    PropertyDefinition, SourceDefinition, Value, ValueType,
)
from ..expressions import Expression, FieldPath
from ..specification.type_shapes import type_name, type_shape
from ..targets.file import FileTarget

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

def _blueprint_symbols(*, components: Sequence[type], bindings: Sequence[BindingDefinition], projections: Sequence[type[Any]], sources: Sequence[BoundTable]) -> tuple[BlueprintSymbol, ...]:
    symbols: list[BlueprintSymbol] = []
    for component in components:
        symbols.append(BlueprintSymbol(id=f"component:{component.__name__}", kind="component", path=component.__name__))
        symbols.extend(BlueprintSymbol(id=f"property:{component.__name__}.{name}", kind="property", path=f"{component.__name__}.{name}") for name in component._properties)
    for projection in projections:
        symbols.append(BlueprintSymbol(id=f"projection:{projection.__name__}", kind="projection", path=projection.__name__))
        symbols.extend(BlueprintSymbol(id=f"projection_field:{projection.__name__}.{name}", kind="projection_field", path=f"{projection.__name__}.{name}") for name in projection._projection_fields)
    symbols.extend(BlueprintSymbol(id=binding.symbol_id, kind="binding", path=binding.debug_name or binding.symbol_id) for binding in bindings)
    symbols.extend(BlueprintSymbol(id=f"source:{source.table.__name__}", kind="source", path=source.table.__name__) for source in sources)
    symbols.extend(BlueprintSymbol(id=f"post_processing:{component.__name__}", kind="post_processing", path=component.__name__) for component in components)
    return tuple(symbols)

def create_blueprint(*, bindings: Iterable[NodeBinding | EdgeBinding], projections: Sequence[type[Any]] = (), sources: Sequence[BoundTable] = (), post_processing: PostProcessingDefinition) -> BuildBlueprint:
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
    return BuildBlueprint(components=tuple(_component(component) for component in components), projections=projection_ir, bindings=tuple(binding_definitions), default_sources=tuple(_source_definition(source) for source in sources), post_processing=post_processing, symbols=_blueprint_symbols(components=components, bindings=binding_definitions, projections=projections, sources=sources))

def _projection_value(value: Value, projections: dict[str, ProjectionDefinition]) -> Value:
    if isinstance(value, FieldReference) and value.table in projections and len(value.path) == 1: return projections[value.table].fields[value.path[0]]
    return value

def _tables(value: Value, projections: dict[str, ProjectionDefinition]) -> set[str]:
    value = _projection_value(value, projections)
    if isinstance(value, FieldReference): return {value.table}
    if isinstance(value, Operation): return set().union(*(_tables(arg, projections) for arg in value.args))
    return set()

def _identifier(name: str, *, quoted: bool = True) -> exp.Identifier:
    return exp.Identifier(this=name, quoted=quoted)

def _path_expression(table: str, path: tuple[str, ...]) -> exp.Expression:
    result: exp.Expression = exp.Column(this=_identifier(path[0]), table=_identifier(table))
    for part in path[1:]: result = exp.Dot(this=result, expression=_identifier(part))
    return result

def _render(value: Value, aliases: dict[str, str], projections: dict[str, ProjectionDefinition], expand_aliases: dict[str, exp.Expression] | None = None) -> exp.Expression:
    value = _projection_value(value, projections)
    if isinstance(value, FieldReference): return _path_expression(aliases[value.table], value.path)
    if isinstance(value, LiteralValue):
        if value.value is None: return exp.Null()
        if isinstance(value.value, str): return exp.Literal.string(value.value)
        if isinstance(value.value, bool): return exp.Boolean(this=value.value)
        return exp.Literal.number(value.value)
    args = [_render(arg, aliases, projections, expand_aliases) for arg in value.args]
    if value.op == "concat": return exp.Anonymous(this="concat", expressions=args)
    if value.op == "coalesce": return exp.Coalesce(expressions=args)
    if value.op == "cast": return exp.Cast(this=args[0], to=exp.DataType.build(value.sql_type or "TEXT", dialect="duckdb"))
    if value.op == "deterministic_uuid": return exp.Anonymous(this="md5", expressions=args)
    if value.op == "expand": return (expand_aliases or {})[value.model_dump_json()]
    if value.op == "struct_field": return exp.Dot(this=args[0], expression=_identifier(value.field_name or ""))
    if value.op == "lookup_one": return args[2]
    raise ValueError(f"unsupported IR operation {value.op}")

def _render_plan_value(value: Value) -> exp.Expression:
    """Render a binding output expression against its compiled row context."""
    if isinstance(value, FieldReference): return _path_expression("plan", value.path)
    if isinstance(value, LiteralValue):
        if value.value is None: return exp.Null()
        if isinstance(value.value, str): return exp.Literal.string(value.value)
        if isinstance(value.value, bool): return exp.Boolean(this=value.value)
        return exp.Literal.number(value.value)
    args = [_render_plan_value(arg) for arg in value.args]
    if value.op == "concat": return exp.Anonymous(this="concat", expressions=args)
    if value.op == "coalesce": return exp.Coalesce(expressions=args)
    if value.op == "cast": return exp.Cast(this=args[0], to=exp.DataType.build(value.sql_type or "TEXT", dialect="duckdb"))
    if value.op == "deterministic_uuid": return exp.Anonymous(this="md5", expressions=args)
    if value.op == "expand": return _path_expression("plan", ("item",))
    if value.op == "struct_field": return exp.Dot(this=args[0], expression=_identifier(value.field_name or ""))
    if value.op == "lookup_one": return args[2]
    raise ValueError(f"unsupported IR operation {value.op}")

def _operations(value: Value, operation: str) -> list[Operation]:
    if not isinstance(value, Operation): return []
    return [item for argument in value.args for item in _operations(argument, operation)] + ([value] if value.op == operation else [])

def _field_references(value: Value) -> list[FieldReference]:
    if isinstance(value, FieldReference): return [value]
    if isinstance(value, Operation): return [reference for argument in value.args for reference in _field_references(argument)]
    return []

def _direct_expand_plan(expands: list[Operation], aliases: dict[str, str]) -> tuple[list[tuple[str, exp.Expression]], dict[str, exp.Expression]]:
    """Build shared parent-first UNNEST steps from collection-aware field paths."""
    fields = [expand.args[0] for expand in expands]
    if not all(isinstance(field, FieldReference) and field.collection_paths for field in fields): return [], {}
    ordered: list[tuple[str, tuple[str, ...]]] = []
    for field in fields:
        assert isinstance(field, FieldReference)
        for path in field.collection_paths:
            item = (field.table, path)
            if item not in ordered: ordered.append(item)
    ordered.sort(key=lambda item: len(item[1]))
    aliases_by_path: dict[tuple[str, tuple[str, ...]], str] = {}
    steps: list[tuple[str, exp.Expression]] = []
    for index, (table, path) in enumerate(ordered):
        parent = next((candidate for candidate in reversed(ordered[:index]) if candidate[0] == table and path[:len(candidate[1])] == candidate[1]), None)
        expression: exp.Expression = _path_expression(aliases[table], path) if parent is None else exp.Dot(this=_identifier(aliases_by_path[parent], quoted=False), expression=_identifier("item"))
        if parent is not None:
            for part in path[len(parent[1]):]: expression = exp.Dot(this=expression, expression=_identifier(part))
        alias = f"expanded{index}"
        aliases_by_path[(table, path)] = alias
        steps.append((alias, expression))
    outputs: dict[str, exp.Expression] = {}
    for expand, field in zip(expands, fields):
        assert isinstance(field, FieldReference)
        collection_path = field.collection_paths[-1]
        output: exp.Expression = exp.Dot(this=_identifier(aliases_by_path[(field.table, collection_path)], quoted=False), expression=_identifier("item"))
        remainder = field.path[len(collection_path):]
        for part in remainder: output = exp.Dot(this=output, expression=_identifier(part))
        outputs[expand.model_dump_json()] = output
    return steps, outputs

def _binding_values(binding: BindingDefinition) -> list[Value]:
    """Return every expression that defines a binding's row context."""
    values = [binding.build_key, *binding.properties.values()]
    if isinstance(binding, EdgeBindingDefinition):
        values.extend((binding.source_build_key, binding.target_build_key))
    return values

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

def _view_name(prefix: str, component: str) -> str:
    return f"kg_{prefix}_{component.lower()}"

def _raw_sql(plans: Sequence[BindingExecutionPlan]) -> str:
    return " UNION ALL ".join(
        f"SELECT * FROM ({plan.sql}) AS {_quote(f'raw_{plan.binding_index}')}"
        for plan in plans
    )

def _normalised_sql(*, raw_view: str, kind: str, properties: Sequence[str]) -> str:
    fields = ["build_key", *properties]
    if kind == "edge": fields[1:1] = ["source_build_key", "target_build_key"]
    select = [_quote("build_key")]
    select.extend(f"min({_quote(field)}) AS {_quote(field)}" for field in fields[1:])
    return f"SELECT {', '.join(select)} FROM {_quote(raw_view)} GROUP BY {_quote('build_key')}"

def _diagnostics(*, graph: BuildBlueprint, post_process: Sequence[ComponentPostProcessPlan]) -> tuple[DiagnosticPlan, ...]:
    components = {component.name: component for component in graph.components}
    plans = {plan.component: plan for plan in post_process}
    diagnostics: list[DiagnosticPlan] = []
    for plan in post_process:
        component = components[plan.component]
        raw = _quote(plan.raw_view)
        diagnostics.append(DiagnosticPlan(
            code="null_build_key",
            sql=f"SELECT '{plan.component}' AS component, count(*) AS occurrences FROM {raw} WHERE {_quote('build_key')} IS NULL",
        ))
        fields = [property.name for property in component.properties]
        if plan.kind == "edge":
            diagnostics.append(DiagnosticPlan(
                code="null_edge_endpoint",
                sql=(f"SELECT '{plan.component}' AS component, count(*) AS occurrences FROM {raw} "
                     f"WHERE {_quote('source_build_key')} IS NULL OR {_quote('target_build_key')} IS NULL"),
            ))
            fields[0:0] = ["source_build_key", "target_build_key"]
        for field in fields:
            diagnostics.append(DiagnosticPlan(
                code="conflicting_value",
                sql=(f"SELECT '{plan.component}' AS component, {_quote('build_key')} AS build_key, '{field}' AS field, "
                     f"count(DISTINCT {_quote(field)}) AS distinct_values FROM {raw} "
                     f"WHERE {_quote('build_key')} IS NOT NULL GROUP BY {_quote('build_key')} "
                     f"HAVING count(DISTINCT {_quote(field)}) FILTER (WHERE {_quote(field)} IS NOT NULL) > 1"),
            ))
    for plan in post_process:
        if plan.kind != "edge":
            continue
        edge = components[plan.component]
        assert edge.source is not None and edge.target is not None
        for endpoint, node_component in (("source_build_key", edge.source), ("target_build_key", edge.target)):
            node = plans.get(node_component)
            if node is None:
                diagnostics.append(DiagnosticPlan(
                    code="missing_edge_endpoint",
                    sql=f"SELECT '{plan.component}' AS component, count(*) AS occurrences FROM {_quote(plan.normalised_view)}",
                ))
                continue
            diagnostics.append(DiagnosticPlan(
                code="missing_edge_endpoint",
                sql=(f"SELECT '{plan.component}' AS component, count(*) AS occurrences "
                     f"FROM {_quote(plan.normalised_view)} AS edge_record "
                     f"LEFT JOIN {_quote(node.normalised_view)} AS node_record "
                     f"ON edge_record.{_quote(endpoint)} = node_record.{_quote('build_key')} "
                     f"WHERE node_record.{_quote('build_key')} IS NULL"),
            ))
    return tuple(diagnostics)

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
    payload.pop("symbols")
    for binding in payload["bindings"]:
        binding.pop("debug_name", None)
    return _fingerprint(payload)

def _effective_sources(*, blueprint: BuildBlueprint, settings: BuildSettings) -> tuple[SourceDefinition, ...]:
    sources = {source.table: source for source in blueprint.default_sources}
    for source in settings.source_overrides:
        sources[source.table] = source
    return tuple(sources[name] for name in sorted(sources))

def _debug_symbols(*, blueprint: BuildBlueprint, plans: Sequence[BindingExecutionPlan], post_process: Sequence[ComponentPostProcessPlan], diagnostics: Sequence[DiagnosticPlan]) -> tuple[DebugSymbolReference, ...]:
    references: list[DebugSymbolReference] = []
    for plan in plans:
        references.append(DebugSymbolReference(artifact=f"binding_plan:{plan.binding_symbol}", symbols=(plan.binding_symbol,)))
    for plan in post_process:
        references.append(DebugSymbolReference(artifact=f"relation:{plan.raw_view}", symbols=(f"component:{plan.component}", f"post_processing:{plan.component}")))
        references.append(DebugSymbolReference(artifact=f"relation:{plan.normalised_view}", symbols=(f"component:{plan.component}", f"post_processing:{plan.component}")))
    for index, diagnostic in enumerate(diagnostics):
        references.append(DebugSymbolReference(artifact=f"diagnostic:{index}:{diagnostic.code}", symbols=(f"post_processing:{diagnostic.sql.split(chr(39))[1]}",)))
    return tuple(references)

def compile_blueprint(*, blueprint: BuildBlueprint, target: object, settings: BuildSettings | None = None) -> BuildContract:
    if not isinstance(target, FileTarget): raise TypeError("the MVP supports FileTarget only")
    requested_settings = settings or BuildSettings()
    source_ir = _effective_sources(blueprint=blueprint, settings=requested_settings)
    plans = tuple(
        BindingExecutionPlan(binding_index=index, binding_symbol=binding.symbol_id, component=binding.component, kind=binding.kind, sql=_compile_binding_sql(graph=blueprint, sources=source_ir, binding=binding))
        for index, binding in enumerate(blueprint.bindings)
    )
    post_process = tuple(
        ComponentPostProcessPlan(
            component=component.name,
            kind=component.kind,
            raw_view=_view_name("raw", component.name),
            normalised_view=_view_name("normalised", component.name),
            raw_sql=_raw_sql([plan for plan in plans if plan.component == component.name]),
            normalised_sql=_normalised_sql(
                raw_view=_view_name("raw", component.name),
                kind=component.kind,
                properties=[property.name for property in component.properties],
            ),
        )
        for component in blueprint.components
        if any(plan.component == component.name for plan in plans)
    )
    diagnostics = _diagnostics(graph=blueprint, post_process=post_process)
    effective_settings = BuildSettings(source_overrides=source_ir, duckdb_threads=requested_settings.duckdb_threads)
    execution_fingerprint = _fingerprint({"plans": plans, "post_process": post_process, "diagnostics": diagnostics, "target": target.location})
    return BuildContract(
        blueprint=blueprint,
        blueprint_fingerprint=_blueprint_fingerprint(blueprint),
        sources=source_ir,
        target=FileTargetDefinition(location=target.location),
        requested_settings=requested_settings,
        effective_settings=effective_settings,
        execution_plan_fingerprint=execution_fingerprint,
        plans=plans,
        post_process=post_process,
        diagnostics=diagnostics,
        debug_symbols=_debug_symbols(blueprint=blueprint, plans=plans, post_process=post_process, diagnostics=diagnostics),
    )
