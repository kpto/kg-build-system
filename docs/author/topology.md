---
title: Declare topology
summary: A node or edge states what a record is, which properties it carries, and for an edge which direction it points.
section: author
order: 60
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/distribution/languages/topology/model/public/declarations.py
  - reference_project/topology/common.py
  - reference_project/topology/site/__init__.py
  - docs/author/topology.md
subject: topology
perspective: guide
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Topology</span><a href="/subjects/topology">Overview</a><a href="/author/topology" class="active">Guide</a><a href="/spec/topology">Spec</a><a href="/reference/api">API</a><a href="/philosophy/meaning-first">Philosophy</a><a href="/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

> [!lede]
> Topology knows nothing about files. It declares node and edge types, their properties, their hierarchy and their direction. A binding later supplies the rows; the topology already states what the record means.

## What it is

| Declaration | Meaning |
| --- | --- |
| `Node` | A concrete, bindable record type. |
| `AbstractNode` | A graph-visible category; it produces no records and is never a binding target. |
| `Edge[Source, Target]` | A directed relation between two node types. |
| `AbstractEdge[...]` | A relationship family; a binding target is concrete. |
| `PropertySlot[T]` + `property()` | One declared property and its value type. |
| `NodeTemplate` / `EdgeTemplate` | Shared properties and annotations; inert, never graph components. |

Templates contribute slots. One abstract category may parent a concrete component. The base order is templates first, category next, terminal concrete component last. A concrete component is terminal: it cannot be inherited.

## Rules

- A concrete component must be a `Node` or `Edge`; it cannot inherit another concrete component.
- A component may have at most one abstract parent, and the parent must be the matching kind (node parent for a node, edge parent for an edge). Parents must be abstract and acyclic.
- Templates are inert. They add properties and annotations; they do not create a component or a key.
- An edge declares both endpoints and a direction. `Edge[SiteNode, UnitNode]` means site → unit, not the reverse.
- A property is a scalar or a flat, non-null array of scalars. Nested arrays, arrays of structs and bare structs are refused.
- A component name is unique across nodes and edges.
- A node or edge carries at most one matching label. A node label on an edge is refused.

## Example

```python
from kg_build_system import (
    Edge, EdgeLabel, EdgeOptions, Node, NodeLabel, NodeOptions,
    PropertySlot, property,
)

from reference_project.topology.common import (
    DocumentedAbstractNode, MonitoredRelationAbstractEdge,
    ProvenancedNodeTemplate, RecordedRelationEdgeTemplate,
)


class SiteNode(ProvenancedNodeTemplate, DocumentedAbstractNode, Node):
    """A monitored site: a premises the estate maintains."""

    options = NodeOptions(annotations=(NodeLabel("Site"),))

    name: PropertySlot[str] = property()
    city: PropertySlot[str] = property()


class UnitNode(ProvenancedNodeTemplate, DocumentedAbstractNode, Node):
    """A piece of installed equipment held on the asset register."""

    options = NodeOptions(annotations=(NodeLabel("Unit"),))

    name: PropertySlot[str] = property()
    in_service: PropertySlot[bool] = property()


class HasUnitEdge(
    RecordedRelationEdgeTemplate, MonitoredRelationAbstractEdge, Edge[SiteNode, UnitNode]
):
    """Relates a site to equipment installed at it."""

    options = EdgeOptions(annotations=(EdgeLabel("HAS_UNIT"),))
```

The direction lives in the generic parameters, not in a property.

## Limits

- An abstract category is graph-visible but produces no records. It exists to share semantics and to let an edge declare a family endpoint.
- A template cannot declare identity, a key or a binding.
- A property cannot hold a nested object. Reify the nested value as nodes and edges, or as a flat scalar if the meaning is genuinely flat.
- A component that mixes node and edge lineage, or inherits a concrete component, is refused.
- Two concrete components in different families may share a property name; they do not share a slot.

## Next

[Bind records](/author/bindings) — map one row context onto one concrete node or edge.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-027 | Support polymorphic categories/templates with one normative base order. | 2026-09-01 | accepted | `docs/reference/topology.md#base-order` |
| D-028 | Require an `endpoint(...)` token only when the declared edge side is abstract. | 2026-09-01 | accepted | `docs/reference/topology.md#endpoint` |
| D-029 | Restrict graph properties to scalars or flat arrays of non-null scalars, and type SQL output by the property type. | 2026-10-22 | accepted | `docs/reference/types.md#graph-property-shape` |
