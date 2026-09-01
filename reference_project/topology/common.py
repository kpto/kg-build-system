"""Topology vocabulary shared across node packages.

A plain module directly under ``topology/`` carries the authoring
declarations shared across node packages — templates share property slots
and annotation flow, categories are the graph-visible parents recorded in
the blueprint IR. They own no ``bindings/`` mirror because abstract
components are never binding targets.

Authoring convention: every declaration carries its tier in the class-name
suffix — ``...NodeTemplate``/``...EdgeTemplate``, ``...AbstractNode``/
``...AbstractEdge``, ``...Node``/``...Edge`` — and the framework strips the
matching suffix to infer the logical name.
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


class ProvenancedNodeTemplate(NodeTemplate):
    """Every concrete node records the data version it was built from."""

    options = NodeOptionsTemplate(annotations=(Provenance(stage="demo-v1"),))
    source_version: PropertySlot[str] = property()


class DocumentedAbstractNode(AbstractNode):
    """Category: every documented entity carries a human-readable summary."""

    options = NodeOptions(annotations=(NodeLabel("Documented"),))
    summary: PropertySlot[str] = property()


class TrackedRelationEdgeTemplate(EdgeTemplate):
    """Every derived relation carries the originating record's profile city
    and stamps the derivation stage it was produced in."""

    options = EdgeOptionsTemplate(annotations=(Provenance(stage="derived"),))
    city: PropertySlot[str] = property()
    stage: PropertySlot[str] = property()


class DerivedRelationAbstractEdge(AbstractEdge[DocumentedAbstractNode, DocumentedAbstractNode]):
    """Category: relations derived between documented entities."""

    options = EdgeOptions(annotations=(EdgeLabel("DERIVED"),))
