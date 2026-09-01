"""Metric -[:HAS_NOTE]-> Note, a second child of the derived-relation
category narrowed to a different concrete endpoint pair."""

from reference_project.topology._common import DerivedRelation, TrackedRelation
from reference_project.topology.metric import MetricNode
from reference_project.topology.note import NoteNode

from kg_build_system import Edge, EdgeLabel, EdgeOptions


class HasNoteEdge(TrackedRelation, DerivedRelation, Edge[MetricNode, NoteNode]):
    options = EdgeOptions(annotations=(EdgeLabel("HAS_NOTE"),))
