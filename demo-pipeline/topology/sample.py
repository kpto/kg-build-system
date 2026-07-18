"""Statically typed Python definition of the demonstration graph.

Downstream bindings will be able to reference ``Target.symbol``,
``Disease.name``, and ``AssociatedWith.score`` directly.
"""

import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from topology import (
    Edge,
    IdentifierRef,
    Neo4jIndex,
    Neo4jRelationshipType,
    Node,
    Ontology,
    OntologyScope,
    PropertyRef,
    topology,
)

SO = Ontology("http://purl.obolibrary.org/obo/so.owl", id="so")
MONDO = Ontology("https://purl.obolibrary.org/ontology/MONDO", id="mondo")
RO = Ontology("http://purl.obolibrary.org/obo/ro.owl", id="ro")


class Target(
    Node,
    description="A biological target.",
):
    id: IdentifierRef[str] = IdentifierRef[str](
        description="Ensembl gene identifier.",
        annotations=[SO("0000704")],
    )
    symbol: PropertyRef[str] = PropertyRef[str](
        nullable=False,
        description="Approved gene symbol.",
        annotations=[Neo4jIndex()],
    )
    name: PropertyRef[str] = PropertyRef[str](description="Approved target name.")


class Disease(
    Node,
    description="A disease or disease phenotype.",
):
    id: IdentifierRef[str] = IdentifierRef[str](
        description="Disease ontology identifier.",
        annotations=[MONDO("0000001")],
    )
    name: PropertyRef[str] = PropertyRef[str](
        nullable=False,
        description="Preferred disease name.",
        annotations=[Neo4jIndex()],
    )


class AssociatedWith(
    Edge[Target, Disease],
    description="Evidence-backed target–disease association.",
    annotations=[
        RO("0003302"),
        Neo4jRelationshipType("ASSOCIATED_WITH"),
    ],
):
    score: PropertyRef[float] = PropertyRef[float](nullable=False, description="Association evidence score.")


TOPOLOGY = topology(
    "target_disease_demo",
    nodes=(Target, Disease),
    edges=(AssociatedWith,),
    description="A minimal target–disease knowledge graph for the MVP demonstration pipeline.",
    annotations=[OntologyScope("biomedical")],
)
