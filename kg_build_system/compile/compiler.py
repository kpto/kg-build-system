"""Lower authoring declarations into canonical Pydantic IR."""
from __future__ import annotations
from collections.abc import Iterable, Sequence
from typing import Any, Literal, cast
from sqlglot import exp
from ..binding import EdgeBinding, ExpressionBinding, NodeBinding
from ..data import BoundTable
from ..definition.ir import (
    BindingDefinition, BindingExecutionPlan, BuildPolicy, CompiledBuildDefinition, CompiledGraphDefinition,
    ComponentDefinition, EdgeBindingDefinition, FieldReference, FileTargetDefinition,
    LiteralValue, NodeBindingDefinition, Operation, ProjectionDefinition,
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
        operation = cast(Literal["concat", "coalesce", "cast", "deterministic_uuid", "expand", "struct_field", "lookup_one"], {"uuid": "deterministic_uuid"}.get(value.op, value.op))
        skip_string = (value.op == "cast" or value.op == "struct_field")
        args = tuple(_to_ir(arg) for arg in value.args if not (skip_string and isinstance(arg, str)))
        return Operation(op=operation, args=args, value_type=_value_type(value.type_hint, value.cardinality), sql_type=value.args[1] if value.op == "cast" else None, field_name=value.args[1] if value.op == "struct_field" else None)
    return LiteralValue(value=value, value_type=_value_type(type(value)))

def _component(component: type) -> ComponentDefinition:
    metadata = component._metadata; properties = tuple(PropertyDefinition(name=prop.name or attr, value_type=_value_type(prop.type_hint), nullable=prop.nullable) for attr, prop in component._properties.items())
    return ComponentDefinition(name=component.__name__, kind=component._kind, properties=properties, source=getattr(metadata.get("source"), "__name__", None), target=getattr(metadata.get("target"), "__name__", None))

def _binding(binding: NodeBinding | EdgeBinding) -> BindingDefinition:
    properties = {name: _to_ir(value) for name, value in _property_expressions(binding).items()}
    if isinstance(binding, EdgeBinding):
        return EdgeBindingDefinition(component=binding.target.__name__, build_key=_to_ir(binding.build_key), source_build_key=_to_ir(binding.source_build_key), target_build_key=_to_ir(binding.target_build_key), properties=properties)
    return NodeBindingDefinition(component=binding.target.__name__, build_key=_to_ir(binding.build_key), properties=properties)

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

def compile_graph(*, bindings: Iterable[NodeBinding | EdgeBinding], projections: Sequence[type[Any]] = ()) -> CompiledGraphDefinition:
    authoring_bindings = tuple(bindings)
    if not authoring_bindings: raise ValueError("a graph requires at least one binding")
    for binding in authoring_bindings: _validate_authoring_binding(binding)
    components = {_binding.target for _binding in authoring_bindings}
    projection_ir = tuple(ProjectionDefinition(name=projection.__name__, fields={name: _to_ir(field.expression) for name, field in projection._projection_fields.items()}) for projection in projections)
    return CompiledGraphDefinition(components=tuple(_component(component) for component in sorted(components, key=lambda item: item.__name__)), projections=projection_ir, bindings=tuple(_binding(binding) for binding in authoring_bindings))

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

def _compile_binding_sql(*, graph: CompiledGraphDefinition, sources: tuple[SourceDefinition, ...], binding: BindingDefinition) -> str:
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
    return final_query.sql(dialect="duckdb")

def compile_build(*, graph: CompiledGraphDefinition, sources: Sequence[BoundTable], target: object, policy: BuildPolicy | None = None) -> CompiledBuildDefinition:
    if not isinstance(target, FileTarget): raise TypeError("the MVP supports FileTarget only")
    source_ir = tuple(SourceDefinition(table=source.table.__name__, location=source.config.location, format=source.config.format.value, credential_reference=source.config.credentials, version=source.config.version) for source in sources)
    plans = tuple(
        BindingExecutionPlan(binding_index=index, sql=_compile_binding_sql(graph=graph, sources=source_ir, binding=binding))
        for index, binding in enumerate(graph.bindings)
    )
    return CompiledBuildDefinition(
        graph=graph,
        sources=source_ir,
        target=FileTargetDefinition(location=target.location),
        policy=policy or BuildPolicy(),
        plans=plans,
    )
