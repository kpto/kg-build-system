# Topology

Topology is the part of a build that knows nothing about files. It declares
what kinds of things exist in the graph, what each thing is called, which
properties it carries, and how those things relate to each other.

You write topology as ordinary Python classes:

- a **node** is a thing: a site, a unit, a defect;
- an **edge** is a directed relationship between two nodes: a site *has* a
  unit, a unit *has* a defect.

The declaration fixes meaning and shape. It stores no data. Values arrive
later, in a [binding](bindings.md), when you assign an expression to every
declared property.

## A first node and edge

```python
from kg_build_system import (
    Edge, EdgeLabel, EdgeOptions, Node, NodeLabel, NodeOptions,
    PropertySlot, property,
)
from kg_build_system.types import Timestamp


class SiteNode(Node):
    """A monitored site: a premises the estate maintains."""

    options = NodeOptions(annotations=(NodeLabel("Site"),))

    name: PropertySlot[str] = property()
    """The site's display name."""

    city: PropertySlot[str | None] = property()
    """City the premises is located in, absent when the register omits it."""


class UnitNode(Node):
    """A piece of installed equipment held on the asset register."""

    options = NodeOptions(annotations=(NodeLabel("Unit"),))

    name: PropertySlot[str] = property()
    """The equipment name as the register records it."""

    in_service: PropertySlot[bool] = property()
    """True while the equipment is in service."""


class HasUnitEdge(Edge[SiteNode, UnitNode]):
    """Relates a site to equipment installed at it."""

    options = EdgeOptions(annotations=(EdgeLabel("HAS_UNIT"),))

    installed_on: PropertySlot[Timestamp | None] = property()
    """Date the equipment was installed, absent when the register omits it."""
```

The type arguments of `Edge[Source, Target]` are the endpoints, in order. The
source is the first argument and the target is the second. An edge is always
directed; the order is part of its meaning, not a display detail.

A topology class is also the object you instantiate in a binding to assign
property expressions, such as
`UnitNode(name=row.unit_name.alter_rows().drop_null(), ...)`. Every declared
property, including inherited ones, must be assigned. There are no defaults and
no optional properties on a declaration; a property is either nullable in its
type or required.

## Scalar and array properties

A `PropertySlot[T]` accepts a scalar graph value or a flat array of non-null
scalars. Use `T | None` when the graph may hold no value:

| Declaration | Meaning |
| --- | --- |
| `PropertySlot[str]` | Required string |
| `PropertySlot[str \| None]` | String or no value |
| `PropertySlot[Timestamp]` | Required timestamp |
| `PropertySlot[Array[str]]` | Required list of strings |
| `PropertySlot[Array[float] \| None]` | List of floats or no list |

Scalars are booleans, integers, floats, strings, `Date`, `Time`, `Timestamp`,
`Uuid`, and custom scalar types. Arrays are one level deep and homogeneous.
Nested arrays and structs are not graph properties; use
[`extract()`](expressions.md) or [`alter_rows().expand()`](projections.md) to
reach scalar values.

Null items inside an array are rejected. When the source gives you
`Array[T | None]`, narrow the array to a present selection and apply
[`drop_null_items()`](expressions.md) before assigning it. An empty array
differs from a missing array.

Nullability is a declaration, not a hint. A required property promises that a
value will be present; the build stops if the data breaks that promise. A
nullable property accepts a null expression, and the null is stored as an
absent graph value. The [bindings](bindings.md) page explains the two ways to
turn a nullable selection into a value the graph can use.

## Property metadata

`property()` accepts `name`, `description` and `annotations`. A plain docstring
immediately below the assignment is the usual form. The framework reads that
source line when the class is created, so keep the declaration in an ordinary
importable module:

```python
name: PropertySlot[str] = property()
"""The site's display name."""
```

The external property name defaults to the attribute name in snake case. One
trailing underscore is reserved as an escape for a Python collision:
`options_` becomes the external name `options`. Two properties on one
component may not share an external name. A property description belongs to
the declaring class and travels with the property through inheritance.

## Templates, categories and concrete components

There are three tiers. They differ in what they contribute to the graph and
whether a binding may target them.

| Base | Purpose | Graph-visible | Bindable |
| --- | --- | --- | --- |
| `NodeTemplate`, `EdgeTemplate` | Share properties and annotations | No | No |
| `AbstractNode`, `AbstractEdge[S, D]` | Category parent and endpoint category | Yes | No |
| `Node`, `Edge[S, D]` | Concrete component | Yes | Yes |

A declaration chooses one tier by its bases. Concrete components are terminal:
you cannot subclass a class that is already a `Node` or `Edge`.

### Templates

A template is an inert mixin. It shares property slots and annotation flow but
never becomes a graph component, never receives a logical name, and may not be
a binding target or an endpoint category.

```python
from kg_build_system import Node, NodeOptionsTemplate, NodeTemplate, PropertySlot, property

class ProvenancedNodeTemplate(NodeTemplate):
    """Every node records the feed version that produced it."""

    options = NodeOptionsTemplate()
    source_version: PropertySlot[str] = property()
    """The data release the node's facts were built from."""

class MeterNode(ProvenancedNodeTemplate, Node):
    """One metering point on the estate."""

    name: PropertySlot[str] = property()
```

Templates declare annotations with `NodeOptionsTemplate(annotations=...)` or
`EdgeOptionsTemplate(annotations=...)`. Those are annotations-only; a template
has no name or description of its own.

A declaration may mix in any number of templates of its own kind. Canonical
order is templates first, the abstract category parent in the middle, and the
terminal base last: `ProvenancedNodeTemplate, DocumentedAbstractNode, Node`.
Mixing node-side and edge-side lineage is rejected at class creation.

Keep one property slot per name. If two concerns need a slot called `as_at`,
but at different types, make them sibling templates and mix the one that
matches; redeclaring an inherited slot at another type is a static type error.

### Categories

An abstract component is a graph-visible parent. It carries shared properties,
gives its children a common parent, and lets an edge name a whole category
instead of one concrete component. It is never a binding target and produces no
records of its own.

```python
from kg_build_system import (
    AbstractNode, Node, NodeLabel, NodeOptions, PropertySlot, property,
)

class DocumentedAbstractNode(AbstractNode):
    """Category: every documented entity carries a human-readable summary."""

    options = NodeOptions(annotations=(NodeLabel("Documented"),))
    summary: PropertySlot[str] = property()
    """A one-line human-readable rendering of the entity."""

class PlaceNode(DocumentedAbstractNode, Node):
    """A named location on the estate."""

    options = NodeOptions(annotations=(NodeLabel("Place"),))
    name: PropertySlot[str] = property()

class AssetNode(DocumentedAbstractNode, Node):
    """A maintained object held on the asset register."""

    options = NodeOptions(annotations=(NodeLabel("Asset"),))
    name: PropertySlot[str] = property()
```

Each declaration has at most one direct category parent. Multiple parents of
the same kind are rejected, as is a non-framework base class. A category's own
options stay on the category; a child does not inherit its description or its
label. Categories may chain, and a concrete component records its nearest
parent.

## Edge endpoints and inheritance

An abstract edge may declare category endpoints. A concrete edge under it may
keep those endpoints or narrow them:

```python
from kg_build_system import AbstractEdge, Edge, EdgeLabel, EdgeOptions

class MonitoredRelationAbstractEdge(
    AbstractEdge[DocumentedAbstractNode, DocumentedAbstractNode]
):
    """Category: a relationship asserted by the monitored estate data."""

    options = EdgeOptions(annotations=(EdgeLabel("MONITORED"),))


class AssetAtEdge(MonitoredRelationAbstractEdge, Edge[AssetNode, PlaceNode]):
    """Relates an asset to the place that holds it."""

    options = EdgeOptions(annotations=(EdgeLabel("ASSET_AT"),))
```

A narrower endpoint must equal or descend from every abstract edge ancestor's
endpoint. Widening is rejected when the class is created. A concrete edge may
also name no endpoints and inherit its parent's pair, as in
`class UnnarrowedAssetAtEdge(MonitoredRelationAbstractEdge, Edge)`. Endpoints
must be declared node components, abstract or concrete; a node template, edge,
or plain Python class cannot be an endpoint.

When a declared side is a category, a binding must name the concrete component
it uses for that side with an [`endpoint(...)`](bindings.md#endpoint-tokens)
token. Concrete declared sides need no token. Prefer concrete endpoints when
the target must understand a fixed pair; declare a category only when the
relationship is genuinely shared across several node types.

## Labels, names and descriptions

A component has a logical name (`options.name` or the class name), a label
(`NodeLabel(...)` or `EdgeLabel(...)`), and a description (`options.description`
or the class docstring). The name is stable graph identity; the label is
target-native type mapping; the description is prose.

A label is an [annotation](annotations.md), not a name. A node label becomes the
target's node label and an edge label its relationship type. At most one label
of the matching kind may be present across the effective annotations. A
template may contribute one, but then the concrete declaration must not add
another.

Labels are not inherited from a category: `PlaceNode` declares its own `Place`
label, while `DocumentedAbstractNode` keeps `Documented` for the category
entry. A child is not automatically labelled as its parent.

The description is own-only too. `options.description` wins; otherwise the
class docstring is used; an inherited description is never copied down. Write a
description for what the component means in the graph.

Logical names default to the class name with one tier suffix removed:
`SiteNode` → `site`, `HasUnitEdge` → `has_unit`, `DocumentedAbstractNode` →
`documented`. An explicit `options.name` replaces the inference completely.
Component names must be unique across nodes and edges, so name the tier in the
class name and let the suffix be stripped.

## Edge or node?

Use an edge for an association that exists between two things and has no
identity of its own beyond the pair and the assertion. Use a node when the
relation is itself a thing that other relations can point at.

Reify a relationship as a node when it has an identity the data already uses
(a survey visit, an observation), carries properties other facts reference,
participates in further relationships, or has its own lifecycle. Keep it as an
edge when it is a named association whose properties describe that
association: a score, an `as_at` date, the stage that asserted it.

Do not store an association as a node property. A `site_id` property on a unit
is a scalar with no graph identity; it cannot be traversed and it duplicates
the site's key. Declare a `HAS_UNIT` edge instead. Conversely, do not invent an
edge for a plain attribute: a unit's name belongs on the unit.

Direction follows the sentence the edge expresses. `Edge[SiteNode, UnitNode]`
with the label `HAS_UNIT` reads *site has unit*. If the reverse is a different
assertion, declare a second edge type with the endpoints swapped.

Topology does not declare cardinality. Multiplicity is a property of the data
and of the key you choose in the binding: one row per ordered pair gives one
edge per pair, while several assertions between the same pair need their own
edge identity. A node key identifies one node within its component; an edge
key identifies one relationship record. Choose the key that matches the
source grain. The [modelling patterns](../guides/patterns.md) guide collects
the recurring choices.

!!! note "A category is not a shortcut for a binding"
    Abstract components and templates exist to share meaning. They never
    receive rows. Every record comes from a concrete component targeted by a
    binding.

## What to remember

- Topology declares meaning and shape, never data.
- A node is a thing; an edge is a directed assertion between two concrete
  nodes.
- Properties are scalars or flat non-null arrays. Anything richer is a node.
- Categories and templates share meaning and never receive rows.
- Direction and identity are declarations; multiplicity comes from the key and
  the source grain.

Next: [Bindings](bindings.md) supplies the rows and values behind these
declarations.
