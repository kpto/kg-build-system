---
title: Explainability is authored
summary: "The framework preserves the meaning you state; it cannot infer why your graph exists."
section: philosophy
order: 40
status: normative
verified: 2026-11-15
sources:
  - docs/content/appendix/philosophy/index.md
  - docs/content/book/intent.md
  - AGENTS.md
  - reference_project/manifest.py
---

> [!lede]
> The framework can make a graph inspectable, typed and reproducible. It cannot make it explainable. Explainability is the part you write: the purpose, the claims, the names and the limits. A valid graph with none of those is still empty of meaning.

## What it is

| The framework can | The framework cannot |
| --- | --- |
| Preserve purposes, claims and limitations as published data | Invent a purpose for a graph that has none |
| Check that a `Graph` has a `Meaning` carrying one purpose | Decide whether the purpose is meaningful or true |
| Publish labels, descriptions and annotations with the blueprint | Infer why a node or edge exists |
| Publish the contract a relation declares | Make a relation purpose follow from the graph purpose |
| Resolve typed references and refuse an unknown one | Know that a reference is the right design |
| Record an absence as a nullable field or a limitation | Decide whether a limit is honest or a convenient omission |
| Refuse a second graph declaration and a second graph purpose | Notice that a project states no purpose at all |

The last row is the important one. A project can publish topology, relations and bindings without a `Graph`. The blueprint still carries topology, data, bindings and their meaning; it carries no `graph_declaration`, so no graph purpose is published. That is a limit, not a silent success.

## Rules

- State the graph purpose before asking the framework to explain the graph. If you cannot state it, record the gap rather than inventing one.
- A claim is not a description. A description explains a component to a reader; a claim is a statement a consumer may rely on. Put each in its own channel.
- Do not use a generated count, example value or meta-graph summary as the meaning of the graph. Those are evidence that the build ran; they are not intent.
- A limitation is a first-class statement. If the data cannot answer a question, say so under the purpose where it is true; do not leave the absence implicit.
- Write meaning for the consumer, not for the compiler. The compiler only checks the structure of the statement.
- Give each relation read by a binding its own `Contract`; a derived relation always states one. The graph purpose does not explain a domain relation, and a relation purpose does not explain the graph.
- Treat the presence of a purpose as a promise. A purpose that no record can serve is worse than an explicit missing purpose.
- The framework will not stop a valid but meaningless design. Review is the guard.

## Example

The reference project has topology, properties, templates, categories and annotations, but no `Graph`. It compiles and publishes records; its purpose is not in the artifact. Add the root:

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
                limitations=(Limitation("Unregistered equipment is absent."),),
            ),
            claims=(Claim("A site holds installed equipment."),),
        ),
    )
```

The blueprint now carries `graph_declaration`; a consumer can read the purpose and its limitations without reading the pipeline. The framework still does not know whether “estate asset management” is the right purpose. That judgment remains authored and reviewed.

## Limits

- No truth evaluation, no inference, no meaning diff and no cross-unit consistency check. The units are published, not proved.
- A project with no graph declaration publishes no graph purpose. A build can still succeed; the absence is a review finding, not an error.
- A description is local: a concrete node does not inherit a description from its category. Annotations and labels have their own flow; they are not meaning.
- A relation contract is domain-level. A consumer that needs to know how the relation serves this graph reads the binding, not a rewritten relation purpose.
- Meta-graph counts are exact for the records that reached the executor; examples are approximate. Neither is a statement of intent.
- Generated source is not meaning. A generated `Field[T]` says what the value is; it does not say why the record exists.
- The review surface is [Review](/appendix/review/index), not the compiler. A green build is evidence of execution, not of explainability.

## Next

[The binding is the fulfilment](/appendix/philosophy/binding-is-fulfilment) — where implementation meets the design.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-023 | Add meaning and graph as value languages with one graph purpose per project. | 2026-11-06 | accepted | `tests/distribution/test_meaning_language.py` |
| D-038 | Keep author docs deep and separate from internal specs, with concept/reference paths. | 2026-11-05 | accepted | `STYLE.md`; `docs/content/appendix/developer/index.md` |
| D-039 | Guard the architecture with a contract test and a reviewer briefing. | 2026-11-02 | accepted | `tests/test_architecture.py`; `FRAMEWORK_STATE.md` |
