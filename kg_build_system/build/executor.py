"""Execute only canonical compiled definitions; no authoring classes are read."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from ..definition.ir import CompiledBuildDefinition, EdgeBindingDefinition, FieldReference, LiteralValue, Operation, Value

@dataclass(frozen=True)
class BuildRuntime:
    credentials: dict[str, str] = field(default_factory=dict)

@dataclass(frozen=True)
class BuildReport:
    nodes: int
    edges: int
    diagnostics: tuple[str, ...]
    provenance: dict[str, Any]

def _sql(value: Value) -> str:
    if isinstance(value, FieldReference): return "plan." + ".".join(f'"{part}"' for part in value.path)
    if isinstance(value, LiteralValue): return "NULL" if value.value is None else repr(value.value)
    args = [_sql(arg) for arg in value.args]
    if value.op == "concat": return "concat(" + ", ".join(args) + ")"
    if value.op == "coalesce": return "coalesce(" + ", ".join(args) + ")"
    if value.op == "cast": return f"CAST({args[0]} AS {value.sql_type})"
    if value.op == "deterministic_uuid": return f"md5({args[0]})"
    if value.op == "expand": return "plan.item"
    if value.op == "lookup_one": return args[2]
    if value.op == "struct_field": return args[0] + f'."{value.field_name}"'
    raise ValueError(f"unsupported IR operation {value.op}")

def build(definition: CompiledBuildDefinition, runtime: BuildRuntime = BuildRuntime()) -> BuildReport:
    try: import duckdb
    except ImportError as error: raise RuntimeError("DuckDB is required to execute builds") from error
    output = Path(definition.target.location); output.parent.mkdir(parents=True, exist_ok=True)
    nodes = edges = 0; diagnostics: list[str] = []; seen: set[tuple[str, str]] = set(); connection = duckdb.connect()
    with output.open("w", encoding="utf-8") as stream:
        for binding, plan in zip(definition.graph.bindings, definition.plans, strict=True):
            columns: list[tuple[str, Value]] = [("build_key", binding.build_key), *binding.properties.items()]
            if isinstance(binding, EdgeBindingDefinition): columns[1:1] = [("source_build_key", binding.source_build_key), ("target_build_key", binding.target_build_key)]
            query = "SELECT " + ", ".join(f'{_sql(value)} AS "{name}"' for name, value in columns) + " FROM (" + plan.sql + ") AS plan"
            for row in connection.execute(query).fetchall():
                record = dict(zip((name for name, _ in columns), row)); key = record["build_key"]
                if key is None:
                    if definition.policy.null_key == "error": raise ValueError(f"null build key for {binding.component}")
                    diagnostics.append(f"skipped {binding.component}: null build key"); continue
                identity = (binding.component, str(key))
                if identity in seen:
                    if definition.policy.duplicate_key == "error": raise ValueError(f"duplicate build key {key} for {binding.component}")
                    diagnostics.append(f"skipped duplicate key {key} for {binding.component}"); continue
                seen.add(identity); record.update(build_key=str(key), type=binding.component, kind=binding.kind)
                if binding.kind == "edge": edges += 1
                else: nodes += 1
                stream.write(json.dumps(record, sort_keys=True, default=str) + "\n")
    return BuildReport(nodes, edges, tuple(diagnostics), {"plans": [plan.model_dump(mode="json") for plan in definition.plans], "sources": [source.model_dump(mode="json") for source in definition.sources]})
