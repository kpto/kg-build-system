"""Compilation from declarations to immutable, inspectable definitions."""
from __future__ import annotations
from dataclasses import dataclass
from collections.abc import Iterable, Sequence
from typing import Any
from ..binding import EdgeBinding, NodeBinding
from ..data import BoundTable, InputFormat
from ..expressions import Expression, FieldPath

@dataclass(frozen=True)
class CompiledGraphDefinition:
    bindings: tuple[NodeBinding | EdgeBinding, ...]
    projections: tuple[type, ...] = ()
@dataclass(frozen=True)
class CompiledBuildDefinition:
    graph: CompiledGraphDefinition; sources: tuple[BoundTable, ...]; sql: str; target: Any

def compile_graph(
    *,
    bindings: Iterable[NodeBinding | EdgeBinding],
    projections: Sequence[type[object]] = (),
) -> CompiledGraphDefinition:
    if not bindings: raise ValueError("A graph requires at least one binding")
    return CompiledGraphDefinition(tuple(bindings), tuple(projections))
def _tables(value: Any) -> set[type]:
    if isinstance(value, FieldPath): return {value.table}
    if isinstance(value, Expression): return set().union(*(_tables(v) for v in value.args)) if value.args else set()
    return set()
def _values(binding):
    values = [binding.build_key, *binding.properties._values.values()]
    if isinstance(binding, EdgeBinding): values += [binding.source_build_key, binding.target_build_key]
    return values
def compile_build(
    *,
    graph: CompiledGraphDefinition,
    sources: Sequence[BoundTable],
    target: object,
) -> CompiledBuildDefinition:
    source_map = {s.table: s for s in sources}; required = set().union(*(_tables(v) for b in graph.bindings for v in _values(b)))
    missing = required - set(source_map)
    if missing: raise ValueError("No source bound for: " + ", ".join(t.__name__ for t in missing))
    aliases = {t: f"t{i}" for i, t in enumerate(sorted(required, key=lambda t: t.__name__))}; scans = []
    for table in sorted(required, key=lambda t: t.__name__):
        source = source_map[table]; fn = "read_csv_auto" if source.config.format == InputFormat.CSV else "read_parquet"
        scans.append(f"{fn}('{source.config.location.replace(chr(39), chr(39)*2)}') AS {aliases[table]}")
    expand = next((v for b in graph.bindings for v in _values(b) if isinstance(v, Expression) and v.op == "expand"), None)
    from_clause = " CROSS JOIN ".join(scans)
    if expand: from_clause += " CROSS JOIN UNNEST(" + expand.args[0].sql(aliases) + ") AS expanded(item)"
    return CompiledBuildDefinition(graph, tuple(sources), "SELECT * FROM " + from_clause, target)
