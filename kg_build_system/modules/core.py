"""Built-in module for portable DuckDB workflow steps and artifact roles.

``CoreArtifactRoles`` is the extension-facing vocabulary for artifacts
published by core graph work.  Modules should use it instead of role strings.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Literal

from ..compile.models import ArtifactRole, WorkflowStep
from ..workflow.interfaces import Module, ModuleCompiler, ModuleExecutor
from ..workflow.models import Artifact, ModuleExecutionContext, StepOutcome, StepStatus


@dataclass(frozen=True)
class GraphRecordArtifact:
    """The component described by a core graph-record role."""

    kind: Literal["node", "edge"]
    component: str


class CoreArtifactRoles:
    """Stable semantic roles produced by the core module.

    Relation roles are core-internal workflow links. ``graph_records`` and
    ``published`` are the supported extension-facing roles.
    """

    NAMESPACE = "core"

    @classmethod
    def binding_relation(cls, binding_index: int) -> ArtifactRole:
        if binding_index < 0:
            raise ValueError("binding indexes must be non-negative")
        return ArtifactRole(namespace=cls.NAMESPACE, name=f"relation.binding.{binding_index}")

    @classmethod
    def raw_relation(cls, component: str) -> ArtifactRole:
        return ArtifactRole(namespace=cls.NAMESPACE, name=f"relation.raw.{component}")

    @classmethod
    def distinct_relation(cls, component: str) -> ArtifactRole:
        return ArtifactRole(namespace=cls.NAMESPACE, name=f"relation.distinct.{component}")

    @classmethod
    def graph_records(cls, kind: Literal["node", "edge"], component: str) -> ArtifactRole:
        return ArtifactRole(namespace=cls.NAMESPACE, name=f"graph.records.{kind}.{component}")

    @classmethod
    def published(cls, module_id: str, name: str) -> ArtifactRole:
        """Mark an otherwise module-owned artifact as a workflow result."""
        return ArtifactRole(namespace=cls.NAMESPACE, name=f"publication.{module_id}.{name}")

    @classmethod
    def graph_record_identity(cls, role: ArtifactRole) -> GraphRecordArtifact | None:
        if role.namespace != cls.NAMESPACE:
            return None
        parts = role.name.split(".", 3)
        if len(parts) != 4 or parts[:2] != ["graph", "records"] or parts[2] not in {"node", "edge"} or not parts[3]:
            return None
        return GraphRecordArtifact(kind=parts[2], component=parts[3])

    @classmethod
    def is_graph_records(cls, role: ArtifactRole) -> bool:
        return cls.graph_record_identity(role) is not None

    @classmethod
    def is_publication(cls, role: ArtifactRole) -> bool:
        return role.namespace == cls.NAMESPACE and role.name.startswith("publication.")


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
        if payload.get("action") == "publish":
            published = tuple(artifact for artifacts in context.inputs.values() for artifact in artifacts)
            return StepOutcome(
                step_id=step.step_id,
                module_id=step.module_id,
                status=StepStatus.SUCCEEDED,
                result={"published_artifacts": published},
            )
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
