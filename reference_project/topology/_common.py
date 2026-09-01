"""Shared topology declarations: templates and categories, never bound.

Underscore-prefixed modules directly under ``topology/`` carry authoring
declarations shared across node packages — templates share property slots
and annotation flow, categories are the graph-visible parents recorded in
the blueprint IR. They own no ``bindings/`` mirror because abstract
components are never binding targets.
"""

from dataclasses import dataclass

from kg_build_system import (
    AbstractEdge, AbstractNode, Annotation, EdgeLabel, EdgeOptions,
    EdgeOptionsTemplate, EdgeTemplate, NodeLabel, NodeOptions,
    NodeOptionsTemplate, NodeTemplate, PropertySlot, property,
)


@dataclass(frozen=True)
class Provenance(Annotation):
    """Records which authoring stage produced or tracks a component."""

    namespace = "reference_project"
    annotation_id = "provenance"

    stage: str


class Provenanced(NodeTemplate):
    """Every concrete node records the data version it was built from."""

    options = NodeOptionsTemplate(annotations=(Provenance(stage="demo-v1"),))
    source_version: PropertySlot[str] = property()


class Documented(AbstractNode):
    """Category: every documented entity carries a human-readable summary."""

    options = NodeOptions(annotations=(NodeLabel("Documented"),))
    summary: PropertySlot[str] = property()


class TrackedRelation(EdgeTemplate):
    """Every derived relation carries the originating record's profile city."""

    options = EdgeOptionsTemplate(annotations=(Provenance(stage="derived"),))
    city: PropertySlot[str] = property()


class DerivedRelation(AbstractEdge[Documented, Documented]):
    """Category: relations derived between documented entities."""

    options = EdgeOptions(annotations=(EdgeLabel("DERIVED"),))
