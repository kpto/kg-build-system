"""Declarative, source-independent knowledge graph topology models."""

from topology.model import (
    Annotation,
    AnnotationTemplate,
    EdgeType,
    Identifier,
    Neo4jIndex,
    Neo4jRelationshipType,
    NodeType,
    Ontology,
    OntologyScope,
    OntologyTerm,
    Property,
    Topology,
    TopologyValidationError,
    ValueType,
)
from topology.declaration import Edge, IdentifierRef, Node, PropertyRef, topology

__all__ = [
    "EdgeType",
    "Edge",
    "Annotation",
    "AnnotationTemplate",
    "Identifier",
    "IdentifierRef",
    "Neo4jIndex",
    "Neo4jRelationshipType",
    "Node",
    "NodeType",
    "Ontology",
    "OntologyScope",
    "OntologyTerm",
    "Property",
    "PropertyRef",
    "Topology",
    "TopologyValidationError",
    "ValueType",
    "topology",
]
