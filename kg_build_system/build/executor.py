"""Execute only canonical compiled definitions; no authoring classes are read."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from ..definition.ir import CompiledBuildDefinition

@dataclass(frozen=True)
class BuildRuntime:
    credentials: dict[str, str] = field(default_factory=dict)

@dataclass(frozen=True)
class BuildReport:
    nodes: int
    edges: int
    diagnostics: tuple[str, ...]
    provenance: dict[str, Any]

def build(definition: CompiledBuildDefinition, runtime: BuildRuntime = BuildRuntime()) -> BuildReport:
    try: import duckdb
    except ImportError as error: raise RuntimeError("DuckDB is required to execute builds") from error
    output = Path(definition.target.location); output.parent.mkdir(parents=True, exist_ok=True)
    nodes = edges = 0; diagnostics: list[str] = []; seen: set[tuple[str, str]] = set(); connection = duckdb.connect()
    with output.open("w", encoding="utf-8") as stream:
        for plan in definition.plans:
            result = connection.execute(plan.sql)
            columns = tuple(column[0] for column in result.description)
            for row in result.fetchall():
                record = dict(zip(columns, row)); key = record["build_key"]
                if key is None:
                    if definition.policy.null_key == "error": raise ValueError(f"null build key for {plan.component}")
                    diagnostics.append(f"skipped {plan.component}: null build key"); continue
                identity = (plan.component, str(key))
                if identity in seen:
                    if definition.policy.duplicate_key == "error": raise ValueError(f"duplicate build key {key} for {plan.component}")
                    diagnostics.append(f"skipped duplicate key {key} for {plan.component}"); continue
                seen.add(identity); record.update(build_key=str(key), type=plan.component, kind=plan.kind)
                if plan.kind == "edge": edges += 1
                else: nodes += 1
                stream.write(json.dumps(record, sort_keys=True, default=str) + "\n")
    return BuildReport(nodes, edges, tuple(diagnostics), {"plans": [plan.model_dump(mode="json") for plan in definition.plans], "sources": [source.model_dump(mode="json") for source in definition.sources]})
