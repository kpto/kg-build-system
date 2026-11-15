---
title: One purpose, read downward
summary: "The graph purpose is the root; topology, data and binding fragments are read under it, not copied from it."
section: philosophy
order: 20
status: normative
verified: 2026-11-10
sources:
  - docs/content/book/part-2/01-meaning-and-purpose.md
  - docs/content/book/part-2/01-meaning-and-purpose.md
  - kg_build_system/distribution/languages/semantics/model/public/units.py
  - kg_build_system/distribution/languages/topology/
---

> [!lede]
> Semantics are connected as a hierarchy: one graph purpose, local purposes that narrow it, and limitations that bound each purpose. The connection is a reading order. It is not an automatic copy from parent to child: semantic inheritance is an obligation, not a copy. A lower purpose inherits the duty to be consistent with the higher meaning.

## What it is

- **Graph purpose** — why the graph exists, what it is for and what it is not for. Attached to the graph declaration’s `Semantics`; it is the root.
- **Topology category/template** — shared properties, annotations and category meaning. Attached to `AbstractNode`, `AbstractEdge` or template options. Properties and template annotations flow structurally; a category’s label and description do not flow to a child.
- **Concrete node/edge** — one expected use of this record, its claims and its limits. Attached to `NodeOptions(semantics=...)` or `EdgeOptions(semantics=...)`; explicit.
- **Property** — one expected use of the value and what that use does not authorize. Attached to `property(semantics=...)`; explicit.
- **Data** — how the implementation supplies the record. Attached to table, projection or field `Semantics`; explicit.
- **Binding** — how this row becomes this record. Attached to `node_binding(..., semantics=...)`; explicit.

<figure class="kb-plate">
  <img src="/_assets/semantics.svg" alt="Graph purpose above topology, data and binding; each lower layer is read under the purpose, and the framework stores attachments rather than copying the parent text.">
  <figcaption>Read from the purpose down. The framework stores each attachment; it does not synthesise the parent link.</figcaption>
</figure>

## Rules

- A project has one root purpose on the graph declaration. A local purpose is optional and must narrow the root.
- A declaration carries at most one purpose. If it needs two incompatible uses, split the declaration or turn one use into a limitation.
- A limitation belongs inside the purpose it bounds. A claim is contextless and never owns a limitation.
- Topology states the design. Data and binding purposes state how this implementation supplies it. A lower purpose must not contradict its parent; if it does, the design changes, not the sentence.
- Structural inheritance is not semantic inheritance. A category’s label and description do not flow to a concrete child; a template’s annotations do. Attach the concrete component’s semantics explicitly.
- Do not repeat the root purpose in every fragment. State the shared meaning at the level that owns it; state only the local purpose below.
- The framework does not check consistency between levels. The author makes the hierarchy coherent; the reviewer reads it from the top.

## Example

```python
from kg_build_system import (
    Claim, Graph, GraphOptions, Limitation, Node, NodeOptions, NodeValues,
    PropertySlot, Purpose, Semantics, node_binding, property, value_expression,
)

from reference_project.table.sites import SitesTable
from reference_project.topology.common import (
    DocumentedAbstractNode, ProvenancedNodeTemplate,
)


class EstateGraph(Graph):
    options = GraphOptions(
        name="estate",
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


class SiteNode(ProvenancedNodeTemplate, DocumentedAbstractNode, Node):
    options = NodeOptions(
        semantics=Semantics(
            purpose=Purpose(
                text="Use this node as the published register.",
                limitations=(Limitation("Closed sites are absent."),),
            ),
        ),
    )

    name: PropertySlot[str] = property()


site_binding = node_binding(
    target=SiteNode,
    rows=SitesTable.row_source(),
    bind=lambda row: NodeValues(
        build_key=row.site_id.alter_rows().drop_null(),
        properties=SiteNode(
            name=row.site_name.default_to("Unnamed site"),
            summary=value_expression("A monitored site."),
            source_version=value_expression("survey-2026-08"),
        ),
    ),
    semantics=Semantics(
        claims=(Claim("One row per site in the register."),),
    ),
)
```

Read it downward: the root purpose says the graph is for estate asset management; the `SiteNode` purpose says this component is the published register and omits closed sites; the binding claim says the mapping is one row per site. None of the lower text is copied from above. Each statement is consistent with the root, and the binding adds the mapping fact the node does not own.

## Limits

- `Semantics` fragments do not inherit from a parent. There is no parent link in the DTO, no propagation and no cross-level consistency check.
- A category’s label and description do not flow to a child. A template’s annotations do. Do not assume one rule covers both.
- Zero `Graph` declarations are legal for claims, but a local purpose is refused without a root. A project that wants a purpose tree must declare the graph purpose.
- A fragment is not a comment. It is published data with purposes, limitations and claims; a docstring or annotation is a different channel.
- A lower purpose can be syntactically valid and still contradict the root. Only review catches that.

## Next

[Design in semantics](/appendix/philosophy/design-in-semantics) — how names and claims carry the design.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-023 | Add semantics and graph as value languages with one graph purpose per project. | 2026-11-06 | accepted | `tests/distribution/test_semantics_language.py` |
| D-027 | Support polymorphic categories/templates with one normative base order. | 2026-09-01 | accepted | `docs/content/appendix/reference/topology.md#base-order` |
