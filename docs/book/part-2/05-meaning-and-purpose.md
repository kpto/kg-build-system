---
title: "8. Meaning and purpose"
summary: "A graph publishes one purpose, contextless claims and framed limitations, so its meaning is part of the contract."
section: book
perspective: book
part: II
chapter: 8
order: 25
status: normative
verified: 2026-11-11
sources:
  - docs/book/part-2/05-meaning-and-purpose.md
  - docs/appendix/spec/meaning.md
  - docs/appendix/philosophy/semantic-hierarchy.md
---

## A graph can compile and still say nothing

A topology can be coherent, every binding can resolve, and the build can produce a clean blueprint while a reader still cannot answer the first question: what is this graph for? The node and edge declarations say what each record is. The bindings say which rows become which record. Neither says why the graph exists, what holds across all of it, or what a consumer must know before trusting a query.

Meaning is not a comment added after the build. It is a value language carried by the declarations themselves and published in the blueprint. A `Claim` states what holds regardless of use. A `Frame` scopes the conditions under which a statement applies. A `Limitation` states what a reader must know inside that scope. A `Purpose` states the one expected use of the graph. The framework stores those values where the author attached them and publishes them beside the topology, the data and the bindings.

The separation matters for the same reason the topology/binding separation matters. If meaning lived in a README, it would drift from the artifact. If it lived in docstrings, no consumer could read it. If every declaration carried its own purpose, the graph would have as many purposes as declarations, and a limitation would be true only in the scope of whoever wrote it.

## Three jobs: claim, frame, limitation

The unit vocabulary is small, and the restrictions between units are the design.

A `Claim` is contextless. It says something that holds regardless of purpose or frame. In the estate graph, "A site holds installed equipment" is a claim: it is true of the model, not only of one report. Claims attach at graph level or declaration level. They never attach under a frame.

A `Frame` scopes the limitation space. "Registered equipment only" is a frame. It does not assert a fact about the world; it names the boundary within which the following limitations are read.

A `Limitation` states what a reader must know given the purpose and the frame. "Unregistered equipment is absent" is a limitation. It belongs to the frame, never directly to a purpose and never to a declaration as a bare statement.

```text
GraphSemantics
  claims: Claim
  purpose: Purpose
             frames: Frame
                       limitations: Limitation

Semantics
  claims: Claim
  frames: Frame
            limitations: Limitation
```

The shape is enforced. A `Frame` owns only `Limitation` values. A `Purpose` owns only `Frame` values. `Semantics` needs at least one claim or frame. `GraphSemantics` requires a purpose and may have no claims. Every unit text is non-empty. Units are immutable and carry no key, owner or reference, so the attachment site is the only thing that says what a unit belongs to.

Why separate a claim from a limitation at all? Because they answer different questions. A claim is part of the model's assertion. A limitation is part of the model's honesty about its scope. Merging them into one "notes" field would let a reader mistake a caveat for a fact, or a fact for a caveat. The types keep the two readable.

## Purpose is the one context

A project declares zero or one `Graph`. `GraphOptions.semantics` is required and must be a `GraphSemantics` carrying exactly one `Purpose`. There is no second purpose and no declaration-level purpose.

The one-purpose rule is what makes a frame meaningful. A frame says "within this scope"; the purpose says what the scope is for. If two purposes existed, the same limitation could be true under one and false under the other, and a consumer would have no way to choose. One root means every lower frame is read under the same expected use.

```python
from kg_build_system import (
    Claim, Frame, Graph, GraphOptions, GraphSemantics, Limitation, Purpose,
)


class EstateGraph(Graph):
    options = GraphOptions(
        name="estate",
        description="Sites and the equipment installed at them.",
        semantics=GraphSemantics(
            claims=(Claim("A site holds installed equipment."),),
            purpose=Purpose(
                text="Estate asset management.",
                frames=(
                    Frame(
                        text="Registered estate only.",
                        limitations=(
                            Limitation("Unregistered equipment is absent."),
                        ),
                    ),
                ),
            ),
        ),
    )
```

`GraphOptions` also carries a name and a description. The name defaults to the class name in snake case. The description is prose; it is not a claim. A `Graph` is not a node, an edge or an asset, and it participates in no references. It is the project's statement of purpose, not another component in the topology.

Two graph declarations are refused. The refusal is not a namespace convenience. Two purposes would make the meaning root ambiguous, and every declaration fragment would inherit that ambiguity. A project that needs a second purpose needs a separate graph build, not a second declaration in the same project.

## A declaration attaches a fragment

A declaration attaches `Semantics`, never `GraphSemantics`. The graph meaning root belongs to the graph declaration alone. Passing a `GraphSemantics` to `NodeOptions`, `property()`, a table option, a field or a binding raises a type error naming the rule.

A `Semantics` fragment carries claims and frames but no purpose. Its frames are read under the one graph purpose. This keeps a node from claiming its own context while still letting the node state its local meaning and its local limits.

| Declaration | Attachment |
| --- | --- |
| Asset | `AssetOptions(semantics=...)` |
| Table, struct, projection | `TableOptions`, `StructOptions`, `ProjectionOptions` |
| Field | `field(semantics=...)` |
| Computed field | `computed_field(semantics=...)` |
| Node or edge | `NodeOptions(semantics=...)`, `EdgeOptions(semantics=...)` |
| Property | `property(semantics=...)` |
| Binding | `node_binding(..., semantics=...)`, `edge_binding(..., semantics=...)`, or `BindingOptions(semantics=...)` |

A `TableGroupOptions` carries no fragment, because a table group is a catalogue rather than a blueprint part. A binding carries one fragment for the whole mapping; there are no per-property binding semantics. A binding also has no description, so `debug_name` is its human handle and annotations are its metadata.

```python
from kg_build_system import (
    Frame, Limitation, Node, NodeLabel, NodeOptions, PropertySlot, Semantics,
    property,
)


class SiteNode(Node):
    options = NodeOptions(
        annotations=(NodeLabel("Site"),),
        semantics=Semantics(
            frames=(
                Frame(
                    text="The register as published.",
                    limitations=(Limitation("Closed sites are absent."),),
                ),
            ),
        ),
    )

    name: PropertySlot[str] = property()
    """The site's display name."""

    summary: PropertySlot[str] = property()
    """One line describing the site."""
```

The fragment above does not repeat "estate asset management". It states the local reading: this component is the published register, and closed sites are outside it. A reader supplies the purpose from the graph declaration and reads the node under it.

## Meaning is read downward, not copied

The semantic hierarchy is a reading order:

1. The graph purpose and its claims.
2. The category and template meaning that topology shares.
3. The concrete node or edge meaning.
4. The data declarations that supply the record.
5. The binding that maps rows onto it.

A lower fragment inherits an obligation, not text. It must be consistent with the purpose above it. The framework does not copy the parent's words into the child, and it does not check consistency. A syntactically valid fragment can still contradict the purpose; review catches that.

Structural inheritance is a separate matter. A category's label and description stay local; they do not flow to a concrete child. A template's annotations do flow, because a template is a structural mixin. A category's semantics is its own attachment and stays there. Do not assume one rule covers both mechanisms.

The practical consequence is that you attach the statement where it is true. A limitation about a binding's coverage belongs on the binding. A limitation about what a node kind excludes belongs on the node. A claim that holds across the graph belongs on `GraphSemantics`. Putting every statement at the root makes the root unreadable; putting every statement on declarations loses the one purpose that makes the frames comparable.

This is why a binding's semantics describes the mapping, not the record. "One row per site in the register" is a claim about the binding. "A site holds installed equipment" is a claim about the model. Moving the second onto the binding would make the mapping responsible for the node's meaning, which is exactly the design leak the seam prevents.

## The blueprint publishes what the author attached

The blueprint is the semantic model of the graph, not a snapshot of the Python declarations. It carries the graph declaration, the topology, the data declarations, the assets and the bindings, together with the semantics attached to each.

The graph declaration is the optional fifth field, `graph_declaration`. It carries the `GraphSemantics` value, including the purpose. When a project declares no `Graph`, the field is `None`. A declaration fragment is published on the DTO of the declaration it was attached to, not copied into a separate meaning index.

Publication is not interpretation. The blueprint does not evaluate truth, resolve claims against each other, revise them, or check cross-unit consistency. It publishes authored units so a consumer can compose them: a documentation renderer can print the purpose, a review tool can list limitations, a downstream service can refuse to answer a question outside a frame. The framework's job ends at carrying the values faithfully.

Only reached declarations are published. A `Semantics` fragment on a table that no binding reads, or on a node no binding targets, is valid Python but not part of the delivered model. Meaning follows the same reachability rule as topology and data: the blueprint describes the graph the bindings populate.

When a blueprint writes back to authoring source, the graph declaration renders first. That order is the reading order made visible: purpose, then topology, data and bindings. A round trip that lost the graph declaration would lose the root of every frame.

## Zero graph declarations is legal and rootless

A project may declare no `Graph` at all. The graph language is optional; topology, data, assets and bindings compile without a purpose. The blueprint publishes `graph_declaration` as `None`, and the build succeeds.

That is legal because the framework does not require every project to adopt the meaning language. A small pipeline, a mechanical transformation, or a graph under construction can exist without a declared purpose. The model still has records, keys, properties and limits.

It is also semantically empty at the root. The declaration fragments that were attached remain in the blueprint, but no published purpose governs how their frames are read. A reader sees "Closed sites are absent" and cannot tell what the graph is for, so the limitation has no scope beyond the sentence. A consumer cannot decide whether a query is inside the graph's intended use. The hierarchy is rootless: the attachments exist, and the reading order has no first term.

Zero is therefore not an error and not a recommendation. A build with no graph declaration is a valid build with an unreviewable root. The right response is to declare the purpose, not to delete the fragments. A fragment without a purpose is a local statement in search of a context; a purpose without fragments is a root with nothing to govern. The pair is what makes the meaning reviewable.

A project can hold fragments while its root is absent, which shows that the framework permits incremental adoption. It does not make the root optional for a graph that intends to be consumed as a contract.

## A description is prose; an annotation is payload

Three channels carry information about a declaration, and they are not substitutes.

A **description** is prose for a human. It comes from `options.description` or a docstring, with the explicit option winning. It has no typed payload and no hierarchy. A component description is own-only: a concrete component does not inherit its category's description. A property description belongs to the declaring class and travels with the inherited slot.

An **annotation** is a frozen dataclass with a stable namespace, a stable identifier and a JSON-compatible payload. `NodeLabel` and `EdgeLabel` are framework annotations: one label names a component for a target such as Neo4j. A label is not a limitation, and an annotation is not a claim. A consumer that does not recognise an annotation preserves it and ignores it.

**Semantics** are the meaning units: claims, frames, limitations and the one purpose. They have a required hierarchy, non-empty text and explicit attachment sites. A docstring moved into `Semantics` does not become a claim; it becomes a claim-shaped string. A label moved into a `Frame` does not become a limitation; it becomes a label-shaped string. The type is what makes the statement reviewable.

The three channels coexist. A node can have a description for readers, a `Site` label for a target, and a semantics fragment for the meaning contract. Removing one does not replace another. This is why "add a comment" is not an answer to a missing limitation, and why "add an annotation" is not an answer to a missing purpose.

## The estate purpose, stated once

Read the estate model from the top. `EstateGraph` says the graph is for estate asset management and states one claim: a site holds installed equipment. Its purpose frame says the graph covers the registered estate only and that unregistered equipment is absent.

`SiteNode` attaches a fragment whose frame says it is the register as published and that closed sites are absent. `HasUnitEdge` can attach a fragment about what the relation asserts and when. A binding can claim "one row per site in the register". None of those lower statements repeats the purpose; each is read under it.

The result is a model that a consumer can use without a conversation. A query about unregistered equipment is outside the purpose. A query about closed sites is outside the node's frame. A query about a site's units is inside both, provided the binding's mapping holds. The framework did not enforce any of that; it published the units in a shape that makes the boundaries visible.

## Next

[9. Generating declarations](/book/part-2/06-generation) — turn an observed source schema into ordinary declarations without making generation part of the build.
