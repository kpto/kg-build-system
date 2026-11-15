---
title: "4. Meaning and purpose"
summary: "A graph publishes one root purpose, local purposes that narrow it, contextless claims and the limitations of each purpose."
section: book
perspective: book
part: II
chapter: 4
order: 21
status: normative
verified: 2026-11-15
sources:
  - docs/content/book/part-2/01-meaning-and-purpose.md
  - docs/content/appendix/spec/meaning.md
  - docs/content/appendix/philosophy/semantic-hierarchy.md
---

## A graph can compile and still say nothing

A topology can be coherent, every binding can resolve, and the build can produce a clean blueprint while a reader still cannot answer the first question: what is this graph for? The node and edge declarations say what each record is. The bindings say which rows become which record. Neither says why the graph exists, what holds across all of it, or what a consumer must know before trusting a query.

Meaning is not a comment added after the build. It is a value language carried by the declarations themselves and published in the blueprint. A `Purpose` states one expected use of a subject and owns the limitations of that use. A `Claim` states what is asserted about the subject regardless of purpose. A `Limitation` states what the purpose does not authorize. The framework stores those values where the author attached them and publishes them beside the topology, the data and the bindings.

The separation matters for the same reason the topology/binding separation matters. If meaning lived in a README, it would drift from the artifact. If it lived in docstrings, no consumer could read it. If a declaration could carry several unrelated purposes, a limitation would be true only in the scope of whoever wrote it, and a consumer would have no rule for choosing the scope.

## Three jobs: claim, purpose, limitation

The unit vocabulary is small, and the restrictions between units are the design.

A `Claim` is contextless. It says something that is asserted about the subject regardless of purpose. In the estate graph, "A site holds installed equipment" is a claim: it is true of the model, not only of one report. Claims attach at graph level or declaration level. They never live inside a purpose.

A `Purpose` is one expected use of the subject. "Use this node as the published estate register" is a purpose. It does not assert a fact about the world; it names what the subject is for and owns the limitations that bound that use.

A `Limitation` states what the purpose does not authorize. "Closed sites are absent" is a limitation. It belongs to a purpose, never directly to a declaration as a bare statement.

```text
Semantics
  purpose: Purpose
             limitations: Limitation
  claims: Claim
```

The shape is enforced. A `Purpose` owns only `Limitation` values. A `Semantics` value carries at most one purpose and any number of claims; it must carry at least one of the two. Every unit text is non-empty. Units are immutable and carry no key, owner or reference, so the attachment site is the only thing that says what a unit belongs to.

Why separate a claim from a purpose? Because a claim is asserted regardless of use, while a purpose says what the subject is for. A limitation then says what that purpose does not license. Merging them into one "notes" field would let a reader mistake a caveat for a fact, or a local use for a contextless assertion.

## Purpose is the root, not the only purpose

A project declares zero or one `Graph`. `GraphOptions.semantics` is required and must be a `Semantics` value carrying a purpose. That graph purpose is the root: it states why the graph exists and what it is for.

A node, edge, property, asset, binding, table or field may attach a local purpose. A local purpose is optional. It must narrow the graph purpose, not replace it.

```text
Graph purpose: estate asset management
  Node purpose: the register as published
    Property purpose: the site's display name
      Limitations
```

The one-root rule is what makes a local purpose meaningful. If several independent purposes existed, the same limitation could be true under one and false under another, and a consumer would have no way to choose. One root means every lower purpose is read under the same expected use.

The framework does not copy the parent purpose into the child. A local purpose inherits an obligation, not text: it must be consistent with the purpose above it. Review catches contradictions; the build publishes the authored values.

## The graph declaration uses the same value

The graph declaration is not a special semantics type. It is the one declaration whose `Semantics` value must carry a purpose.

```python
from kg_build_system import (
    Claim, Graph, GraphOptions, Limitation, Purpose, Semantics,
)


class EstateGraph(Graph):
    options = GraphOptions(
        name="estate",
        description="Sites and the equipment installed at them.",
        semantics=Semantics(
            purpose=Purpose(
                text="Estate asset management.",
                limitations=(
                    Limitation("Unregistered equipment is absent."),
                ),
            ),
            claims=(Claim("A site holds installed equipment."),),
        ),
    )
```

`GraphOptions` also carries a name and a description. The name defaults to the class name in snake case. The description is prose; it is not a claim. A `Graph` is not a node, an edge or an asset, and it participates in no references. It is the project's statement of purpose, not another component in the topology.

Two graph declarations are refused. The refusal is not a namespace convenience. Two graph declarations would give the model two roots, and every local purpose would inherit that ambiguity. A project that needs a second root needs a separate graph build, not a second declaration in the same project.

## A declaration attaches one fragment

Every declaration attaches the same `Semantics` type. The graph declaration requires a purpose; every other declaration may carry one.

```python
from kg_build_system import (
    Claim, Limitation, Node, NodeLabel, NodeOptions, Purpose, Semantics,
    PropertySlot, property,
)


class SiteNode(Node):
    options = NodeOptions(
        annotations=(NodeLabel("Site"),),
        semantics=Semantics(
            purpose=Purpose(
                text="Use this node as the published estate register.",
                limitations=(Limitation("Closed sites are absent."),),
            ),
        ),
    )

    name: PropertySlot[str] = property(
        semantics=Semantics(
            purpose=Purpose(
                text="Use this value as the site's display name.",
                limitations=(
                    Limitation("Not unique; do not use it as identity."),
                ),
            ),
            claims=(
                Claim("The name supplied by the estate register."),
            ),
        ),
    )
```

A declaration fragment does not repeat "estate asset management". It states the local use: this component is the published register, and this property is the display name. A reader supplies the root purpose from the graph declaration and reads the fragment under it.

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

## Meaning is read downward, not copied

The semantic hierarchy is a reading order:

1. The graph purpose and its claims.
2. The category and template meaning that topology shares.
3. The concrete node or edge purpose.
4. The property purposes inside it.
5. The data declarations that supply the record.
6. The binding that maps rows onto it.

A lower fragment inherits an obligation, not text. It must be consistent with the purpose above it. The framework does not copy the parent's words into the child, and it does not check consistency. A syntactically valid fragment can still contradict the purpose; review catches that.

Structural inheritance is a separate matter. A category's label and description stay local; they do not flow to a concrete child. A template's annotations do flow, because a template is a structural mixin. A category's semantics is its own attachment and stays there. Do not assume one rule covers both mechanisms.

The practical consequence is that you attach the statement where it is true. A limitation about a binding's coverage belongs on the binding's purpose. A limitation about what a node kind excludes belongs on the node's purpose. A claim that holds across the graph belongs on the graph's `Semantics`. Putting every statement at the root makes the root unreadable; putting every statement on declarations loses the one root that makes local purposes comparable.

This is why a binding's semantics describes the mapping, not the record. "One row per site in the register" is a claim about the binding. "A site holds installed equipment" is a claim about the model. Moving the second onto the binding would make the mapping responsible for the node's meaning, which is exactly the design leak the seam prevents.

## The blueprint publishes what the author attached

The blueprint is the semantic model of the graph, not a snapshot of the Python declarations. It carries the graph declaration, the topology, the data declarations, the assets and the bindings, together with the semantics attached to each.

The graph declaration is the optional fifth field, `graph_declaration`. It carries the graph's `Semantics` value, including the root purpose. When a project declares no `Graph`, the field is `None`. A declaration fragment is published on the DTO of the declaration it was attached to, not copied into a separate meaning index.

Publication is not interpretation. The blueprint does not evaluate truth, resolve claims against each other, revise them, or check cross-unit consistency. It publishes authored units so a consumer can compose them: a documentation renderer can print the purpose tree, a review tool can list limitations, a downstream service can refuse to answer a question outside a purpose. The framework's job ends at carrying the values faithfully.

Only reached declarations are published. A `Semantics` value on a table that no binding reads, or on a node no binding targets, is valid Python but not part of the delivered model. Meaning follows the same reachability rule as topology and data: the blueprint describes the graph the bindings populate.

When a blueprint writes back to authoring source, the graph declaration renders first. That order is the reading order made visible: root purpose, then local purposes, then topology, data and bindings. A round trip that lost the graph declaration would lose the root of every local purpose.

## Zero graph declarations is legal and rootless

A project may declare no `Graph` at all. The graph language is optional; topology, data, assets and bindings compile without a root purpose. The blueprint publishes `graph_declaration` as `None`, and the build succeeds.

That is legal because the framework does not require every project to adopt the meaning language. A small pipeline, a mechanical transformation, or a graph under construction can exist without a declared purpose.

It is also semantically empty at the root. A contextless claim remains a claim: it needs no purpose. A local purpose does not: without a graph purpose, the purpose tree has no root. Publishing a limitation under a local purpose would give it a scope that no consumer can relate to the graph's intended use. For that reason, a project that attaches a local purpose must also declare a graph purpose. A project may attach claims without a root; it may not attach local purposes without one.

Zero is therefore not an error and not a recommendation. A build with no graph declaration is a valid build with an unreviewable root. The right response is to declare the purpose, not to delete the claims. A claim without a purpose is a contextless statement; a purpose without a root is an unanchored use. The root is what makes the purpose tree reviewable.

## A description is prose; an annotation is payload

Three channels carry information about a declaration, and they are not substitutes.

A **description** is prose for a human. It comes from `options.description` or a docstring, with the explicit option winning. It has no typed payload and no hierarchy. A component description is own-only: a concrete component does not inherit its category's description. A property description belongs to the declaring class and travels with the inherited slot.

An **annotation** is a frozen dataclass with a stable namespace, a stable identifier and a JSON-compatible payload. `NodeLabel` and `EdgeLabel` are framework annotations: one label names a component for a target such as Neo4j. A label is not a limitation, and an annotation is not a claim. A consumer that does not recognise an annotation preserves it and ignores it.

**Semantics** are the meaning units: purposes, limitations and claims. They have a required hierarchy, non-empty text and explicit attachment sites. A docstring moved into `Semantics` does not become a claim; it becomes a claim-shaped string. A label moved into a `Purpose` does not become a limitation; it becomes a label-shaped string. The type is what makes the statement reviewable.

The three channels coexist. A node can have a description for readers, a `Site` label for a target, and a semantics fragment for the meaning contract. Removing one does not replace another. This is why "add a comment" is not an answer to a missing limitation, and why "add an annotation" is not an answer to a missing purpose.

## The estate purpose, stated once

Read the estate model from the top. `EstateGraph` states the root purpose: estate asset management, limited to the registered estate, with unregistered equipment absent. It also states one claim: a site holds installed equipment.

`SiteNode` attaches a local purpose: the register as published, with closed sites absent. `HasUnitEdge` attaches the purpose of the relation: what it asserts and when. A binding claims "one row per site in the register". None of those lower statements repeats the root purpose; each is read under it.

The result is a model that a consumer can use without a conversation. A query about unregistered equipment is outside the graph purpose. A query about closed sites is outside the node's local purpose. A query about a site's units is inside both, provided the binding's mapping holds. The framework did not enforce any of that; it published the units in a shape that makes the boundaries visible.

## Next

[5. Topology](/book/part-2/02-topology) — turn the purpose into the record kinds and properties the graph will assert.
