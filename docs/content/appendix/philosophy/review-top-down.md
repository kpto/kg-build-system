---
title: Review top-down
summary: "Read purpose, topology and semantics before bindings, data and plan; a bottom-up review passes a meaningless graph."
section: philosophy
order: 60
status: normative
verified: 2026-11-10
sources:
  - AGENTS.md
  - reference_project/
  - docs/content/appendix/developer/system-design.md
  - kg_build_system/distribution/interpreter/service/_private/validation.py
---

> [!lede]
> A plan can be correct and a graph can be meaningless. Review in the order the meaning is built: purpose, topology, semantics, bindings, data, then plan. A bottom-up review checks the plumbing and misses the design.

## What it is

| Step | Read | Pass condition |
| --- | --- | --- |
| 1 | Graph purpose and claims | One `Graph`; one purpose; claims the records can serve. |
| 2 | Topology | Node/edge meaning, direction, properties and category/template use are deliberate. |
| 3 | Semantics | Each fragment is at the right level and consistent with the purpose; limits are stated. |
| 4 | Bindings | One record per row; present keys; every property; endpoints only where needed. |
| 5 | Data | Asset, table, selection, grain and projection names describe the design, not the recipe. |
| 6 | Plan and report | Components, kinds, connections and publications support the design; they do not define it. |

If step 1 or 2 is empty, stop. Execution cannot supply a design that was never declared.

## Rules

- Review the purpose first. A graph with no `Graph` has no published purpose; say so rather than assuming one.
- Read topology as meaning: a node is a thing, an edge is a directed assertion, a property is a value the record carries. A missing edge is as important as a wrong one.
- Check that every lower fragment is consistent with the purpose. The framework does not check this for you.
- Review names before SQL. A domain name at the blueprint level and a technical name in the plan is healthy; the reverse is a leak.
- Review limits. What does the graph not answer? A limit at the right frame is a feature; a missing limit is a hidden claim.
- Review provenance. Can a consumer trace a record to its asset, relation and declaration? A plan step is not a source dataset.
- Do not accept “it compiles”, “the report succeeded” or “the counts are right” as a design review. Those are execution facts.

## Example

The reference project, reviewed top-down:

| Step | Result | Evidence |
| --- | --- | --- |
| Purpose | **fail** | No `Graph` declaration; no published purpose. |
| Topology | pass | Six concrete node types, six concrete edge types, categories and templates with deliberate direction. |
| Semantics | partial | Descriptions, labels and provenance annotations; no `Semantics` fragment and no graph purpose. |
| Bindings | pass | Fourteen bindings; keys narrowed; properties supplied; endpoint tokens only where needed. |
| Data | pass | One asset, five tables, two named projections; the defect grain is explicit. |
| Plan | pass | Six components, sixty steps, ninety connections; the run publishes records and a report. |

The graph is useful and structurally sound. It is not a fully explainable design, because the purpose and the semantic fragments are missing. The review names that gap; the build cannot.

## Limits

- There is no semantic lint, no consistency check across levels and no automated “is this meaningful” test.
- The reviewer supplies judgment. The framework supplies the structure, the references and the published artifacts.
- A pass on topology does not imply a pass on data; a source can be unable to supply a declared property. Read both.
- A reference project’s choices are evidence, not a template. Its missing `Graph` is a limit to name, not a pattern to copy.
- A plan/report review is still necessary; it catches wiring, kinds and resource failures that the design review cannot.
- The review order is a discipline, not a compiler phase.

## Next

[Anti-patterns](/appendix/philosophy/anti-patterns) — the smells this review is looking for.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-023 | Add semantics and graph as value languages with one graph purpose per project. | 2026-11-06 | accepted | `tests/distribution/test_semantics_language.py` |
| D-038 | Keep author docs deep and separate from internal specs, with concept/reference paths. | 2026-11-05 | accepted | `STYLE.md`; `docs/content/appendix/developer/index.md` |
| D-039 | Guard the architecture with a contract test and a reviewer briefing. | 2026-11-02 | accepted | `tests/test_architecture.py`; `FRAMEWORK_STATE.md` |
