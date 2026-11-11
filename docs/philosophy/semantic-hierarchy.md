---
title: One purpose, read downward
summary: "The graph purpose is the root; topology, data and binding fragments are read under it, not copied from it."
section: philosophy
order: 20
status: normative
verified: 2026-11-10
sources:
  - docs/author/meaning.md
  - docs/author/meaning.md
  - kg_build_system/distribution/languages/semantics/model/public/units.py
  - kg_build_system/distribution/languages/topology/
---

> [!lede]
> Semantics are connected as a hierarchy: one project purpose, topology that states what each record is, then data and bindings that state how this implementation supplies it. The connection is a reading order. It is not an automatic copy from parent to child: semantic inheritance is an obligation, not a copy. A lower fragment inherits the duty to be consistent with the higher meaning.

## What it is

- **Graph purpose** — why the graph exists and the claims true of the whole graph. Attached to `GraphSemantics` on the one `Graph`; it is the root.
- **Topology category/template** — shared properties, annotations and category meaning. Attached to `AbstractNode`, `AbstractEdge` or template options. Properties and template annotations flow structurally; a category’s label and description do not flow to a child.
- **Concrete node/edge** — what this record is, its direction and its limits. Attached to `NodeOptions(semantics=...)` or `EdgeOptions(semantics=...)`; explicit.
- **Data** — how the implementation supplies the record. Attached to table, projection or field `Semantics`; explicit.
- **Binding** — how this row becomes this record. Attached to `node_binding(..., semantics=...)`; explicit.

<figure class="kb-plate">
  <img src="/_assets/semantics.svg" alt="Graph purpose above topology, data and binding; each lower layer is read under the purpose, and the framework stores attachments rather than copying the parent text.">
  <figcaption>Read from the purpose down. The framework stores each attachment; it does not synthesise the parent link.</figcaption>
</figure>

## Rules

- A project has exactly one purpose. A declaration fragment has no purpose of its own; every frame is read under the graph purpose.
- Topology states the design. Data and binding fragments state how this implementation reads under it. A lower fragment must not contradict the purpose; if it does, the design changes, not the sentence.
- Structural inheritance is not semantic inheritance. A category’s label and description do not flow to a concrete child; a template’s annotations do. Attach the concrete component’s semantics explicitly.
- Put a limitation in the frame where it is true. A binding-specific absence belongs on the binding; a node-wide exclusion belongs on the node.
- Do not repeat the purpose in every fragment. State the shared meaning at the level that owns it; state only the local reading below.
- The framework does not check consistency between levels. The author makes the hierarchy coherent; the reviewer reads it from the top.

## Example

```python
from kg_build_system import (
    Claim, Frame, Graph, GraphOptions, GraphSemantics, Limitation, Node,
    NodeOptions, NodeValues, PropertySlot, Purpose, Semantics, node_binding,
    property, value_expression,
)

from reference_project.table.sites import SitesTable
from reference_project.topology.common import (
    DocumentedAbstractNode, ProvenancedNodeTemplate,
)


class EstateGraph(Graph):
    options = GraphOptions(
        name="estate",
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


class SiteNode(ProvenancedNodeTemplate, DocumentedAbstractNode, Node):
    options = NodeOptions(
        semantics=Semantics(
            frames=(
                Frame(
                    text="The published register.",
                    limitations=(Limitation("Closed sites are absent."),),
                ),
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

Read it downward: the purpose says the graph is for estate asset management; the `SiteNode` frame says this component states the published register and omits closed sites; the binding claim says the mapping is one row per site. None of the lower text is copied from above. Each statement is consistent with the purpose, and the binding adds the mapping fact the node does not own.

## Limits

- `Semantics` fragments do not inherit from a parent. There is no parent link in the DTO, no propagation and no cross-level consistency check.
- A category’s label and description do not flow to a child. A template’s annotations do. Do not assume one rule covers both.
- Zero `Graph` declarations are legal. The hierarchy is then rootless: the attachments remain, but no published purpose governs their reading. The reference project is in this state.
- A fragment is not a comment. It is published data with claims, frames and limitations; a docstring or annotation is a different channel.
- A lower fragment can be syntactically valid and still contradict the purpose. Only review catches that.

## Next

[Design in semantics](/philosophy/design-in-semantics) — how names and claims carry the design.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-023 | Add semantics and graph as value languages with one graph purpose per project. | 2026-11-06 | accepted | `tests/distribution/test_semantics_language.py` |
| D-027 | Support polymorphic categories/templates with one normative base order. | 2026-09-01 | accepted | `docs/reference/topology.md#base-order` |
