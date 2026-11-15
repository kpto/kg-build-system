---
title: "4. Meaning and purpose"
summary: "One root purpose on the graph axis, one contract on the relation axis, and the binding that joins them."
section: book
perspective: book
part: II
chapter: 4
order: 21
status: normative
verified: 2026-11-15
sources:
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
Meaning
  purpose: Purpose
             limitations: Limitation
  claims: Claim
```

The shape is enforced. A `Purpose` owns only `Limitation` values. A `Meaning` value carries at most one purpose and any number of claims; it must carry at least one of the two. Every unit text is non-empty. Units are immutable and carry no key, owner or reference, so the attachment site is the only thing that says what a unit belongs to.

Why separate a claim from a purpose? Because a claim is asserted regardless of use, while a purpose says what the subject is for. A limitation then says what that purpose does not license. Merging them into one "notes" field would let a reader mistake a caveat for a fact, or a local use for a contextless assertion.

## Choosing the unit

The unit is decided by the question the sentence answers, not by where the sentence was first written.

| Question | Unit |
| --- | --- |
| What is the subject for? | `Purpose` |
| What is asserted about it regardless of use? | `Claim` |
| What must a reader not infer while using it? | `Limitation` |
| What was measured to support a boundary? | `Claim` beside the purpose |
| Which category does the statement belong to? | A field, not a text prefix |

- A definition, identity, grain or cardinality is a claim, not a purpose.
- A prohibition, absence, exclusion or inference ceiling is a limitation, not a
  claim.
- A measurement is not a limitation. The limitation states the boundary the
  measurement supports; the figure stays in a claim.
- A unit states one thing. `association:` or `score:` in front of a sentence is
  a label, not a concept reference; if grouping is required, model it.
- A declaration with no positive use carries claims only. Do not invent a
  purpose to fill the shape.
- Two declarations may share a purpose only when the use is identical. If the
  subject or the operation differs, the purpose differs.
- A binding's purpose states the fulfilment it performs: which relation satisfies
  which record purpose, at grain, identity and coverage, and where it falls short.
  The record's meaning stays on its node or edge; the relation's meaning stays on
  the relation.

## Two axes, and the binding between them

A statement is attached on one of two axes, and the attachment site tells a reader which question it answers.

The **graph axis** is about records. It runs from the graph declaration through categories to concrete nodes and edges and to their properties. It answers what a record is, what it is for, and what the graph asserts. It has one root: the graph purpose.

The **relation axis** is about rows. It runs from a source relation or a derived relation to the fields that relation publishes. It answers what one row is, what identifies it, and what the relation means in the domain. Each relation states its own contract, and that contract is not a child of the graph purpose.

The two axes are deliberately not a hierarchy. A relation is a domain object: it may serve several graphs, be tested without one, and name a purpose that has nothing to do with estate asset management. Forcing it under the graph root would make its meaning depend on who consumes it, and the next consumer would have to rewrite it.

A binding is the only place the axes meet. It states that a published relation fulfils a declared record at a grain, an identity, a coverage and a meaning — and it states where that fulfilment falls short. That is the subject of [Binding as fulfilment](/book/part-2/08-binding); here it fixes where each kind of statement belongs.

| Axis | Root | Attached to | Answers |
| --- | --- | --- | --- |
| Graph | The graph purpose | Graph, category, node, edge, property | What does the graph claim, and under which use? |
| Relation | The relation contract | Source relation, derived relation, field | What is one row, and what does the relation mean? |
| Binding | The record purpose it fulfils | One binding | How does the relation satisfy the record, and where does it not? |

## The graph axis has one root

A project declares zero or one `Graph`. `GraphOptions.meaning` is required and must be a `Meaning` value carrying a purpose. That graph purpose is the root: it states why the graph exists and what it is for.

A node, edge, property or category may attach a local purpose. A local purpose is optional. It must narrow the graph purpose, not replace it. An asset states the source rather than a record, so its meaning is read with the relations that read it, not under the record purpose.

```text
Graph purpose: estate asset management
  Node purpose: the register as published
    Property purpose: the site's display name
      Limitations
```

The one-root rule is what makes a local purpose meaningful. If several independent purposes existed, the same limitation could be true under one and false under another, and a consumer would have no way to choose. One root means every lower purpose is read under the same expected use.

The framework does not copy the parent purpose into the child. A local purpose inherits an obligation, not text: it must be consistent with the purpose above it. Review catches contradictions; the build publishes the authored values.

## The relation axis has one contract per relation

A relation is a contract. Its options carry one `Contract` with two parts:

```text
Contract
  definition: grain, identity
  meaning: purpose, claims, limitations
```

A `Definition` states the structural facts: the grain — what one row is — and the identity — the field or field tuple whose value distinguishes one row. A `Meaning` states the domain use, the claims and the limitations. A declared contract is complete: a relation states both parts or it states neither. A half-contract is not a weaker contract; a relation with no contract is simply not yet a published object.

The two relation kinds differ in what their meaning must contain. A derived relation requires a purpose, because it exists only because some use asked for that grain. A source relation may state claims only, because it describes what the source holds and the use is chosen by whoever binds it; requiring a purpose there would force the author to invent one. Neither kind may state a meaning without a definition.

The contract is authored on the relation, not on its consumer. A source relation states it in `SourceRelationOptions`, a derived relation in `DerivedRelationOptions`. A `Stage` — the private intermediate relation inside one derived-relation package — states a `Definition` and no meaning, because it is not offered to anyone outside its package. [Source and rows](/book/part-2/03-source-and-rows) writes the first contract; [Derived relations](/book/part-2/05-grain-and-projections) writes the second.

A field carries a smaller version of the same idea. `field(...)` and `computed_field(...)` accept a `FieldDefinition(value, unit, null_meaning)`: what the value is, the unit it is measured in, and what its absence denotes. A field definition never restates the source column name or the logical type, because those are the declaration itself. The detailed contract material belongs to chapter 6.

## The graph declaration uses the same value

The graph declaration is not a special meaning type. It is the one declaration whose `Meaning` value must carry a purpose.

```python
from kg_build_system import (
    Claim, Graph, GraphOptions, Limitation, Meaning, Purpose,
)


class EstateGraph(Graph):
    options = GraphOptions(
        name="estate",
        description="Sites and the equipment installed at them.",
        meaning=Meaning(
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

Every declaration attaches the same `Meaning` type. The graph declaration requires a purpose, and so does a derived relation, which carries its meaning inside a contract. A source relation may state claims only, and a stage states no meaning at all; every other declaration may carry a purpose.

```python
from kg_build_system import (
    Claim, Limitation, Meaning, Node, NodeLabel, NodeOptions, Purpose,
    PropertySlot, property,
)


class SiteNode(Node):
    options = NodeOptions(
        annotations=(NodeLabel("Site"),),
        meaning=Meaning(
            purpose=Purpose(
                text="Use this node as the published estate register.",
                limitations=(Limitation("Closed sites are absent."),),
            ),
        ),
    )

    name: PropertySlot[str] = property(
        meaning=Meaning(
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
| Asset | `AssetOptions(meaning=...)` |
| Source relation, derived relation | `SourceRelationOptions(contract=...)`, `DerivedRelationOptions(contract=...)` |
| Stage | `StageOptions(definition=...)` — a definition and no meaning |
| Struct | `StructOptions(meaning=...)` |
| Field | `field(meaning=..., definition=...)` |
| Computed field | `computed_field(..., meaning=..., definition=...)` |
| Node or edge | `NodeOptions(meaning=...)`, `EdgeOptions(meaning=...)` |
| Property | `property(meaning=...)` |
| Binding | `node_binding(..., meaning=...)`, `edge_binding(..., meaning=...)`, or `BindingOptions(meaning=...)` |

A `SourceRelationGroupOptions` carries no fragment, because a relation group is a catalogue rather than a blueprint part. A binding carries one fragment for the whole mapping; there are no per-property binding meanings. A binding also has no description, so `debug_name` is its human handle and annotations are its metadata.

Write the value at the declaration. A project helper may assemble structure such as labels, options and defaults, but it must not take purpose, claim or limitation text as parameters. If a helper composes options, it accepts a `Meaning` value and passes it through. The reader must see the declaration and its meaning in one place; a parameter that sends the reader to another module for the meaning is an adaptation, not a convenience.

## Meaning is read along its axis, not copied

Each axis has a reading order:

1. The graph purpose and its claims.
2. The category and template meaning that topology shares.
3. The concrete node or edge purpose.
4. The property purposes inside it.
5. The relation's definition: grain and identity.
6. The relation's meaning: purpose, claims and limitations.
7. The field definitions and field meanings inside it.
8. The binding: how that relation fulfils the record's purpose, at grain,
   identity, coverage and meaning.

Steps one to four are the graph axis and are read under the graph purpose. Steps five to seven are the relation axis and are read under the relation's own contract. Step eight is the only place the two reading orders join.

A lower record fragment inherits an obligation, not text. The framework does not copy the parent's words into the child, and it does not check consistency. A syntactically valid fragment can still contradict the purpose; review catches that. A relation's purpose owes nothing to the graph purpose; the binding is where the two must agree.

Structural inheritance is a separate matter. A category's label and description stay local; they do not flow to a concrete child. A template's annotations do flow, because a template is a structural mixin. A category's meaning is its own attachment and stays there. Do not assume one rule covers both mechanisms.

The practical consequence is that you attach the statement where it is true. A limitation about a binding's coverage belongs on the binding's purpose. A limitation about what a node kind excludes belongs on the node's purpose. A claim that holds across the graph belongs on the graph's `Meaning`. A statement about what a source relation's rows contain belongs on that relation's contract. Putting every statement at the root makes the root unreadable; putting every statement on declarations loses the one root that makes local purposes comparable.

This is why a binding's meaning describes the fulfilment, not the record and not the relation. "One row per site in the register" is a claim about the mapping; "a site holds installed equipment" is a claim about the model. The binding states that the site relation satisfies the site-record purpose and where it falls short: the register covers the published estate, not unregistered sites. Moving the record's meaning onto the binding would make the mapping responsible for the node's meaning, which is the design leak the seam prevents.

## The blueprint publishes what the author attached

The blueprint is the semantic model of the graph, not a snapshot of the Python declarations. It carries the graph declaration, the topology, the data declarations, the assets and the bindings, together with the meaning attached to each. A relation publishes its two parts together as one `Contract` of a `Definition` and a `Meaning`.

The graph declaration is the optional fifth field, `graph_declaration`. It carries the graph's `Meaning` value, including the root purpose. When a project declares no `Graph`, the field is `None`. A declaration fragment is published on the DTO of the declaration it was attached to — its `MeaningDTO`, its relation contract or its field definition — not copied into a separate meaning index.

Publication is not interpretation. The blueprint does not evaluate truth, resolve claims against each other, revise them, or check cross-unit consistency. It publishes authored units so a consumer can compose them: a documentation renderer can print the purpose tree, a review tool can list limitations, a downstream service can refuse to answer a question outside a purpose. The framework's job ends at carrying the values faithfully.

Only reached declarations are published. A `Meaning` on a source relation that no binding reads, or on a node no binding targets, is valid Python but not part of the delivered model. Meaning follows the same reachability rule as topology and data: the blueprint describes the graph the bindings populate. A stage is not reached by publication at all: it stays inside its derived relation's package.

When a blueprint writes back to authoring source, the graph declaration renders first. That order is the reading order made visible: root purpose, then local purposes, then topology, then the relation axis, then bindings. A round trip that lost the graph declaration would lose the root of every graph-side purpose.

## Zero graph declarations is legal, and the relation axis stands alone

A project may declare no `Graph` at all. The graph language is optional; topology, data, assets and bindings compile without a root purpose. The blueprint publishes `graph_declaration` as `None`, and the build succeeds.

That is legal because the framework does not require every project to adopt the graph meaning language. A small pipeline, a mechanical transformation, or a graph under construction can exist without a declared purpose.

It is also semantically empty at the graph root. A contextless claim remains a claim: it needs no purpose. A local purpose does not: without a graph purpose, the purpose tree has no root. Publishing a limitation under a local purpose would give it a scope that no consumer can relate to the graph's intended use. For that reason, a project that attaches a graph-side local purpose must also declare a graph purpose. A project may attach claims without a root; it may not attach local purposes without one.

The relation axis is independent of that rule. A relation contract states a grain, an identity and a domain meaning, and it can be written, reviewed and tested in a project that declares no graph at all. What the relation axis cannot do without a graph is fulfil a record: a binding needs a node or an edge to target and a record purpose to satisfy, and it must state that fulfilment with a purpose of its own.

Zero is therefore not an error and not a recommendation. A build with no graph declaration is a valid build with an unreviewable root. The right response is to declare the purpose, not to delete the claims. A claim without a purpose is a contextless statement; a purpose without a root is an unanchored use. The root is what makes the purpose tree reviewable.

## A description is prose; an annotation is payload

Four channels carry information about a declaration, and they are not substitutes.

A **description** is prose for a human. It comes from `options.description` or a docstring, with the explicit option winning. It has no typed payload and no hierarchy. A component description is own-only: a concrete component does not inherit its category's description. A property description belongs to the declaring class and travels with the inherited slot.

An **annotation** is a frozen dataclass with a stable namespace, a stable identifier and a JSON-compatible payload. `NodeLabel` and `EdgeLabel` are framework annotations: one label names a component for a target such as Neo4j. A label is not a limitation, and an annotation is not a claim. A consumer that does not recognise an annotation preserves it and ignores it.

A **definition** is a typed structural statement: a relation's grain and identity, a field's value, unit and null meaning. It is not prose and not a claim; a binding is judged against it, which is why it lives on the declaration that owns the structure.

**Meaning** is the value language: purposes, limitations and claims. It has a required hierarchy, non-empty text and explicit attachment sites. A docstring moved into `Meaning` does not become a claim; it becomes a claim-shaped string. A label moved into a `Purpose` does not become a limitation; it becomes a label-shaped string. The type is what makes the statement reviewable.

The four channels coexist. A node can have a description for readers, a `Site` label for a target, and a meaning fragment for the contract. Removing one does not replace another. This is why "add a comment" is not an answer to a missing limitation, and why "add an annotation" is not an answer to a missing purpose.

## The estate purpose, stated once

Read the estate model from the top. `EstateGraph` states the root purpose: estate asset management, limited to the registered estate, with unregistered equipment absent. It also states one claim: a site holds installed equipment.

`SiteNode` attaches a local purpose: the register as published, with closed sites absent. `HasUnitEdge` attaches the purpose of the relation: what it asserts and when. `SitesSourceRelation` states a contract on the other axis: one row per monitored site, identified by `site_id`, with its own domain purpose. `site_binding` states the fulfilment: the site relation satisfies the site-record purpose, one row per site in the register, and it falls short where the register does. None of those lower statements repeats the root purpose; each is read on its axis, and the binding is where they meet.

The result is a model that a consumer can use without a conversation. A query about unregistered equipment is outside the graph purpose. A query about closed sites is outside the node's local purpose. A query about a site's units is inside both, provided the binding's mapping holds. The framework did not enforce any of that; it published the units in a shape that makes the boundaries visible.

## Next

[5. Topology](/book/part-2/02-topology) — turn the purpose into the record kinds and properties the graph will assert.
