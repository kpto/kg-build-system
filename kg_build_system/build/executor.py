"""Execute compiled DuckDB plans and write only normalised graph records."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..definition.ir import BuildContract


@dataclass(frozen=True)
class BuildRuntime:
    credentials: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class BuildReport:
    nodes: int
    edges: int
    diagnostics: tuple[str, ...]
    provenance: dict[str, Any]


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _create_views(connection: Any, definition: BuildContract) -> None:
    for plan in definition.post_process:
        connection.execute(f"CREATE TEMP VIEW {_quote(plan.raw_view)} AS {plan.raw_sql}")
    for plan in definition.post_process:
        connection.execute(f"CREATE TEMP VIEW {_quote(plan.normalised_view)} AS {plan.normalised_sql}")


def _structural_diagnostics(connection: Any, definition: BuildContract) -> tuple[str, ...]:
    failures: list[str] = []
    for diagnostic in definition.diagnostics:
        rows = connection.execute(diagnostic.sql).fetchall()
        for row in rows:
            # Aggregate diagnostic plans always contain a count; zero means the
            # invariant held and should not appear in a build report.
            if not row or not isinstance(row[-1], int) or row[-1] == 0:
                continue
            if diagnostic.code == "conflicting_value":
                component, build_key, field, distinct_values = row
                failures.append(
                    f"{component}({build_key!s}) has {distinct_values} non-null values for {field}"
                )
            else:
                component, occurrences = row
                failures.append(f"{diagnostic.code} for {component}: {occurrences} record(s)")
    return tuple(failures)


def build(contract: BuildContract, runtime: BuildRuntime = BuildRuntime()) -> BuildReport:
    """Run the compiled relational plans; Python performs only target I/O."""
    try:
        import duckdb
    except ImportError as error:
        raise RuntimeError("DuckDB is required to execute builds") from error

    connection = duckdb.connect()
    if contract.effective_settings.duckdb_threads is not None:
        connection.execute(f"SET threads = {contract.effective_settings.duckdb_threads}")
    _create_views(connection, contract)
    diagnostics = _structural_diagnostics(connection, contract)
    if diagnostics:
        raise ValueError("graph normalisation failed: " + "; ".join(diagnostics))

    output = Path(contract.target.location)
    output.parent.mkdir(parents=True, exist_ok=True)
    nodes = edges = 0
    with output.open("w", encoding="utf-8") as stream:
        for plan in contract.post_process:
            result = connection.execute(f"SELECT * FROM {_quote(plan.normalised_view)}")
            columns = tuple(column[0] for column in result.description)
            for row in result.fetchall():
                record = dict(zip(columns, row, strict=True))
                record.update(build_key=str(record["build_key"]), type=plan.component, kind=plan.kind)
                if plan.kind == "node":
                    nodes += 1
                else:
                    edges += 1
                stream.write(json.dumps(record, sort_keys=True, default=str) + "\n")
    return BuildReport(
        nodes=nodes,
        edges=edges,
        diagnostics=(),
        provenance={
            "blueprint_fingerprint": contract.blueprint_fingerprint,
            "execution_plan_fingerprint": contract.execution_plan_fingerprint,
            "plans": [plan.model_dump(mode="json") for plan in contract.plans],
            "post_process": [plan.model_dump(mode="json") for plan in contract.post_process],
            "sources": [source.model_dump(mode="json") for source in contract.sources],
        },
    )
