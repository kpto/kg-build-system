---
title: Declare meaning
summary: One graph purpose, claims that hold regardless of use, and frames that own the limits a reader must know.
section: author
order: 80
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/distribution/languages/semantics/model/public/units.py
  - kg_build_system/distribution/languages/graph/model/public/options.py
  - kg_build_system/distribution/languages/graph/model/public/declarations.py
  - kg_build_system/distribution/languages/annotations/model/public/base.py
  - docs/author/meaning.md
subject: meaning
perspective: guide
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Semantics and graph purpose</span><a href="/subjects/meaning">Overview</a><a href="/author/meaning" class="active">Guide</a><a href="/spec/meaning">Spec</a><a href="/reference/api">API</a><a href="/philosophy/semantic-hierarchy">Philosophy</a><a href="/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

> [!lede]
> Meaning is a value language, not prose metadata. The graph carries one purpose; declarations attach claims and frames that are read under that purpose.

## What it is

| Unit | Answers | Owned by |
| --- | --- | --- |
| `Claim(text)` | What holds regardless of purpose or frame? | `GraphSemantics` or `Semantics`. |
| `Limitation(text)` | What must a reader know given the purpose and frame? | A `Frame` only. |
| `Frame(text, limitations)` | Within what scope is the limitation stated? | `Purpose` or `Semantics`. |
| `Purpose(text, frames)` | What is the graph for? | `GraphSemantics` only. |
| `Semantics(claims, frames)` | What does this declaration mean? | A declaration attachment. |
| `GraphSemantics(claims, purpose)` | What is the project's meaning root? | The one `Graph`. |

The two levels are distinct. `GraphSemantics` is the meaning root; `Semantics` is a fragment with no purpose of its own. Units are immutable and carry no key, owner or reference, so the attachment site is the only ownership.

Attach a fragment through `AssetOptions(semantics=...)`, `TableOptions`/`StructOptions`/`ProjectionOptions`, `field(semantics=...)`, `computed_field(semantics=...)`, `NodeOptions`/`EdgeOptions(semantics=...)`, `property(semantics=...)`, `BindingOptions(semantics=...)` or `node_binding`/`edge_binding(semantics=...)`.

Annotations are a separate channel: a portable `(namespace, annotation_id, arguments)` payload. `NodeLabel` and `EdgeLabel` are single-label annotations. Descriptions are prose on options and DTOs; they are not claims, and neither is an annotation.

## Rules

- Every unit text is non-empty. A `Frame` owns only `Limitation` values, and a `Purpose` owns only `Frame` values.
- Claims live at graph or declaration level, never under a frame. Limitations live under a frame, never directly under a purpose.
- `Semantics` needs at least one claim or frame. `GraphSemantics` requires a `Purpose`; it may have no claims.
- A declaration attaches `Semantics`, never `GraphSemantics`. The graph meaning root belongs to the graph declaration alone.
- `GraphOptions.semantics` is required and must be `GraphSemantics` carrying a `Purpose`. Its `name` defaults to the class name in snake case.
- A project declares zero or one `Graph`. Two graph declarations are refused.
- A declaration fragment cannot state its own purpose. Every declaration frame is read under the one graph purpose.
- A node or edge carries at most one matching label. A node label on an edge is refused.
- `TableGroupOptions` has no semantics field. A table group is a catalogue, not a blueprint part.
- The graph declaration becomes `graph_declaration` in the blueprint, an optional fifth field, and renders first when a blueprint writes back to source.

## Example

```python
from kg_build_system import (
    Claim, Frame, Graph, GraphOptions, GraphSemantics, Limitation,
    Node, NodeLabel, NodeOptions, PropertySlot, Purpose, Semantics, property,
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
                        text="Registered equipment only.",
                        limitations=(
                            Limitation("Unregistered equipment is absent."),
                        ),
                    ),
                ),
            ),
        ),
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
```

`EstateGraph` states the project purpose. `SiteNode` attaches a fragment whose frame is interpreted under that purpose, and `NodeLabel("Site")` names the component for a target.

## Limits

- There is no truth evaluation, revision, cut, change, resolution or cross-unit consistency check. The blueprint publishes authored units; consumers compose them.
- There is no second purpose and no declaration-level purpose. A statement that only makes sense in a narrower scope becomes a limitation in a frame.
- A graph declaration is not a node, edge or asset, and it participates in no references.
- Semantics are independent of descriptions and annotations. Moving prose into `Semantics` does not make it a claim, and a label is not a limitation.
- `TableGroupOptions` carries no fragment, and per-property binding semantics do not exist; attach one fragment to the whole binding.
- Units have no inheritance and no identity. A category fragment and a declaration fragment are separate attachments.
- A graph property is a scalar or a flat, non-null array of scalars. Nested meaning becomes nodes and edges, not a richer property.

## Next

[Read the blueprint](/pipeline/blueprint) — where `graph_declaration` is published and rendered first.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-023 | Add semantics and graph as value languages with one graph purpose per project. | 2026-11-06 | accepted | `tests/distribution/test_semantics_language.py` |
| D-029 | Restrict graph properties to scalars or flat arrays of non-null scalars, and type SQL output by the property type. | 2026-10-22 | accepted | `docs/reference/types.md#graph-property-shape` |
