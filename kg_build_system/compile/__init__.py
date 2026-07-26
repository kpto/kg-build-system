"""Compilation from declarations to immutable, inspectable definitions."""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from types import UnionType
from typing import Any, get_args, get_origin

from ..binding import EdgeBinding, NodeBinding
from ..data import BoundTable, InputFormat
from ..expressions import Expression, FieldPath, item_type

Binding = NodeBinding | EdgeBinding

@dataclass(frozen=True)
class CompiledGraphDefinition:
    bindings: tuple[Binding, ...]
    projections: tuple[type, ...] = ()

@dataclass(frozen=True)
class CompiledBuildDefinition:
    graph: CompiledGraphDefinition
    sources: tuple[BoundTable, ...]
    sql: str
    target: object

def _type_compatible(expected: Any, actual: Any) -> bool:
    if expected is Any or actual is Any or actual is None: return True
    if expected == actual: return True
    origin = get_origin(expected)
    if origin in (UnionType,): return any(_type_compatible(option, actual) for option in get_args(expected))
    return False

def _values(binding: Binding) -> list[Expression[Any] | FieldPath[Any]]:
    values = [binding.build_key, *binding.properties._values.values()]
    if isinstance(binding, EdgeBinding): values += [binding.source_build_key, binding.target_build_key]
    return values

def _validate_value(value: Expression[Any] | FieldPath[Any], *, expected: Any, context: str) -> None:
    if value.cardinality == "collection":
        raise TypeError(f"{context} maps a collection; use provide.collection.expand(...) explicitly")
    if not _type_compatible(expected, value.type_hint):
        raise TypeError(f"{context} expects {expected!r}, but expression resolves to {value.type_hint!r}")

def compile_graph(*, bindings: Iterable[Binding], projections: Sequence[type[object]] = ()) -> CompiledGraphDefinition:
    compiled = tuple(bindings)
    if not compiled: raise ValueError("A graph requires at least one binding")
    for binding in compiled:
        if binding.target._kind not in {"node", "edge"}: raise TypeError("Bindings require a decorated node or edge")
        for name, value in binding.properties._values.items():
            if name not in binding.target._properties: raise TypeError(f"{binding.target.__name__} has no property {name!r}")
            _validate_value(value, expected=binding.target._properties[name].type_hint, context=f"{binding.target.__name__}.{name}")
        _validate_value(binding.build_key, expected=str, context=f"{binding.target.__name__} build key")
    return CompiledGraphDefinition(compiled, tuple(projections))

def _projection_expression(path: FieldPath[Any]) -> Expression[Any] | FieldPath[Any]:
    fields = getattr(path.table, "_projection_fields", {})
    if not fields or path.path[0] not in fields: return path
    expression = fields[path.path[0]].expression
    if len(path.path) > 1 and isinstance(expression, FieldPath):
        for part in path.path[1:]: expression = getattr(expression, part)
    return expression

def _tables(value: Any) -> set[type]:
    if isinstance(value, FieldPath):
        projected = _projection_expression(value)
        return {value.table} if projected is value else _tables(projected)
    if isinstance(value, Expression): return set().union(*(_tables(part) for part in value.args)) if value.args else set()
    return set()

def _render(value: Expression[Any] | FieldPath[Any], aliases: dict[type, str]) -> str:
    if isinstance(value, FieldPath):
        projected = _projection_expression(value)
        if projected is not value: return _render(projected, aliases)
    return value.sql(aliases)

def _expands(value: Any) -> list[Expression[Any]]:
    if isinstance(value, Expression):
        here = [value] if value.op == "expand" else []
        return here + [result for part in value.args for result in _expands(part)]
    return []

def compile_build(*, graph: CompiledGraphDefinition, sources: Sequence[BoundTable], target: object) -> CompiledBuildDefinition:
    source_map = {source.table: source for source in sources}
    all_values = [value for binding in graph.bindings for value in _values(binding)]
    for projection_type in graph.projections:
        all_values.extend(field.expression for field in projection_type._projection_fields.values())
    required = set().union(*(_tables(value) for value in all_values))
    missing = required - set(source_map)
    if missing: raise ValueError("No source bound for: " + ", ".join(table.__name__ for table in missing))
    aliases = {table: f"t{index}" for index, table in enumerate(sorted(required, key=lambda table: table.__name__))}
    scans = []
    for table in sorted(required, key=lambda table: table.__name__):
        source = source_map[table]; function = "read_csv_auto" if source.config.format == InputFormat.CSV else "read_parquet"
        scans.append(f"{function}('{source.config.location.replace(chr(39), chr(39) * 2)}') AS {aliases[table]}")
    from_clause = " CROSS JOIN ".join(scans)
    # Every expansion is explicit; this MVP accepts exactly one per row context.
    expands = [expand for value in all_values for expand in _expands(value)]
    unique_expands = list(dict.fromkeys(expands))
    if len(unique_expands) > 1: raise ValueError("Multiple expansions require a correlation policy")
    if unique_expands: from_clause += " CROSS JOIN UNNEST(" + _render(unique_expands[0].args[0], aliases) + ") AS expanded(item)"
    ctes: list[str] = []
    for projection_type in graph.projections:
        fields = projection_type._projection_fields.values()
        select = ", ".join(f'{_render(field.expression, aliases)} AS "{field.name}"' for field in fields)
        ctes.append(f'{projection_type.__name__.lower()} AS (SELECT {select} FROM {from_clause})')
    if graph.projections:
        from_clause = graph.projections[-1].__name__.lower() + " AS p0"
    prefix = ("WITH " + ", ".join(ctes) + " ") if ctes else ""
    return CompiledBuildDefinition(graph, tuple(sources), prefix + "SELECT * FROM " + from_clause, target)
