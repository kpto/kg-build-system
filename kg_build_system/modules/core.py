"""Built-in runtime module for portable DuckDB workflow steps."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, ClassVar

from ..compile.models import WorkflowStep


class CoreModule:
    ID: ClassVar[str] = "core"
    VERSION: ClassVar[str] = "1"

    @classmethod
    async def create_runtime(cls, _configuration: Mapping[str, Any]) -> CoreModule:
        return cls()

    async def execute_step(self, context: Any, step: WorkflowStep) -> Any:
        payload = step.payload or {}
        connection = context.services["duckdb"]
        if payload.get("action") == "diagnostic":
            return [f"{payload['component']}({key}) has {count} non-null values for {payload['field']}" for key, count in connection.execute(payload["sql"]).fetchall()]
        if payload.get("action") != "relation":
            raise ValueError(f"unsupported core action {payload.get('action')!r}")
        materialization = "TABLE" if payload.get("materialization") == "temporary_table" else "VIEW"
        relation = payload["relation"].replace('"', '""')
        connection.execute(f'CREATE TEMP {materialization} "{relation}" AS {payload["sql"]}')
        return relation
