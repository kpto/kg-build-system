"""DuckDB lowering owned by the built-in core workflow module."""
from __future__ import annotations

from dataclasses import dataclass

from sqlglot import exp

from ..compile.models import BindingDefinition, BuildBlueprint, EdgeBindingDefinition, FieldReference, LiteralValue, Operation, ProjectionDefinition, SourceDefinition, Value


def _projection(value: Value, projections: dict[str, ProjectionDefinition]) -> Value:
    if isinstance(value, FieldReference) and value.table in projections and len(value.path) == 1:
        return projections[value.table].fields[value.path[0]]
    return value


def _references(value: Value) -> list[FieldReference]:
    if isinstance(value, FieldReference): return [value]
    if isinstance(value, Operation): return [reference for argument in value.args for reference in _references(argument)]
    return []


def _tables(value: Value, projections: dict[str, ProjectionDefinition]) -> set[str]:
    value = _projection(value, projections)
    if isinstance(value, FieldReference): return {value.table}
    if isinstance(value, Operation): return set().union(*(_tables(argument, projections) for argument in value.args))
    return set()


def _operations(value: Value, name: str) -> list[Operation]:
    if not isinstance(value, Operation): return []
    return [item for argument in value.args for item in _operations(argument, name)] + ([value] if value.op == name else [])


def _identifier(name: str, *, quoted: bool = True) -> exp.Identifier: return exp.Identifier(this=name, quoted=quoted)
def _path(table: str, path: tuple[str, ...]) -> exp.Expression:
    result: exp.Expression = exp.Column(this=_identifier(path[0]), table=_identifier(table))
    for part in path[1:]: result = exp.Dot(this=result, expression=_identifier(part))
    return result


@dataclass(frozen=True)
class _RenderContext:
    projections: dict[str, ProjectionDefinition]
    aliases: dict[str, str] | None = None
    expanded: dict[str, exp.Expression] | None = None
    row_alias: str | None = None
    resolve_projections: bool = True

    def field(self, value: FieldReference) -> exp.Expression:
        return _path(self.row_alias, value.path) if self.row_alias else _path(self.aliases[value.table], value.path)  # type: ignore[index]

    def expand(self, value: Operation) -> exp.Expression:
        return _path(self.row_alias, ("item",)) if self.row_alias else self.expanded[value.model_dump_json()]  # type: ignore[index]


def _render(value: Value, context: _RenderContext) -> exp.Expression:
    if context.resolve_projections:
        value = _projection(value, context.projections)
    if isinstance(value, FieldReference): return context.field(value)
    if isinstance(value, LiteralValue):
        if value.value is None: return exp.Null()
        if isinstance(value.value, str): return exp.Literal.string(value.value)
        if isinstance(value.value, bool): return exp.Boolean(this=value.value)
        return exp.Literal.number(value.value)
    args = [_render(arg, context) for arg in value.args]
    if value.op == "concat": return exp.Anonymous(this="concat", expressions=args)
    if value.op == "coalesce": return exp.Coalesce(expressions=args)
    if value.op == "cast": return exp.Cast(this=args[0], to=exp.DataType.build(value.sql_type or "TEXT", dialect="duckdb"))
    if value.op == "deterministic_uuid": return exp.Anonymous(this="md5", expressions=args)
    if value.op == "expand": return context.expand(value)
    if value.op == "struct_field": return exp.Dot(this=args[0], expression=_identifier(value.field_name or ""))
    if value.op == "lookup_one": return args[2]
    raise ValueError(f"unsupported IR operation {value.op}")
def _binding_values(binding: BindingDefinition) -> list[Value]:
    values = [binding.build_key, *binding.properties.values()]
    if isinstance(binding, EdgeBindingDefinition): values.extend((binding.source_build_key, binding.target_build_key))
    return values


def _direct_expands(expands: list[Operation], aliases: dict[str, str]) -> tuple[list[tuple[str, exp.Expression]], dict[str, exp.Expression]]:
    fields = [expand.args[0] for expand in expands]
    if not all(isinstance(field, FieldReference) and field.collection_paths for field in fields): return [], {}
    ordered: list[tuple[str, tuple[str, ...]]] = []
    for field in fields:
        assert isinstance(field, FieldReference)
        for path in field.collection_paths:
            item = (field.table, path)
            if item not in ordered: ordered.append(item)
    ordered.sort(key=lambda item: len(item[1]))
    aliases_by_path: dict[tuple[str, tuple[str, ...]], str] = {}; steps: list[tuple[str, exp.Expression]] = []
    for index, (table, path) in enumerate(ordered):
        parent = next((candidate for candidate in reversed(ordered[:index]) if candidate[0] == table and path[:len(candidate[1])] == candidate[1]), None)
        expression: exp.Expression = _path(aliases[table], path) if parent is None else exp.Dot(this=_identifier(aliases_by_path[parent], quoted=False), expression=_identifier("item"))
        if parent is not None:
            for part in path[len(parent[1]):]: expression = exp.Dot(this=expression, expression=_identifier(part))
        alias = f"expanded{index}"; aliases_by_path[(table, path)] = alias; steps.append((alias, expression))
    outputs: dict[str, exp.Expression] = {}
    for expand, field in zip(expands, fields):
        assert isinstance(field, FieldReference)
        collection_path = field.collection_paths[-1]
        output: exp.Expression = exp.Dot(this=_identifier(aliases_by_path[(field.table, collection_path)], quoted=False), expression=_identifier("item"))
        for part in field.path[len(collection_path):]: output = exp.Dot(this=output, expression=_identifier(part))
        outputs[expand.model_dump_json()] = output
    return steps, outputs


def lower_binding_sql(graph: BuildBlueprint, sources: tuple[SourceDefinition, ...], binding: BindingDefinition) -> str:
    projections = {projection.name: projection for projection in graph.projections}
    binding_values = _binding_values(binding)
    used = [projection for projection in graph.projections if any(reference.table == projection.name for value in binding_values for reference in _references(value))]
    if len(used) > 1: raise ValueError("a binding may reference fields from only one projection")
    values = binding_values + [value for projection in used for value in projection.fields.values()]
    required = set().union(*(_tables(value, projections) for value in values))
    available = {source.table: source for source in sources}
    missing = required - set(available)
    if missing: raise ValueError("no source bound for: " + ", ".join(sorted(missing)))
    aliases = {table: f"t{index}" for index, table in enumerate(sorted(required))}
    source_context = _RenderContext(projections=projections, aliases=aliases)
    def scan(table: str) -> exp.Table:
        source = available[table]; function = {"csv": "read_csv_auto", "json": "read_json_auto", "parquet": "read_parquet"}[source.format]
        return exp.Table(this=exp.Anonymous(this=function, expressions=[exp.Literal.string(source.location)]), alias=exp.TableAlias(this=_identifier(aliases[table], quoted=False)))
    lookups = [lookup for value in values for lookup in _operations(value, "lookup_one")]
    lookup_tables = {lookup.args[1].table for lookup in lookups if isinstance(lookup.args[1], FieldReference)}
    bases = sorted(required - lookup_tables)
    if not bases: raise ValueError("a lookup requires a non-lookup source table")
    query = exp.select("*").from_(scan(bases[0]))
    for table in bases[1:]: query = query.join(scan(table), join_type="CROSS")
    for lookup in lookups:
        match = lookup.args[1]
        if not isinstance(match, FieldReference): raise ValueError("lookup match must be a field reference")
        query = query.join(scan(match.table), on=exp.EQ(this=_render(match, source_context), expression=_render(lookup.args[0], source_context)), join_type="LEFT")
    expands = list({item.model_dump_json(): item for value in values for item in _operations(value, "expand")}.values())
    direct = [item for item in expands if isinstance(item.args[0], FieldReference) and item.args[0].collection_paths]
    steps, expanded = _direct_expands(direct, aliases)
    source_context = _RenderContext(projections=projections, aliases=aliases, expanded=expanded)
    for alias, expression in steps:
        query = query.join(exp.Unnest(expressions=[expression], alias=exp.TableAlias(this=_identifier(alias, quoted=False), columns=[_identifier("item", quoted=False)])), join_type="CROSS")
    for index, operation in enumerate([item for item in expands if item not in direct], start=len(steps)):
        alias = f"expanded{index}"; expanded[operation.model_dump_json()] = exp.Dot(this=_identifier(alias, quoted=False), expression=_identifier("item"))
        query = query.join(exp.Unnest(expressions=[_render(operation.args[0], source_context)], alias=exp.TableAlias(this=_identifier(alias, quoted=False), columns=[_identifier("item", quoted=False)])), join_type="CROSS")
    final: exp.Expression = query
    for projection in used:
        select = [exp.alias_(_render(value, source_context), name, quoted=True) for name, value in projection.fields.items()]
        direct_fields = {(field.table, (field.path[0],)): field.model_copy(update={"path": (field.path[0],)}) for value in binding_values for field in _references(value) if field.table not in projections}
        names = set(projection.fields)
        for field in direct_fields.values():
            if field.path[-1] not in names: select.append(exp.alias_(_render(field, source_context), field.path[-1], quoted=True))
        final = exp.select("*").from_(exp.Table(this=_identifier(projection.name.lower(), quoted=False), alias=exp.TableAlias(this=_identifier("p0", quoted=False)))).with_(projection.name.lower(), as_=query.copy().select(*select, append=False))
    plan_context = _RenderContext(projections=projections, row_alias="plan", resolve_projections=False)
    columns = [exp.alias_(_render(binding.build_key, plan_context), "build_key", quoted=True)]
    if isinstance(binding, EdgeBindingDefinition): columns.extend((exp.alias_(_render(binding.source_build_key, plan_context), "source_build_key", quoted=True), exp.alias_(_render(binding.target_build_key, plan_context), "target_build_key", quoted=True)))
    columns.extend(exp.alias_(_render(value, plan_context), name, quoted=True) for name, value in binding.properties.items())
    return exp.select(*columns).from_(exp.Subquery(this=final, alias=exp.TableAlias(this=_identifier("plan", quoted=False)))).sql(dialect="duckdb")
