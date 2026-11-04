# Semantics and annotations

A build carries its meaning as data: descriptions explain a component to people, labels name it for targets, and annotations record facts a tool can act on.

When you declare a node, edge, property or binding, you state more than a shape. You state what a record means, what a consumer may conclude from it, and which facts downstream tooling needs. kg-build-system compiles those statements into the blueprint and publishes them with the build, so a consumer can read the meaning without reading your pipeline.

## Why meaning is delivered as data

A comment in Python is invisible to the graph consumer. A label added by a loader can drift from the declaration it describes. Here the declaration is the source, and the build delivers the result:

- the blueprint carries every annotation on every reached declaration;
- `meta_graph.json` describes the effective topology in readable form;
- the Neo4j bundle uses the effective labels and relationship types.

This makes meaning part of the build artifact, not a convention around it. The same declarations that produce records also produce the description of those records, and a change to either is visible in the build.

## What you can state

| Channel | Answers | Written as | Where a consumer reads it |
| --- | --- | --- | --- |
| Description | What does this component mean to a person? | class docstring or `description=` | `meta_graph.json` |
| Label | What is this component called in a target? | `NodeLabel` or `EdgeLabel` | `meta_graph.json` and the Neo4j bundle |
| Annotation | What fact should a tool read? | a frozen `Annotation` subclass | the blueprint |

Descriptions and annotations are independent. A description never becomes an annotation, and a custom annotation does not appear in the meta-graph unless a planner or executor interprets it. A label is an annotation with a framework-defined meaning.

## A node with all three

The survey build has a site table and a `SiteNode`. The declaration below gives the node a human description, a target label and a tool-readable provenance fact.

```python
from dataclasses import dataclass

from kg_build_system import (
    Annotation, Node, NodeLabel, NodeOptions, PropertySlot, property,
)


@dataclass(frozen=True)
class Provenance(Annotation):
    """The build stage that owns a component's facts."""

    namespace = "reference_project"
    annotation_id = "provenance"

    stage: str


class SiteNode(Node):
    """A surveyed location in the estate."""

    options = NodeOptions(
        annotations=(NodeLabel("Site"), Provenance(stage="survey")),
    )

    site_id: PropertySlot[str] = property()
    """The stable identifier from the survey feed."""

    name: PropertySlot[str | None] = property(
        description="The display name, when the feed supplies one.",
    )


class UnitNode(Node):
    """A surveyed unit within a site."""

    options = NodeOptions(annotations=(NodeLabel("Unit"),))

    asset_tag: PropertySlot[str] = property()
```

`SiteNode` states three different things. Its docstring explains the node to a reader. `NodeLabel("Site")` says that a target such as Neo4j should call it `Site` instead of the default logical name `site`. `Provenance(stage="survey")` records a fact that a downstream tool can match and read. `UnitNode` is the other endpoint used in the label example below.

## Descriptions

A component takes its description from `options.description` when you set it, and otherwise from its own class docstring. The explicit option wins. The description is local: a concrete node with neither its own option nor its own docstring has no description, even when its category parent is documented. The same rule applies to tables, structs, table groups and projections.

A property or field follows the same pattern. Write the description as an argument, or as a string directly below the assignment:

```python
class ReadingNode(Node):
    recorded_on: PropertySlot[str] = property(
        description="The instant the reading was taken.",
    )
```

`computed_field` reads the same string form. A projection field declared that way follows the same rule, and an explicit `description=` always wins. A property description belongs to the declaration that writes the slot; a subclass that inherits the property keeps that description.

!!! note "Attribute docstrings need readable source"

    A description written below a field or property assignment is recovered when the class is created. If the source cannot be read, for example when the class was built from a string or entered in a REPL, the string yields no description. The `description=` argument always works.

A binding has no description. `debug_name` names it in the meta-graph, and annotations record facts about it.

## Labels

`NodeLabel` and `EdgeLabel` are ordinary annotations with a framework-defined namespace and identifier. They override the component's semantic label:

```python
from kg_build_system import Edge, EdgeLabel, EdgeOptions


class HasUnitEdge(Edge[SiteNode, UnitNode]):
    options = EdgeOptions(annotations=(EdgeLabel("HAS_UNIT"),))
```

Without a label, a component's label is its logical name. `SiteNode` defaults to `site`; `HasUnitEdge` defaults to `has_unit`. Labels are target-neutral: Neo4j writes a node label as `:LABEL` and an edge label as `:TYPE`. A label belongs to the declaration that writes it; a category parent's label does not flow to a child, while a template's label follows the template annotation flow described below.

!!! warning "One label per component"

    A component may carry at most one label of its matching kind in its effective annotations. A label of the wrong kind is invalid for that component, and a target that reads labels rejects it. Neo4j has one node label and one relationship type, so a second label has no single spelling there.

## Annotations

An annotation is a frozen dataclass with a stable namespace, a stable identifier and a JSON-compatible payload. Its class is a declaration of the fact; an instance carries the values.

Attach an annotation through the options of any declaration that accepts them, or through a field or property helper. The blueprint stores only the namespace, the identifier and the payload. It never stores the annotation class itself. A downstream planner or executor matches on namespace and identifier and reads the payload; an annotation it does not recognise is preserved and ignored.

An annotation has no owner field. The attachment on the declaration says what it belongs to, and the rules that read it live in functions and planners beside the data.

!!! note "A planner or executor decides what an annotation means"

    The framework has no central annotation policy. A planner or executor may interpret the annotations it supports, such as a label, and ignore the rest. Putting a fact in an annotation does not change the graph by itself.

## How annotations flow

Mixing a template into a component adds the template's annotations to that component. Each template contributes its own frozen tuple once, base template before derived, followed by the component's own `options.annotations`. The template is not a graph component and does not enter the blueprint. A category parent's own annotations stay on the parent; they are not copied down to its children.

When you compile, every reached declaration contributes its annotations to the blueprint, including bindings and assets. Only declarations the build reaches are published: the tables and projections a binding reads, the components a binding targets and their ancestors and endpoints, the structs those types use, and the assets those tables name. An annotation on an unrelated declaration is valid Python but no consumer can reach it.

## What consumers see

- **The blueprint** carries every annotation on every reached declaration, with its namespace and payload. Read it when a tool needs to act.
- **`meta_graph.json`** carries labels, descriptions, properties with logical types and descriptions, record counts and example values. Read it when a person or a catalogue needs to explain the graph.
- **The Neo4j bundle** carries the effective node labels and relationship types. The target translates the target-neutral label into its own vocabulary.

!!! note "What the meta-graph guarantees"

    Record counts are exact for the records that reached the executor, so they reflect the last stage that owned those records. Example values are illustrative: the executor uses `approx_top_k`, bounded by `example_limit`, and the document names that method. An abstract category carries inclusive counts and pooled examples from its descendants because it emits no records of its own.

## Limits

- A component description is local prose. It is not inherited from a category parent, and it is not created from an annotation.
- An annotation is frozen data, not behaviour. It cannot read the graph, resolve a reference or change a record without a planner or executor that interprets it.
- The payload must be JSON-compatible and stable because it is part of the
  blueprint. Keep it small, and do not encode the owner, the component name or
  the binding name; the attachment already says what it belongs to.
- Only annotations on reached declarations are published. An annotation elsewhere
  in the module is not delivered.
- One component carries at most one matching label. Labels of the wrong kind fail
  when a target reads them.
- An annotation or description on a reached declaration changes the blueprint
  even when it does not change the workflow plan.

## Next steps

- [Planners and executors](planners-and-executors.md) explains how a build stage can read and act on what a declaration publishes.
- [Compile, execute and outputs](build-and-outputs.md) follows the blueprint, workflow plan and output files.

## Reference

- [Semantics reference](../reference/semantics.md) lists the annotation types, attachment points, description rules and meta-graph fields.
