"""Built-in module for portable DuckDB workflow steps."""
from __future__ import annotations

from typing import Any, ClassVar

from ..compile.models import WorkflowStep
from ..workflow.interfaces import Module, ModuleCompiler, ModuleExecutor
from ..workflow.models import Artifact, ModuleExecutionContext, StepOutcome, StepStatus


class CoreModule(Module):
    ID: ClassVar[str] = "core"
    VERSION: ClassVar[str] = "1"

    @classmethod
    async def create_compiler(cls, context: Any) -> ModuleCompiler:
        raise RuntimeError("the core module is compiled by the graph compiler")

    @classmethod
    async def create_executor(cls, context: Any) -> ModuleExecutor:
        return CoreExecutor()


class CoreExecutor:
    async def execute_step(self, context: ModuleExecutionContext, step: WorkflowStep) -> StepOutcome:
        payload = step.payload or {}
        connection = context.services["duckdb"]
        if payload.get("action") != "relation":
            raise ValueError(f"unsupported core action {payload.get('action')!r}")
        materialization = "TABLE" if payload.get("materialization") == "temporary_table" else "VIEW"
        relation = str(payload["relation"]).replace('"', '""')
        connection.execute(f'CREATE TEMP {materialization} "{relation}" AS {payload["sql"]}')
        output = step.outputs[0]
        return StepOutcome(
            step_id=step.step_id,
            module_id=step.module_id,
            status=StepStatus.SUCCEEDED,
            artifacts=(Artifact(output.slot_id, output.artifact_role, relation),),
        )
