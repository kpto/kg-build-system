"""Graph-record artifact identity for the Neo4j target."""
from __future__ import annotations

from dataclasses import dataclass

from kg_build_system.kernel import ArtifactType


@dataclass(frozen=True, slots=True)
class GraphRecordIdentity:
    """The component and record kind named by a core graph-record artifact."""

    kind: str
    component: str


def graph_record_identity(
    artifact_type: ArtifactType,
) -> GraphRecordIdentity | None:
    """Read a core ``graph.<kind>.<component>`` artifact type, if it is one."""
    if artifact_type.namespace != "core":
        return None
    parts = artifact_type.name.split(".", 2)
    if (
        len(parts) != 3
        or parts[0] != "graph"
        or parts[1] not in {"node", "edge"}
        or not parts[2]
    ):
        return None
    return GraphRecordIdentity(parts[1], parts[2])


__all__ = ["GraphRecordIdentity", "graph_record_identity"]
