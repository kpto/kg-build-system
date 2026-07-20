"""Topology declaration for the demonstration graph."""

from kg_build_system.topology import (
    Edge,
    IdentifierRef,
    Neo4jIndex,
    Neo4jRelationshipType,
    Node,
    Ontology,
    OntologyScope,
    PropertyRef,
    edge,
    node,
    topology,
)

SO = Ontology("http://purl.obolibrary.org/obo/so.owl", id="so")
MONDO = Ontology("https://purl.obolibrary.org/ontology/MONDO", id="mondo")
RO = Ontology("http://purl.obolibrary.org/obo/ro.owl", id="ro")


class NamedEntity(Node):
    name: PropertyRef[str] = PropertyRef[str](description="Preferred entity name.")


@node(description="A biological target.")
class Target(NamedEntity):
    id: IdentifierRef[str] = IdentifierRef[str](
        description="Ensembl gene identifier.",
        annotations=[SO("0000704")],
    )
    symbol: PropertyRef[str] = PropertyRef[str](
        nullable=False,
        description="Approved gene symbol.",
        annotations=[Neo4jIndex()],
    )


@node(description="A disease or disease phenotype.")
class Disease(NamedEntity):
    id: IdentifierRef[str] = IdentifierRef[str](
        description="Disease ontology identifier.",
        annotations=[MONDO("0000001")],
    )
    name: PropertyRef[str] = PropertyRef[str](
        nullable=False,
        description="Preferred disease name.",
        annotations=[Neo4jIndex()],
    )


class ScoredAssociation(Edge[Target, Disease]):
    score: PropertyRef[float] = PropertyRef[float](nullable=False, description="Association evidence score.")


@edge(
    description="Evidence-backed target-disease association.",
    annotations=[RO("0003302"), Neo4jRelationshipType("ASSOCIATED_WITH")],
)
class AssociatedWith(ScoredAssociation):
    pass


TOPOLOGY = topology(
    "target_disease_demo",
    nodes=(Target, Disease),
    edges=(AssociatedWith,),
    description="A minimal target-disease knowledge graph.",
    annotations=[OntologyScope("biomedical")],
)
