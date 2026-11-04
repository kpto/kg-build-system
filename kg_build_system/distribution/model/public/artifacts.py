"""The distribution's graph artifact vocabulary.

One definition of the artifact types the supplied planners produce and consume.
The kernel carries only the ``ArtifactType`` key; this module names the graph
roles encoded in that key. Constructors take semantic parts, never a dotted
string, and the one parser reads key segments, never a display name.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

from kg_build_system.kernel import ArtifactType


@dataclass(frozen=True, slots=True)
class GraphRecordArtifact:
    """The record kind and component named by one core graph-record type.

    Example:
    ```python
    record = GraphRecordArtifact("node", "site")
    assert record.component == "site"
    ```
    """

    kind: Literal["node", "edge"]
    component: str


class CoreArtifactTypes:
    """Stable artifact types produced and consumed by graph workflow planners.

    Example:
    ```python
    from kg_build_system.distribution.model.public.artifacts import (
        CoreArtifactTypes,
    )

    records = CoreArtifactTypes.graph_records("node", "site")
    assert records.name == "graph.node.site"
    ```
    """

    NAMESPACE = "core"

    @classmethod
    def graph_records(
        cls, kind: Literal["node", "edge"], component: str,
    ) -> ArtifactType:
        """The record stream of one graph component.

        Example:
        ```python
        records = CoreArtifactTypes.graph_records("edge", "site")
        assert records.key.segments == ("core", "graph", "edge", "site")
        ```
        """
        return ArtifactType.of(cls.NAMESPACE, "graph", kind, component)

    @classmethod
    def binding(cls, component: str, index: int) -> ArtifactType:
        """The plan-local rows of one binding contribution.

        Example:
        ```python
        binding = CoreArtifactTypes.binding("site", 0)
        assert binding.name == "binding.site.0"
        ```
        """
        return ArtifactType.of(cls.NAMESPACE, "binding", component, str(index))

    @classmethod
    def table(cls, name: str) -> ArtifactType:
        """The logical relation of one source table.

        Example:
        ```python
        table = CoreArtifactTypes.table("site")
        assert table.name == "data.table.site"
        ```
        """
        return ArtifactType.of(cls.NAMESPACE, "data", "table", name)

    @classmethod
    def projection(cls, name: str) -> ArtifactType:
        """The materialised relation of one projection.

        Example:
        ```python
        projection = CoreArtifactTypes.projection("defects")
        assert projection.name == "data.projection.defects"
        ```
        """
        return ArtifactType.of(cls.NAMESPACE, "data", "projection", name)

    @classmethod
    def row_source(cls, key: str) -> ArtifactType:
        """The materialised relation of one derived row source.

        Example:
        ```python
        row_source = CoreArtifactTypes.row_source("rows")
        assert row_source.name == "data.row_source.rows"
        ```
        """
        return ArtifactType.of(cls.NAMESPACE, "data", "row_source", key)


def graph_record_artifact(
    artifact_type: ArtifactType,
) -> GraphRecordArtifact | None:
    """Read a core graph-record artifact type, if it is one.

    Example:
    ```python
    from kg_build_system.distribution.model.public.artifacts import (
        CoreArtifactTypes, graph_record_artifact,
    )

    record = graph_record_artifact(CoreArtifactTypes.graph_records("node", "site"))
    assert record is not None and record.component == "site"
    ```
    """
    segments = artifact_type.key.segments
    if len(segments) != 4 or segments[:2] != ("core", "graph"):
        return None
    if segments[2] not in {"node", "edge"} or not segments[3]:
        return None
    return GraphRecordArtifact(
        kind=cast(Literal["node", "edge"], segments[2]),
        component=segments[3],
    )


__all__ = ["CoreArtifactTypes", "GraphRecordArtifact", "graph_record_artifact"]
