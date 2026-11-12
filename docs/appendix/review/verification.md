---
title: Verification
summary: What this checkout measures, and where the framework docs disagree with the code.
section: review
order: 50
status: normative
verified: 2026-11-10
sources:
  - FRAMEWORK_STATE.md
  - kg_build_system/api.py
  - kg_build_system/distribution/interpreter/
  - docs/
  - tests/test_architecture.py
subject: verification
perspective: review
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Verification, limits and debugging</span><a href="/appendix/subjects/verification">Overview</a><a href="/book/part-4/04-limits-and-evidence">Guide</a><a href="/appendix/spec/verification">Spec</a><a href="/appendix/reference/failures">API</a><a href="/appendix/philosophy/explainability-is-authored">Philosophy</a><a href="/appendix/review/decisions" class="active">Review</a></div>
<!-- END GENERATED:views -->

> [!lede]
> Verification is a measurement with a date and a commit. Counts are a property of the checkout, not a promise about the next one; a disagreement between a doc and the code is evidence to record, not to smooth over.

## What it is

Two generated blocks carry the measurement. `status` runs the suite and pyright and names the source HEAD. `reference` compiles and executes the reference project and reports components, steps, connections and publications. A reader can reproduce both through [Install and verify](/book/part-1/02-a-first-build).

| Block | Measures | Read it for |
| --- | --- | --- |
| `status` | Tests, subtests, pyright, source HEAD | Whether this checkout passes. |
| `reference` | Components, steps, connections, records, publications | Whether the public path composes. |

## Rules

- Run the command before quoting a count; counts belong to the checkout.
- Report the measured pyright error count, not the hoped-for zero.
- Quote the source commit beside every count.
- Record a doc/code disagreement in the table; do not silently pick a winner.
- Treat the Open Targets suite as external evidence, not a check on this checkout.
- Generated blocks are written by `scripts/kb.py generate`; do not hand-edit them.
- A green local run is not a release gate while the repository has no CI.

## Evidence

<!-- BEGIN GENERATED:status -->
| Measure | Value |
| --- | --- |
| Test suite | 363 tests, 1957 subtests, 7.46s — passes |
| Static types | 0 errors |
| Source | `1b20440` (2026-11-11) |
| Docs build | `./docs-site/build.sh` from the repository root |
<!-- END GENERATED:status -->

<!-- BEGIN GENERATED:reference -->
| Measure | Reference build |
| --- | --- |
| Components | 6 |
| Steps | 60 |
| Connections | 90 |
| Published records | 21 nodes, 21 edges |
| Publications | import_bundle, meta_graph_document, write_result |
| Report | succeeded |
<!-- END GENERATED:reference -->

Known doc/code drift measured at the source HEAD in the status block:

| Doc claim | Measured in source |
| --- | --- |
| 259 tests and 1,858 subtests | 363 tests and 1,957 subtests |
| `GraphBlueprint` has four fields | Five fields, including `graph_declaration` |
| The linker order sometimes omits graph | `expressions`, `asset`, `data`, `topology`, `binding`, `graph` |
| The default languages sometimes omit graph | The default includes `GraphLanguage` |
| Codecs uniformly omit absent members | Asset governance and binding `rows` write explicit `null` |
| The renderer follows the linker order | Renderer: graph declaration, asset, topology, data, binding |
| A nullable generated value renders `T \| None` | It renders `Nullable[T]` |
| Provider version is 7 | The provider declares `VERSION = "8"` |
| Open Targets has 7 tests | External; not run in this checkout |

The stored document shape is described in [Documents](/appendix/reference/documents); the review consequence of a stale doc is [Drift](/appendix/review/drift).

## Limits

- Test duration and counts vary with the machine and dependency versions; the pass/fail result and pyright error count are the stable claims.
- Reference counts depend on the reference project and the selected planners. They are not a scale benchmark.
- Pyright analyses `kg_build_system` plus two authoring fixtures, not all of `tests/`, `reference_project/` or `legacy/`.
- The Open Targets suite belongs to another checkout and is not evidence here.
- No CI means the generated blocks can be stale between manual runs.
- A doc/code gap can be stale prose rather than a code defect; read the source before changing either.

The contract-suite groups and their gaps are in [Testing](/appendix/developer/testing).

## Next

[Drift](/appendix/review/drift) — which claims have outlived their sources.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-039 | Guard the architecture with a contract test and a reviewer briefing. | 2026-11-02 | accepted | `tests/test_architecture.py`; `FRAMEWORK_STATE.md`; `DESIGN_ISSUES.md` |
