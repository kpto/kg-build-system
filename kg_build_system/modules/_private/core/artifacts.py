"""Artifact vocabulary produced by the core module."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

from ....compile.internal.ir import BuildBlueprint
from ....kernel import ArtifactType
from ....topology.internal.ir import ComponentIR


@dataclass(frozen=True, slots=True)
class GraphRecordArtifact:
    kind: Literal["node", "edge"]
    component: str


class CoreArtifactTypes:
    """Stable artifact types produced and consumed by graph workflow modules."""

    NAMESPACE = "core"

    @classmethod
    def graph_records(
        cls, kind: Literal["node", "edge"], component: str,
    ) -> ArtifactType:
        return ArtifactType(namespace=cls.NAMESPACE, name=f"graph.{kind}.{component}")

    @classmethod
    def binding(cls, symbol_id: str) -> ArtifactType:
        return ArtifactType(namespace=cls.NAMESPACE, name=f"binding.{symbol_id}")

    @classmethod
    def table(cls, name: str) -> ArtifactType:
        return ArtifactType(namespace=cls.NAMESPACE, name=f"data.table.{name}")

    @classmethod
    def projection(cls, name: str) -> ArtifactType:
        return ArtifactType(namespace=cls.NAMESPACE, name=f"data.projection.{name}")

    @classmethod
    def row_source(cls, key: str) -> ArtifactType:
        return ArtifactType(namespace=cls.NAMESPACE, name=f"data.row_source.{key}")

    @classmethod
    def graph_record_identity(
        cls, artifact_type: ArtifactType,
    ) -> GraphRecordArtifact | None:
        if artifact_type.namespace != cls.NAMESPACE:
            return None
        parts = artifact_type.name.split(".", 2)
        if (
            len(parts) != 3
            or parts[0] != "graph"
            or parts[1] not in {"node", "edge"}
            or not parts[2]
        ):
            return None
        return GraphRecordArtifact(
            kind=cast(Literal["node", "edge"], parts[1]),
            component=parts[2],
        )

    @classmethod
    def is_graph_records(cls, artifact_type: ArtifactType) -> bool:
        return cls.graph_record_identity(artifact_type) is not None


def graph_record_components(
    blueprint: BuildBlueprint,
) -> tuple[ComponentIR, ...]:
    """Components that actually produce graph records.

    A component produces records only when at least one binding targets it.
    Abstract categories enter the blueprint to carry topology meaning and the
    parent chain, and are never binding targets, so they produce no records,
    no aggregation step, and no downstream artifact for any consumer.
    """
    bound = {binding.component for binding in blueprint.bindings}
    return tuple(item for item in blueprint.components if item.name in bound)


__all__ = [
    "CoreArtifactTypes", "GraphRecordArtifact", "graph_record_components",
]
