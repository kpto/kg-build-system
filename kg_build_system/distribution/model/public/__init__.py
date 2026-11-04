"""The distribution's authoring model: build settings and typed references."""
from __future__ import annotations

from .artifacts import (
    CoreArtifactTypes, GraphRecordArtifact, graph_record_artifact,
)
from .refs import (
    EdgeRef, FieldRef, NodeRef, OperationRef, PropertyRef, Ref, RelationRef,
    SourceRef, ref_from_document, ref_to_document,
)
from .runtime import BuildRuntime

__all__ = [
    "BuildRuntime", "CoreArtifactTypes", "EdgeRef", "FieldRef",
    "GraphRecordArtifact", "NodeRef", "OperationRef", "PropertyRef", "Ref",
    "RelationRef", "SourceRef", "graph_record_artifact", "ref_from_document",
    "ref_to_document",
]
