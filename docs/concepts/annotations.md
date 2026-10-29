# Annotations and descriptions

Authors document a build through two independent channels: **descriptions**,
prose for humans, and **annotations**, typed payloads for tools. Labels are
annotations with a fixed meaning: they name graph components in a target-neutral
way.

## Describing a component

A graph component takes its description from its own `description` option, or,
when that is absent, from the class docstring:

```python
from kg_build_system import Node, NodeLabel, NodeOptions, PropertySlot, property


class UnitNode(Node):
    """A monitored piece of equipment."""

    options = NodeOptions(annotations=(NodeLabel("Unit"),))

    asset_tag: PropertySlot[str] = property()
    """The estate feed's asset tag for the unit."""
```

`options.description` wins over the docstring. The description is never
inherited: a concrete node with neither its own option nor its own docstring has
no description, even when its category parent is documented. Tables, structs,
table groups and projections follow the same rule; see
[Data contracts](data-contracts.md) and [Projections](projections.md).

## Describing a property or field

Two spellings are equivalent for a topology property. The component example
above uses the string form; this one uses the argument:

```python
class ReadingNode(Node):
    recorded_on: PropertySlot[str] = property(
        description="The instant the reading was taken.",
    )
```

A property description comes from the argument, or from a string written
directly below the assignment; a field on a table or struct works the same way.
These attribute docstrings are recovered from the declaration's source when the
class is created. If the source cannot be read — for example when the class was
built from a string or typed into a REPL — the string yields no description; the
argument form always works.

`computed_field` reads the same string form, because it returns the same `Field`
descriptor: an explicit `description=` wins, otherwise a string written directly
below the assignment is used when the class is created. The source-reading
limitation is the same. See [Projections](projections.md).

## Declaring an annotation

An annotation is a frozen dataclass with a stable namespace and a stable
identifier. Its fields are its payload:

```python
from dataclasses import dataclass

from kg_build_system import Annotation


@dataclass(frozen=True)
class Provenance(Annotation):
    """Records which build stage produced or tracks a component."""

    namespace = "reference_project"
    annotation_id = "provenance"

    stage: str
```

Attach it through any declaration's options; the annotations table below lists
them all. Guidelines for a payload:

- keep it JSON-compatible and stable, because it is part of the blueprint and its
  fingerprint;
- do not encode the owner, the component name or the binding name — the
  attachment already says what it belongs to.

The blueprint stores only the namespace, the identifier and the frozen payload.
It never stores the annotation class. A downstream module matches on namespace
and identifier and reads the payload; an annotation it does not recognise is
preserved and ignored. All annotations are frozen values, and none of them know
what they are attached to.

## Labels

`NodeLabel` and `EdgeLabel` are ordinary annotations with a framework-defined
namespace and identifier. They override the component's semantic label:

```python
from kg_build_system import (
    Edge, EdgeLabel, EdgeOptions, Node, NodeLabel, NodeOptions,
)


class SiteNode(Node):
    options = NodeOptions(annotations=(NodeLabel("Site"),))


class HasUnitEdge(Edge[SiteNode, SiteNode]):
    options = EdgeOptions(annotations=(EdgeLabel("HAS_UNIT"),))
```

Without one, a component's label is its logical name; `SiteNode` defaults to `site`.

!!! warning "One label per component"

    At most one label of the matching kind may appear in the component's
    effective annotations. A label of the wrong kind is invalid for that
    component; a target that reads labels rejects it.

Labels are target-neutral; a target translates them. Neo4j writes a node label
as `:LABEL` and an edge label as `:TYPE`, so a node's label must be one label.

## Where annotations attach

| Declaration | Where |
| --- | --- |
| Table, struct, table group | that class's `options` |
| Field | `field(annotations=...)` |
| Projection | `ProjectionOptions(annotations=...)` |
| Projection field | `computed_field(annotations=...)` |
| Node or edge component | `NodeOptions` / `EdgeOptions` |
| Property | `property(annotations=...)` |
| Binding | `BindingOptions(annotations=...)` |
| Source binding | `SourceBindingOptions(annotations=...)` |

A binding has no description: `debug_name` names it, and annotations record it:

```python
from kg_build_system import (
    BindingOptions, Field, NodeValues, Table, field, node_binding,
)

class UnitTable(Table):
    asset_tag: Field[str] = field()


unit_binding = node_binding(
    target=UnitNode,
    rows=UnitTable.row_source(),
    bind=lambda row: NodeValues(
        build_key=row.asset_tag.alter_rows().drop_null(),
        properties=UnitNode(
            asset_tag=row.asset_tag.alter_rows().drop_null(),
        ),
    ),
    debug_name="unit_from_equipment",
    options=BindingOptions(
        annotations=(Provenance(stage="bound"),),
    ),
)
```

Binding annotations travel in the blueprint for downstream tooling.
`debug_name` is what appears in the meta-graph's binding entries and keeps
otherwise identical producers apart.

## Templates

A template shares property slots and annotations with every declaration that
mixes it in, but never enters the build itself. Its options carry annotations
only, because a template has no identity to name or describe:

```python
from kg_build_system import NodeTemplate, NodeOptionsTemplate, PropertySlot, property

class ProvenancedNodeTemplate(NodeTemplate):
    options = NodeOptionsTemplate(
        annotations=(Provenance(stage="built"),),
    )

    source_version: PropertySlot[str] = property()
    """The data release the node's facts were built from."""
```

Each template records its own annotations as one frozen tuple when it is
created. A host's effective annotations are those template tuples in C3 order —
each template once, base template before derived — followed by the host's own
`options.annotations`. The template itself is not a blueprint entry; only a
reached declaration carries the resulting tuple. A category parent's own
annotations are not copied down: labels and descriptions belong to the
declaration that writes them. Label uniqueness is checked against the complete
effective set, so a template cannot accidentally give a component two labels.

Canonical class order is templates, category parents, then the terminal base:

```python
from kg_build_system import AbstractNode

class AuditedTemplate(NodeTemplate):
    options = NodeOptionsTemplate(annotations=(Provenance(stage="audited"),))

class EquipmentNode(AbstractNode):
    options = NodeOptions(annotations=(NodeLabel("Equipment"),))

class RecordNode(AuditedTemplate, EquipmentNode, Node):
    """A recorded unit, tracked and provenanced."""
```

Here the category keeps its `Equipment` label on the category entry, the
template contributes the reusable annotation, and the concrete class takes its
own default label unless it declares one.

## What downstream consumers see

- **`meta_graph.json`** — labels, descriptions, properties with logical types
  and descriptions, counts and examples.
- **The blueprint** — every annotation on every declaration, with its namespace
  and payload.
- **The Neo4j bundle** — the effective node labels and relationship types.

Read annotations from the blueprint to act; descriptions from the meta-graph to
explain.

Only declarations the build reaches enter the blueprint: the tables and
projections read by a binding, the components a binding targets and their
ancestors and endpoints, the structs those types use, and the sources those
tables need. An annotation on an unrelated declaration is valid Python but is
not published, because no consumer can reach it.

## The amnesic rule

Annotations, like every domain model in the framework, are amnesic: frozen data
holding only its own facts. An annotation has no owner field and no behaviour
that needs the wider build. The attachment lives on the declaration; the rules
that read it live in functions and modules beside the data.

Put the fact in the payload, put the relationship in the declaration, and see
[Modules](modules.md) for how a module interprets what it recognises.

## What to remember

- Descriptions are prose for humans; annotations are typed payloads for tools.
- A docstring and `description=` are alternatives; the explicit option wins.
- Descriptions are not inherited.
- Annotations are frozen, JSON-compatible facts with no owner and no
  behaviour.
- Labels are the target-neutral way to name a graph component.

Next: [Modules](modules.md) explains how a build uses these declarations, and
[Compile and build](build.md) runs it.
