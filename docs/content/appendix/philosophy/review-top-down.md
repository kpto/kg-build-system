---
title: Review top-down
summary: "Read purpose, topology and relation contracts before bindings, data and plan; a bottom-up review passes a meaningless graph."
section: philosophy
order: 60
status: normative
verified: 2026-11-15
sources:
  - AGENTS.md
  - reference_project/build.py
  - docs/content/appendix/developer/project-structure.md
---

> [!lede]
> A plan can be correct and a graph can be meaningless. Review in the order the meaning is built: purpose, topology and record meaning, relation contracts, bindings, data, then plan. A bottom-up review checks the plumbing and misses the design.

## What it is

| Step | Read | Pass condition |
| --- | --- | --- |
| 1 | Graph meaning and claims | One `Graph`; one graph purpose; claims the records can serve. |
| 2 | Topology and record meaning | Node and edge meaning, direction, properties and category/template use are deliberate. |
| 3 | Relation contracts | Each relation read by a binding has a `Contract`: grain and identity in `Definition`, domain purpose, claims and limitations in `Meaning`. A derived relation always states one. |
| 4 | Bindings | Each binding has a meaning with a purpose; grain, identity and coverage match; the relation is published and record-agnostic. |
| 5 | Data and structure | `SourceRelation`, `DerivedRelation` and `Stage` names describe the design; stages stay private. |
| 6 | Plan and report | Components, kinds, connections and publications support the design; they do not define it. |

If step 1 or 2 is empty, stop. Execution cannot supply a design that was never declared. If step 3 or 4 is empty, the record may still be produced, but nothing states why the relation is allowed to produce it.

## Rules

- Review the graph purpose first. A graph with no `Graph` has no published purpose; say so rather than assuming one.
- Read topology as meaning: a node is a thing, an edge is a directed assertion, a property is a value the record carries. A missing edge is as important as a wrong one.
- Read each relation on its own axis. A relation purpose is not a local purpose under the graph; it must stand without a node, edge, binding or pipeline step. Check that a published relation does not name a record's properties, key or endpoints.
- Check that every relation a binding reads has both parts of the contract. A relation with a grain but no domain purpose is a source shape; a relation with a purpose but no identity cannot be bound honestly. A derived relation always states a contract.
- Check that every binding states a fulfilment, not a mapping. It names the relation, the record purpose, the grain, the coverage and the shortfall. A one-to-one mapping is allowed only when that is the whole truth.
- Check that a `Stage` stays inside its derived-relation package. A binding that reads a stage has bypassed the published contract.
- Review names before SQL. A domain name at the blueprint level and a technical name in the plan is healthy; the reverse is a leak.
- Review limits. What does the graph not answer? A limit under the right purpose is a feature; a missing limit is a hidden claim.
- Review provenance. Can a consumer trace a record to its asset, relation and declaration? A plan step is not a source dataset.
- Do not accept “it compiles”, “the report succeeded” or “the counts are right” as a design review. Those are execution facts.

## Example

The reference project, reviewed top-down:

| Step | Result | Evidence |
| --- | --- | --- |
| Graph meaning | **fail** | No `Graph` declaration; no published graph purpose. |
| Topology | pass | Six concrete node types, six concrete edge types, categories and templates with deliberate direction. |
| Record meaning | partial | Descriptions, labels and provenance annotations; no graph purpose and no local `Meaning` values. |
| Relation contracts | partial | Source and derived relations exist; grain is stated in code and comments, not in a `Contract`. |
| Bindings | partial | Keys narrowed, properties supplied and endpoint tokens only where needed; no binding `Meaning` states the fulfilment. |
| Data and structure | partial | Relations and bindings are grouped by subject, but declarations still live in `__init__.py` files. |
| Plan | pass | The run publishes records and a report; the wiring supports the design. |

The graph is useful and structurally sound. It is not a fully explainable design, because the graph purpose and the relation contracts are missing, and the declaration files do not yet follow [Project structure](/appendix/developer/project-structure). The review names those gaps; the build cannot.

## Limits

- There is no meaning lint, no consistency check across the axes and no automated “is this meaningful” test.
- The reviewer supplies judgment. The framework supplies the structure, the references and the published artifacts.
- A pass on topology does not imply a pass on data; a source can be unable to supply a declared property. Read both.
- A reference project's choices are evidence, not a template. Its missing `Graph` is a limit to name, not a pattern to copy.
- A plan and report review is still necessary; it catches wiring, kinds and resource failures that the design review cannot.
- The review order is a discipline, not a compiler phase.

## Next

[Anti-patterns](/appendix/philosophy/anti-patterns) — the smells this review is looking for.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-023 | Add meaning and graph as value languages with one graph purpose per project. | 2026-11-06 | accepted | `tests/distribution/test_meaning_language.py` |
| D-038 | Keep author docs deep and separate from internal specs, with concept/reference paths. | 2026-11-05 | accepted | `STYLE.md`; `docs/content/appendix/developer/index.md` |
| D-039 | Guard the architecture with a contract test and a reviewer briefing. | 2026-11-02 | accepted | `tests/test_architecture.py`; `FRAMEWORK_STATE.md` |
