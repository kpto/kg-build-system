"""Execute compiled DuckDB plans and write only normalised graph records."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..definition.ir import BuildContract, ExecutionStep, FileWriteStep, RelationalStep, ValidationStep


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


def _execute_relations(connection: Any, contract: BuildContract) -> tuple[tuple[ValidationStep, ...], tuple[FileWriteStep, ...]]:
    """Materialise relation steps once their declared dependencies are ready."""
    pending = list(contract.execution_plan)
    completed: set[str] = set()
    diagnostics: list[ValidationStep] = []
    writes: list[FileWriteStep] = []
    while pending:
        ready = [step for step in pending if set(step.depends_on) <= completed]
        if not ready:
            raise RuntimeError("DuckDB execution plan has a dependency cycle")
        for step in ready:
            if isinstance(step, RelationalStep):
                statement = "CREATE TEMP TABLE" if step.materialization == "temporary_table" else "CREATE TEMP VIEW"
                connection.execute(f"{statement} {_quote(step.relation)} AS {step.sql}")
            elif isinstance(step, ValidationStep):
                diagnostics.append(step)
            else:
                writes.append(step)
            completed.add(step.id)
            pending.remove(step)
    return tuple(diagnostics), tuple(writes)


def _structural_diagnostics(connection: Any, diagnostic_steps: tuple[ValidationStep, ...]) -> tuple[str, ...]:
    failures: list[str] = []
    for diagnostic in diagnostic_steps:
        rows = connection.execute(diagnostic.sql).fetchall()
        for row in rows:
            # Aggregate diagnostic plans always contain a count; zero means the
            # invariant held and should not appear in a build report.
            if not row or not isinstance(row[-1], int) or row[-1] == 0:
                continue
            if diagnostic.diagnostic_code == "conflicting_value":
                component, build_key, field, distinct_values = row
                failures.append(
                    f"{component}({build_key!s}) has {distinct_values} non-null values for {field}"
                )
            else:
                component, occurrences = row
                failures.append(f"{diagnostic.diagnostic_code} for {component}: {occurrences} record(s)")
    return tuple(failures)


def build(contract: BuildContract, runtime: BuildRuntime = BuildRuntime()) -> BuildReport:
    """Run the compiled relational plans; Python performs only target I/O."""
    try:
        import duckdb
    except ImportError as error:
        raise RuntimeError("DuckDB is required to execute builds") from error

    connection = duckdb.connect()
    if contract.settings.duckdb_threads is not None:
        connection.execute(f"SET threads = {contract.settings.duckdb_threads}")
    diagnostic_steps, write_steps = _execute_relations(connection, contract)
    diagnostics = _structural_diagnostics(connection, diagnostic_steps)
    if diagnostics:
        raise ValueError("graph normalisation failed: " + "; ".join(diagnostics))

    nodes = edges = 0
    for write_step in write_steps:
        assert write_step.target is not None
        output = Path(write_step.target.location)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8") as stream:
            for output_relation in write_step.write_outputs:
                result = connection.execute(f"SELECT * FROM {_quote(output_relation.relation)}")
                columns = tuple(column[0] for column in result.description)
                for row in result.fetchall():
                    record = dict(zip(columns, row, strict=True))
                    record.update(build_key=str(record["build_key"]), type=output_relation.component, kind=output_relation.kind)
                    if output_relation.kind == "node": nodes += 1
                    else: edges += 1
                    stream.write(json.dumps(record, sort_keys=True, default=str) + "\n")
    return BuildReport(
        nodes=nodes,
        edges=edges,
        diagnostics=(),
        provenance={
            "blueprint_fingerprint": contract.blueprint_fingerprint,
            "execution_plan_fingerprint": contract.execution_plan_fingerprint,
            "execution_plan": [step.model_dump(mode="json") for step in contract.execution_plan],
            "sources": [source.model_dump(mode="json") for source in contract.sources],
        },
    )
