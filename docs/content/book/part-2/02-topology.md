---
title: "5. Topology"
summary: "A record is designed before a row supplies it; topology states the node, edge, property and category."
section: book
perspective: book
part: II
chapter: 5
order: 22
status: normative
verified: 2026-11-15
sources:
  - docs/content/book/part-2/02-topology.md
  - docs/content/appendix/reference/topology.md
  - docs/content/appendix/spec/topology.md
---

## A record exists before a row

Ask what a site is in an estate graph. The source answers with columns: `site_id`, `site_name`, `premises`, `priority_scores`. That answer is about a file, not about a site. A site is a thing the graph asserts, with a name, a summary and a place in a hierarchy of assets. If the column list defines the record, the source owns the model, and every schema change becomes a change of meaning.

Topology reverses that order. A `Node` subclass declares a kind of record before any row exists. It names the component, the properties the record carries, and, for an edge, the two node kinds the relation connects. A binding supplies the rows later. The separation is the whole point: the design can be reviewed as a design, and the mapping can be reviewed as a mapping.

The estate example carries through this chapter. Sites hold units. A `SiteNode` is a place; a `UnitNode` is installed equipment; `HasUnitEdge` is the assertion that a site holds a unit. None of those declarations reads a relation. The equipment relation can change its fields without changing what a site is.

## Two component kinds, one direction

A concrete node is declared as a `Node` subclass. A concrete edge is declared as `Edge[Source, Target]`. The two type arguments are node-side declarations: sites and units, not source relations and derived relations. The order is the direction. `Edge[SiteNode, UnitNode]` means site to unit. It does not mean the reverse, and it is not a symmetric association.

```python
from kg_build_system import (
    AbstractNode, Edge, EdgeLabel, EdgeOptions, Node, NodeLabel,
    NodeOptions, PropertySlot, property,
)


class AssetNode(AbstractNode):
    """A category: everything the estate records as an asset."""

    options = NodeOptions(annotations=(NodeLabel("Asset"),))
    summary: PropertySlot[str] = property()
    """One line describing the asset."""


class SiteNode(AssetNode, Node):
    """A monitored site: premises the estate maintains."""

    options = NodeOptions(annotations=(NodeLabel("Site"),))
    name: PropertySlot[str] = property()
    """The site's display name."""


class UnitNode(AssetNode, Node):
    """Installed equipment held on the asset register."""

    options = NodeOptions(annotations=(NodeLabel("Unit"),))
    name: PropertySlot[str] = property()
    """The equipment name as the register records it."""

    in_service: PropertySlot[bool] = property()
    """True while the equipment is in service."""

    survey_period: PropertySlot[str | None] = property()
    """The period the register last reviewed the equipment, when recorded."""


class HasUnitEdge(Edge[SiteNode, UnitNode]):
    """A site holds a unit."""

    options = EdgeOptions(annotations=(EdgeLabel("HAS_UNIT"),))
    as_at: PropertySlot[str] = property()
    """The period the relation is asserted as at."""
```

Direction belongs in the type arguments because it must be checkable before values arrive. If direction were a property, two rows of the same edge could disagree about which endpoint is the source, and no declaration-time check could catch it. A relation that genuinely points both ways is two edges with two meanings, or one edge whose meaning is symmetric. The graph states which.

Concrete components are terminal. A class declared as a `Node` or `Edge` cannot be subclassed. This is restrictive on purpose: if one concrete record could inherit another, "what this record is" would have more than one answer, and a binding target would be ambiguous. Sharing belongs in categories and templates, which exist for that job.

## A property is a stored scalar, not a subtree

A property is declared with `PropertySlot[T]` and assigned `property()`. The accepted value shapes are narrow: a scalar, an optional scalar, a flat array of non-null scalars, or an optional flat array. A nested array, an array of structs and a bare struct are refused.

The restriction follows from what a graph property is. It is a value stored on one record, not a shape embedded in the graph. A contact block with a name, an email and a nested location is a structure with its own identity and its own evidence; flattening it into a property hides that. Reify it as nodes and edges, or flatten it only when the meaning is genuinely one flat value. The refusal is a design prompt, not a storage limitation.

Nullability is part of the declaration. `survey_period: PropertySlot[str | None]` says a unit may have no recorded review period. `name: PropertySlot[str]` says a name is required. The binding must respect that distinction: a required property needs a present selection, while an optional property accepts a nullable one. Declaring every property as optional and filling absences with empty strings moves a design decision into the data, where it cannot be reviewed.

Topology also declares no cardinality. How many units a site holds, and whether a unit belongs to one site or several, is not a property of the node or edge class. Multiplicity comes from the binding key and the grain of the row source. A graph model that tried to state cardinality at the type level would need a second language for constraints; the key and the rows state it instead.

## Categories state meaning; templates share structure

`AbstractNode` and `AbstractEdge` declare categories. A category is graph-visible: it appears in the hierarchy, can be an edge endpoint, and carries properties and annotations. It produces no records of its own and is never a binding target. `AssetNode` above is a category: every asset has a summary, and an edge can declare that it connects assets without naming every concrete kind.

`NodeTemplate` and `EdgeTemplate` are a different mechanism. A template shares property slots and annotations with its host, but it never becomes a graph component. It has no logical name, no key, no binding target and no blueprint entry. A template that records the data release a node was built from is structure reused across components; it is not a claim that those components form a family.

Keeping the two apart prevents a data shortcut from becoming design. A category is a statement that a family of records shares meaning. A template is a statement that several declarations share slots. If a template were allowed to become a component, reuse would silently create a type; if a category were used as a mixin for convenience, a family would be invented to avoid repeating a property.

The base order states the hierarchy directly:

```python
class MeterNode(ProvenancedNodeTemplate, DocumentedAbstractNode, Node):
    ...
```

Templates come first, the one abstract category parent sits in the middle, and the terminal concrete base comes last. A component may have at most one abstract parent, and the parent must match its kind. A category may itself have a category parent, so a chain is possible; a concrete component may not inherit another concrete component.

Only reached categories enter the blueprint. A category is reached when a bound concrete component names it as an ancestor, or when a bound edge declares it as an endpoint. A category with no bound descendant and no bound edge endpoint is valid Python but is not published, because nothing in the graph can refer to it. The blueprint carries the graph the bindings actually populate, not every class the interpreter imported.

## Next

[6. Source and rows](/book/part-2/03-source-and-rows) — leave the design for a moment and look at the rows that will supply it.
