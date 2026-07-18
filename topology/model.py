"""The abstract data model for a knowledge graph topology.

This package deliberately contains no data acquisition or target-specific
execution code. Target features belong in namespaced annotations so that the
core node and edge semantics remain portable.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, ClassVar, Self

NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
SCHEMA_VERSION = "1"


class TopologyValidationError(ValueError):
    """Raised when a topology is structurally invalid."""


class ValueType(StrEnum):
    """Portable property value types supported by the MVP."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"


class Annotation:
    """Base class for semantic and target-specific topology annotations."""

    key: ClassVar[str]

    def to_dict(self) -> dict[str, Any]:
        """Return the portable representation of this annotation."""
        raise NotImplementedError


class AnnotationTemplate:
    """A globally declared object that can be referenced by annotations."""

    def to_dict(self) -> dict[str, Any]:
        """Return the portable representation of this definition."""
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class Ontology(AnnotationTemplate):
    """A globally serialised ontology definition and term-annotation factory."""

    uri: str
    id: str

    def __post_init__(self) -> None:
        if not self.uri or not isinstance(self.uri, str):
            raise TopologyValidationError("Ontology URIs must be non-empty strings.")
        if not self.id or not isinstance(self.id, str):
            raise TopologyValidationError("Annotation template IDs must be non-empty strings.")

    def __call__(self, term: str) -> OntologyTerm:
        """Create an ontology-term annotation in this ontology."""
        return OntologyTerm(ontology=self, term=term)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "type": "ontology", "uri": self.uri}


@dataclass(frozen=True, slots=True)
class OntologyTerm(Annotation):
    """Maps an element to a term from a preselected ontology."""

    ontology: Ontology
    term: str
    key: ClassVar[str] = "ontology.term"

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.key, "template": self.ontology.id, "term": self.term}


@dataclass(frozen=True, slots=True)
class OntologyScope(Annotation):
    """Describes the ontology scope of a topology."""

    scope: str
    key: ClassVar[str] = "ontology.scope"

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.key, "value": self.scope}


@dataclass(frozen=True, slots=True)
class Neo4jIndex(Annotation):
    """Requests a standard Neo4j index for the annotated property."""

    key: ClassVar[str] = "neo4j.index"

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.key}


@dataclass(frozen=True, slots=True)
class Neo4jRelationshipType(Annotation):
    """Overrides the relationship type used for a Neo4j target."""

    relationship_type: str
    key: ClassVar[str] = "neo4j.relationship_type"

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.key, "value": self.relationship_type}


def _annotation_from_dict(
    data: Mapping[str, Any],
    templates: Mapping[str, AnnotationTemplate],
) -> Annotation:
    annotation_type = _required_str(data, "type")
    match annotation_type:
        case OntologyTerm.key:
            template_id = _required_str(data, "template")
            template = templates.get(template_id)
            if not isinstance(template, Ontology):
                raise TopologyValidationError(f"Unknown ontology template: {template_id!r}")
            return template(_required_str(data, "term"))
        case OntologyScope.key:
            return OntologyScope(_required_str(data, "value"))
        case Neo4jIndex.key:
            return Neo4jIndex()
        case Neo4jRelationshipType.key:
            return Neo4jRelationshipType(_required_str(data, "value"))
        case _:
            raise TopologyValidationError(f"Unsupported annotation type: {annotation_type!r}")


def _annotation_template_from_dict(data: Mapping[str, Any]) -> AnnotationTemplate:
    template_type = _required_str(data, "type")
    if template_type == "ontology":
        return Ontology(uri=_required_str(data, "uri"), id=_required_str(data, "id"))
    raise TopologyValidationError(f"Unsupported annotation template type: {template_type!r}")


def _validate_name(value: str, *, kind: str) -> None:
    if not NAME_PATTERN.fullmatch(value):
        message = f"{kind} name must match {NAME_PATTERN.pattern}: {value!r}"
        raise TopologyValidationError(message)


def _validate_annotations(annotations: Sequence[Annotation]) -> None:
    if not all(isinstance(annotation, Annotation) for annotation in annotations):
        raise TopologyValidationError("Annotations must be Annotation instances.")
    keys = [annotation.key for annotation in annotations]
    if len(keys) != len(set(keys)):
        raise TopologyValidationError("Annotation keys must be unique on one element.")


@dataclass(frozen=True, slots=True)
class Property:
    """A named property on a node or edge type."""

    name: str
    value_type: ValueType
    nullable: bool = True
    many: bool = False
    description: str | None = None
    annotations: Sequence[Annotation] = ()

    def __post_init__(self) -> None:
        _validate_name(self.name, kind="Property")
        _validate_annotations(self.annotations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value_type": self.value_type.value,
            "nullable": self.nullable,
            "many": self.many,
            "description": self.description,
            "annotations": [annotation.to_dict() for annotation in self.annotations],
        }

    @classmethod
    def from_dict(
        cls,
        data: Mapping[str, Any],
        *,
        templates: Mapping[str, AnnotationTemplate] | None = None,
    ) -> Self:
        return cls(
            name=_required_str(data, "name"),
            value_type=ValueType(_required_str(data, "value_type")),
            nullable=_optional_bool(data, "nullable", default=True),
            many=_optional_bool(data, "many", default=False),
            description=_optional_str(data, "description"),
            annotations=_optional_annotations(data, templates=templates),
        )


@dataclass(frozen=True, slots=True)
class Identifier:
    """The stable identifier policy for a node type."""

    value_type: ValueType = ValueType.STRING
    description: str | None = None
    annotations: Sequence[Annotation] = ()

    def __post_init__(self) -> None:
        _validate_annotations(self.annotations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "value_type": self.value_type.value,
            "description": self.description,
            "annotations": [annotation.to_dict() for annotation in self.annotations],
        }

    @classmethod
    def from_dict(
        cls,
        data: Mapping[str, Any],
        *,
        templates: Mapping[str, AnnotationTemplate] | None = None,
    ) -> Self:
        return cls(
            value_type=ValueType(_required_str(data, "value_type")),
            description=_optional_str(data, "description"),
            annotations=_optional_annotations(data, templates=templates),
        )


@dataclass(frozen=True, slots=True)
class NodeType:
    """A source-independent category of graph node."""

    name: str
    identifier: Identifier = field(default_factory=Identifier)
    properties: Sequence[Property] = ()
    description: str | None = None
    annotations: Sequence[Annotation] = ()

    def __post_init__(self) -> None:
        _validate_name(self.name, kind="Node")
        _validate_annotations(self.annotations)
        _validate_unique_property_names(self.properties, owner=f"Node {self.name}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "identifier": self.identifier.to_dict(),
            "properties": [property_.to_dict() for property_ in self.properties],
            "description": self.description,
            "annotations": [annotation.to_dict() for annotation in self.annotations],
        }

    @classmethod
    def from_dict(
        cls,
        data: Mapping[str, Any],
        *,
        templates: Mapping[str, AnnotationTemplate] | None = None,
    ) -> Self:
        return cls(
            name=_required_str(data, "name"),
            identifier=Identifier.from_dict(_required_mapping(data, "identifier"), templates=templates),
            properties=tuple(
                Property.from_dict(item, templates=templates) for item in _optional_mappings(data, "properties")
            ),
            description=_optional_str(data, "description"),
            annotations=_optional_annotations(data, templates=templates),
        )


@dataclass(frozen=True, slots=True)
class EdgeType:
    """A directed relationship between two declared node types."""

    name: str
    source: str
    target: str
    properties: Sequence[Property] = ()
    description: str | None = None
    annotations: Sequence[Annotation] = ()

    def __post_init__(self) -> None:
        _validate_name(self.name, kind="Edge")
        _validate_name(self.source, kind="Edge source")
        _validate_name(self.target, kind="Edge target")
        _validate_annotations(self.annotations)
        _validate_unique_property_names(self.properties, owner=f"Edge {self.name}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "source": self.source,
            "target": self.target,
            "properties": [property_.to_dict() for property_ in self.properties],
            "description": self.description,
            "annotations": [annotation.to_dict() for annotation in self.annotations],
        }

    @classmethod
    def from_dict(
        cls,
        data: Mapping[str, Any],
        *,
        templates: Mapping[str, AnnotationTemplate] | None = None,
    ) -> Self:
        return cls(
            name=_required_str(data, "name"),
            source=_required_str(data, "source"),
            target=_required_str(data, "target"),
            properties=tuple(
                Property.from_dict(item, templates=templates) for item in _optional_mappings(data, "properties")
            ),
            description=_optional_str(data, "description"),
            annotations=_optional_annotations(data, templates=templates),
        )


@dataclass(frozen=True, slots=True)
class Topology:
    """A complete, validated, source-independent graph topology."""

    name: str
    nodes: Sequence[NodeType]
    edges: Sequence[EdgeType]
    description: str | None = None
    annotation_templates: Sequence[AnnotationTemplate] = ()
    annotations: Sequence[Annotation] = ()
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _validate_name(self.name, kind="Topology")
        _validate_annotations(self.annotations)
        templates_by_id: dict[str, AnnotationTemplate] = {}
        for template in (*self.annotation_templates, *_referenced_templates(self.nodes, self.edges, self.annotations)):
            existing = templates_by_id.get(template.id)
            if existing is not None and existing != template:
                raise TopologyValidationError(f"Conflicting annotation template ID: {template.id!r}")
            templates_by_id[template.id] = template
        object.__setattr__(self, "annotation_templates", tuple(templates_by_id.values()))
        if self.schema_version != SCHEMA_VERSION:
            message = f"Unsupported topology schema version: {self.schema_version!r}"
            raise TopologyValidationError(message)
        _validate_unique_names(self.nodes, kind="Node")
        _validate_unique_names(self.edges, kind="Edge")
        node_names = {node.name for node in self.nodes}
        for edge in self.edges:
            if edge.source not in node_names or edge.target not in node_names:
                message = f"Edge {edge.name!r} references an undeclared node type."
                raise TopologyValidationError(message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "description": self.description,
            "annotation_templates": [template.to_dict() for template in self.annotation_templates],
            "annotations": [annotation.to_dict() for annotation in self.annotations],
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
        }

    def to_json(self, *, indent: int = 2) -> str:
        """Return the portable JSON representation of this topology."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True) + "\n"

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        annotation_templates = tuple(
            _annotation_template_from_dict(item) for item in _optional_mappings(data, "annotation_templates")
        )
        templates_by_id = {template.id: template for template in annotation_templates}
        return cls(
            schema_version=_required_str(data, "schema_version"),
            name=_required_str(data, "name"),
            description=_optional_str(data, "description"),
            annotation_templates=annotation_templates,
            annotations=_optional_annotations(data, templates=templates_by_id),
            nodes=tuple(
                NodeType.from_dict(item, templates=templates_by_id) for item in _optional_mappings(data, "nodes")
            ),
            edges=tuple(
                EdgeType.from_dict(item, templates=templates_by_id) for item in _optional_mappings(data, "edges")
            ),
        )

    @classmethod
    def from_json(cls, value: str) -> Self:
        """Load and validate a topology from its JSON representation."""
        try:
            data = json.loads(value)
        except json.JSONDecodeError as error:
            raise TopologyValidationError("Topology is not valid JSON.") from error
        if not isinstance(data, Mapping):
            raise TopologyValidationError("Topology JSON root must be an object.")
        return cls.from_dict(data)

    @classmethod
    def from_json_file(cls, path: str | Path) -> Self:
        """Load and validate a topology from a JSON file."""
        return cls.from_json(Path(path).read_text(encoding="utf-8"))


def _validate_unique_names(elements: Sequence[NodeType] | Sequence[EdgeType], *, kind: str) -> None:
    names = [element.name for element in elements]
    if len(names) != len(set(names)):
        raise TopologyValidationError(f"{kind} names must be unique.")


def _validate_unique_property_names(properties: Sequence[Property], *, owner: str) -> None:
    names = [property_.name for property_ in properties]
    if len(names) != len(set(names)):
        raise TopologyValidationError(f"{owner} property names must be unique.")


def _referenced_templates(
    nodes: Sequence[NodeType],
    edges: Sequence[EdgeType],
    topology_annotations: Sequence[Annotation],
) -> Sequence[AnnotationTemplate]:
    annotation_lists: list[Sequence[Annotation]] = [topology_annotations]
    for node in nodes:
        annotation_lists.extend((node.annotations, node.identifier.annotations))
        annotation_lists.extend(property_.annotations for property_ in node.properties)
    for edge in edges:
        annotation_lists.append(edge.annotations)
        annotation_lists.extend(property_.annotations for property_ in edge.properties)

    return tuple(
        annotation.ontology
        for annotations in annotation_lists
        for annotation in annotations
        if isinstance(annotation, OntologyTerm)
    )


def _required_mapping(data: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = data.get(key)
    if not isinstance(value, Mapping):
        raise TopologyValidationError(f"{key!r} must be an object.")
    return value


def _optional_mappings(data: Mapping[str, Any], key: str) -> Sequence[Mapping[str, Any]]:
    value = data.get(key, ())
    if not isinstance(value, Sequence) or isinstance(value, str):
        raise TopologyValidationError(f"{key!r} must be an array.")
    if not all(isinstance(item, Mapping) for item in value):
        raise TopologyValidationError(f"{key!r} must contain only objects.")
    return value


def _optional_annotations(
    data: Mapping[str, Any],
    *,
    templates: Mapping[str, AnnotationTemplate] | None = None,
) -> Sequence[Annotation]:
    """Return the annotation list, or an empty list when it is omitted."""
    return tuple(
        _annotation_from_dict(item, templates or {}) for item in _optional_mappings(data, "annotations")
    )


def _required_str(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise TopologyValidationError(f"{key!r} must be a non-empty string.")
    return value


def _optional_str(data: Mapping[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is not None and not isinstance(value, str):
        raise TopologyValidationError(f"{key!r} must be a string or null.")
    return value


def _optional_bool(data: Mapping[str, Any], key: str, *, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        raise TopologyValidationError(f"{key!r} must be a boolean.")
    return value
