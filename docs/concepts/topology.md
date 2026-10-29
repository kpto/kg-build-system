# Topology

Topology declares the graph's meaning: the node and edge types, their properties, their hierarchy and the direction of every relationship.

Input rows say which values exist. Topology says what those values are to a graph consumer. It reads no files and holds no data. It is the contract that every binding must satisfy and the declaration the build publishes alongside the graph.

## The problem: a row does not say what it means

A `unit_ref` column identifies a unit, but it does not tell a consumer that a site *has* that unit, or that the unit belongs to a site rather than to a survey.

Without a declaration, that meaning lives in a comment, a query or someone's memory. Topology moves it into the graph: a `SiteNode`, a `UnitNode`, and a `HAS_UNIT` edge whose source is the site and whose target is the unit.

## The model

You write topology as ordinary Python classes:

- A **node** is a thing: a site, a unit, a defect.
- An **edge** is a directed assertion between two nodes: a site *has* a unit, a unit *has* a defect.

Each declaration names the component, its properties and, for an edge, its two endpoints. The declaration stores no values. Values arrive later, in a [binding](bindings.md), when you assign an expression to every declared property.

```python
from kg_build_system import (
    Edge, EdgeLabel, EdgeOptions, Node, NodeLabel, NodeOptions,
    PropertySlot, property,
)


class SiteNode(Node):
    """A monitored site: a premises the estate maintains."""

    options = NodeOptions(annotations=(NodeLabel("Site"),))

    name: PropertySlot[str] = property()
    """The site's display name."""

    region: PropertySlot[str | None] = property()
    """Region the site belongs to, absent when the register omits it."""


class UnitNode(Node):
    """A piece of installed equipment held on the asset register."""

    options = NodeOptions(annotations=(NodeLabel("Unit"),))

    name: PropertySlot[str] = property()
    in_service: PropertySlot[bool] = property()


class DefectNode(Node):
    """A defect recorded against a unit."""

    options = NodeOptions(annotations=(NodeLabel("Defect"),))

    title: PropertySlot[str] = property()
    severity: PropertySlot[str | None] = property()


class HasUnitEdge(Edge[SiteNode, UnitNode]):
    """Relates a site to equipment installed at it."""

    options = EdgeOptions(annotations=(EdgeLabel("HAS_UNIT"),))

    as_at: PropertySlot[str | None] = property()


class HasDefectEdge(Edge[UnitNode, DefectNode]):
    """Relates a unit to a defect found on it."""

    options = EdgeOptions(annotations=(EdgeLabel("HAS_DEFECT"),))

    reported_on: PropertySlot[str | None] = property()
```

The type arguments of `Edge[Source, Target]` are the endpoints, in order. An edge is always directed, and the order is part of its meaning. `Edge[SiteNode, UnitNode]` reads *site has unit*, not *unit has site*.

## Properties

A `PropertySlot[T]` accepts a scalar graph value or a flat array of non-null scalars. Use `T | None` when the graph may hold no value:

| Declaration | Stores |
| --- | --- |
| `PropertySlot[str]` | A required string |
| `PropertySlot[str \| None]` | A string or no value |
| `PropertySlot[Array[str]]` | A required list of strings |
| `PropertySlot[Array[float] \| None]` | A list of floats or no list |

Arrays are one level deep and homogeneous. Null items inside an array are rejected; narrow the array and apply `drop_null_items()` before assigning it. An empty array differs from a missing array.

Nested arrays and structs are not graph properties. When a value is richer than a flat array, make it a node and connect it with an edge. Use [`extract()`](expressions.md) or [`alter_rows().expand()`](projections.md) to reach the scalar values a property accepts.

Nullability is a declaration, not a hint. A required property promises that a value will be present, and the build stops if the data breaks that promise. A nullable property accepts a null expression and stores no graph value. Every declared property, including inherited ones, must be bound; there are no defaults.

## Templates, categories and concrete components

A topology class has one of three roles:

| Base | Role | Receives records |
| --- | --- | --- |
| `NodeTemplate`, `EdgeTemplate` | Share property slots and annotations | No |
| `AbstractNode`, `AbstractEdge` | A graph-visible category parent | No |
| `Node`, `Edge` | A concrete component | Yes |

A template is an inert mixin. It never becomes a graph component, never receives a logical name, and cannot be a binding target or an endpoint. A category is a graph-visible parent: it carries shared properties and lets an edge name a whole family of nodes instead of one concrete component. A concrete component is the only thing a binding can target.

```python
from kg_build_system import (
    AbstractEdge, AbstractNode, Edge, Node, NodeTemplate, PropertySlot, property,
)


class ProvenancedNodeTemplate(NodeTemplate):
    """Every node records the feed version that produced it."""

    source_version: PropertySlot[str] = property()


class DocumentedAbstractNode(AbstractNode):
    """Category: every documented entity carries a human-readable summary."""

    summary: PropertySlot[str] = property()


class PlaceNode(ProvenancedNodeTemplate, DocumentedAbstractNode, Node):
    """A named location on the estate."""

    name: PropertySlot[str] = property()
```

Base order is normative: templates first, one abstract category parent in the middle, and the terminal base last. A declaration may mix in several templates of its own kind, but it has at most one direct category parent. A concrete component is terminal: you cannot subclass a class that is already a `Node` or an `Edge`.

A category is not a shortcut for a binding. It produces no records of its own; every record comes from a concrete component. Use a category when several components genuinely share meaning. Use a template when they only share property slots or annotations.

An abstract edge may declare category endpoints, and a concrete edge under it may keep or narrow them:

```python
from kg_build_system import AbstractEdge, Edge


class DocumentedRelationAbstractEdge(
    AbstractEdge[DocumentedAbstractNode, DocumentedAbstractNode]
):
    """Category: a relationship between documented entities."""


class PlaceAtEdge(DocumentedRelationAbstractEdge, Edge[PlaceNode, PlaceNode]):
    """Relates one place to another."""
```

A narrower endpoint must equal or descend from every abstract ancestor's endpoint. When a declared side is a category, a binding names the concrete node it uses with an [`endpoint(...)`](bindings.md#endpoint-tokens) token. Concrete declared sides need no token.

## Names, labels and descriptions

A component has three descriptions:

- The **logical name** is stable graph identity. It defaults to the class name with one tier suffix removed: `SiteNode` becomes `site`, `HasUnitEdge` becomes `has_unit`. An explicit `options.name` replaces the inference.
- The **label** is the target-native type mapping. `NodeLabel("Site")` becomes the target's node label, and `EdgeLabel("HAS_UNIT")` becomes its relationship type.
- The **description** is prose for a human. `options.description` wins; otherwise the class docstring is used.

A label is an [annotation](semantics.md), not a name. At most one label of the matching kind may be present. Labels and descriptions are own-only: a child does not inherit a category's label or description, and a category keeps its own entry. The logical name must be unique across nodes and edges.

Name the tier in the class name and let the suffix be stripped. This keeps the source readable while giving the graph a short, stable name.

## Edge or node?

Use an edge for an association that exists between two things and has no identity beyond the pair and the assertion. Use a node when the relationship is itself a thing that other relationships can point at.

Reify a relationship as a node when it has an identity the data already uses (a survey visit, an observation), carries properties other facts reference, participates in further relationships, or has its own lifecycle. Keep it as an edge when it is a named association whose properties describe that association: a score, an `as_at` date, the stage that asserted it.

Do not store an association as a node property. A `site_id` property on a unit is a scalar with no graph identity; it cannot be traversed and it duplicates the site's key. Declare a `HAS_UNIT` edge instead. Conversely, do not invent an edge for a plain attribute: a unit's name belongs on the unit.

Direction follows the sentence the edge expresses. If the reverse is a different assertion, declare a second edge type with the endpoints swapped.

## Cardinality and identity

Topology does not declare cardinality. Multiplicity is a property of the data and of the key you choose in the binding.

One row per ordered pair gives one edge per pair. If several assertions can exist between the same pair, give each assertion its own edge identity. A node key identifies one node within its component; an edge key identifies one relationship record. Choose the key that matches the source grain. The [modelling patterns](../how-to/patterns.md) guide collects the recurring choices.

## Limits

- Topology declares meaning and shape, never data or cardinality.
- Properties are scalars or flat, homogeneous arrays of non-null scalars. Anything richer is a node.
- Templates and categories never receive records.
- A concrete component is terminal and cannot be subclassed.
- Labels and descriptions are own-only; a child does not inherit its category's.

## What to remember

- A node is a thing; an edge is a directed assertion between two concrete nodes.
- Every declared property is required at binding time, and nullability is part of the declaration.
- Templates share slots, categories share graph meaning, and only concrete components receive records.
- Direction and identity are declarations; multiplicity comes from the key and the source grain.
- A label is target-native metadata, not the component's logical name.

## Next steps

- [Bindings](bindings.md) supply the rows and values behind these declarations.
- [Semantics and annotations](semantics.md) publish portable metadata alongside the topology.

## Reference

[Topology reference](../reference/topology.md) lists the declaration rules, property metadata, endpoint constraints and errors.
