"""Compilation and validation services."""
from __future__ import annotations
from collections.abc import Iterable, Sequence
from types import UnionType
from typing import Any, get_args, get_origin
from ..binding import EdgeBinding
from ..data import BoundTable, InputFormat
from ..expressions import Expression, FieldPath
from ..expression_sql import render_sql
from .models import Binding, CompiledBuildDefinition, CompiledGraphDefinition

def _values(binding: Binding) -> list[Expression[Any] | FieldPath[Any]]:
    return [binding.build_key, *binding.properties._values.values(), *([binding.source_build_key, binding.target_build_key] if isinstance(binding, EdgeBinding) else [])]

def _compatible(expected: Any, actual: Any) -> bool:
    if expected is Any or actual is Any or actual is None or expected == actual: return True
    return any(_compatible(option, actual) for option in get_args(expected)) if get_origin(expected) is UnionType else False

def _validate(value: Expression[Any] | FieldPath[Any], expected: Any, context: str) -> None:
    if value.cardinality == "collection": raise TypeError(f"{context} maps a collection; use provide.collection.expand(...) explicitly")
    if not _compatible(expected, value.type_hint): raise TypeError(f"{context} expects {expected!r}, but expression resolves to {value.type_hint!r}")

def compile_graph(*, bindings: Iterable[Binding], projections: Sequence[type[object]] = ()) -> CompiledGraphDefinition:
    compiled = tuple(bindings)
    if not compiled: raise ValueError("A graph requires at least one binding")
    for binding in compiled:
        if binding.target._kind not in {"node", "edge"}: raise TypeError("Bindings require a decorated node or edge")
        for name, value in binding.properties._values.items():
            if name not in binding.target._properties: raise TypeError(f"{binding.target.__name__} has no property {name!r}")
            _validate(value, binding.target._properties[name].type_hint, f"{binding.target.__name__}.{name}")
        _validate(binding.build_key, str, f"{binding.target.__name__} build key")
    return CompiledGraphDefinition(compiled, tuple(projections))

def _projection(value: FieldPath[Any]) -> Expression[Any] | FieldPath[Any]:
    fields = getattr(value.table, "_projection_fields", {})
    if not fields or value.path[0] not in fields: return value
    return fields[value.path[0]].expression

def _tables(value: Any) -> set[type]:
    if isinstance(value, FieldPath):
        projected = _projection(value); return {value.table} if projected is value else _tables(projected)
    if isinstance(value, Expression): return set().union(*(_tables(part) for part in value.args)) if value.args else set()
    return set()

def _render(value: Expression[Any] | FieldPath[Any], aliases: dict[type, str]) -> str:
    if isinstance(value, FieldPath):
        projected = _projection(value)
        if projected is not value: return _render(projected, aliases)
    return render_sql(value, aliases)

def _expands(value: Any) -> list[Expression[Any]]:
    return (([value] if value.op == "expand" else []) + [result for part in value.args for result in _expands(part)]) if isinstance(value, Expression) else []

def compile_build(*, graph: CompiledGraphDefinition, sources: Sequence[BoundTable], target: object) -> CompiledBuildDefinition:
    source_map = {source.table: source for source in sources}; values = [value for binding in graph.bindings for value in _values(binding)]
    for projection in graph.projections: values.extend(field.expression for field in projection._projection_fields.values())
    required = set().union(*(_tables(value) for value in values)); missing = required - set(source_map)
    if missing: raise ValueError("No source bound for: " + ", ".join(table.__name__ for table in missing))
    aliases = {table: f"t{index}" for index, table in enumerate(sorted(required, key=lambda table: table.__name__))}
    scans = [f"{'read_csv_auto' if source_map[table].config.format == InputFormat.CSV else 'read_parquet'}('{source_map[table].config.location.replace(chr(39), chr(39)*2)}') AS {aliases[table]}" for table in sorted(required, key=lambda table: table.__name__)]
    from_clause = " CROSS JOIN ".join(scans); expands = list(dict.fromkeys(expand for value in values for expand in _expands(value)))
    if len(expands) > 1: raise ValueError("Multiple expansions require a correlation policy")
    if expands: from_clause += " CROSS JOIN UNNEST(" + _render(expands[0].args[0], aliases) + ") AS expanded(item)"
    ctes = [f'{projection.__name__.lower()} AS (SELECT ' + ", ".join(f'{_render(field.expression, aliases)} AS "{field.name}"' for field in projection._projection_fields.values()) + f" FROM {from_clause})" for projection in graph.projections]
    final_from = graph.projections[-1].__name__.lower() + " AS p0" if graph.projections else from_clause
    return CompiledBuildDefinition(graph, tuple(sources), ("WITH " + ", ".join(ctes) + " " if ctes else "") + "SELECT * FROM " + final_from, target)
