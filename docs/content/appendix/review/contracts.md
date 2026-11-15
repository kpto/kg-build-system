---
title: Contracts
summary: Seventeen invariants that keep meaning, build, compile and execute from collapsing into one another.
section: review
order: 20
status: normative
verified: 2026-11-15
sources:
  - kg_build_system/kernel/model/public/symbol.py
  - kg_build_system/kernel/service/public/pipeline.py
  - kg_build_system/distribution/interpreter/
  - docs/content/appendix/developer/system-design.md
  - tests/kernel/test_toolchain_flow.py
subject: architecture
perspective: review
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Kernel, distribution and contracts</span><a href="/appendix/subjects/architecture">Overview</a><a href="/book/part-4/03-architecture-and-tests">Guide</a><a href="/appendix/spec/architecture">Spec</a><a href="/appendix/reference/api">API</a><a href="/appendix/philosophy/review-top-down">Philosophy</a><a href="/appendix/review/architecture" class="active">Review</a></div>
<!-- END GENERATED:views -->

> [!lede]
> A contract is a refusal with a test or a named review path behind it. Meaning, build, compile and execute stay separate only while every row below holds; each row names the page that owns the rule.

## What it is

The architecture says where code belongs; the contracts say what a change must not break there. Read them as a review checklist, not an API reference. [Architecture](/appendix/review/architecture) owns the boundary; this page owns the promises that cross it.

| Verb | Input | Output | It must not |
| --- | --- | --- | --- |
| Build | a namespace of declarations through a linker | one linked model | execute a step |
| Compile | the linked model | a `WorkflowPlan` | build a blueprint |
| Execute | the plan and an output directory | a `WorkflowReport` | plan a step |

## Rules

| # | Invariant | Refusal or test | Owner |
| --- | --- | --- | --- |
| 1 | Build links declarations, compile plans, execute runs. `compile` never builds; `execute` never plans. | `tests/kernel/test_toolchain_flow.py`; compile of an unbuilt model is refused, and an executor receives a plan, not a namespace. | [Pipeline](/book/part-3/02-planning) |
| 2 | A declaration has no key; `compute_key` derives it. A symbol carries key, kind, value and references. | `tests/kernel/test_kernel.py`; a duplicate key is refused and `Declaration` has no key field. | [Link](/book/part-3/01-linking-and-blueprint) |
| 3 | The linker owns roots, closure and order; the kernel does not. | `tests/distribution/test_blueprint_linker.py`; an unknown ref is refused and a reference cycle fails ordering. | [Link](/book/part-3/01-linking-and-blueprint) |
| 4 | The blueprint is the semantic model; the symbol graph is linker IR. | `tests/distribution/test_blueprint_dto.py`; a symbol ID or Python path in the blueprint is refused. | [Blueprint](/book/part-3/01-linking-and-blueprint) |
| 5 | Cross-symbol fields are role-typed refs, never bare strings. | `tests/distribution/test_typed_refs.py`; a string where `NodeRef`, `FieldRef` or `PropertyRef` is required is a type error. | [Blueprint](/book/part-3/01-linking-and-blueprint) |
| 6 | `Selection[T]` is the only authoring value. `Field[T]` never declares absence; the owner supplies nullability. | `tests/test_authoring_api.py`, `tests/typecheck/authoring.py`; an optional-union annotation on `Field` is a static type error. | [Data](/book/part-2/03-source-and-rows) |
| 7 | A row source is a value; a derived relation pins exactly one; `alter_rows` is one-shot. | `tests/test_authoring_api.py`; `DerivedRelation()` without a source is refused, and a second effect on one handle is absent. | [Grain](/book/part-2/05-grain-and-projections) |
| 8 | Topology declares meaning without importing a source relation; a binding is the only place that imports both sides. | `tests/test_architecture.py`; a topology-to-data import is refused, and an unbound endpoint fails. | [Bindings](/book/part-2/08-binding) |
| 9 | One `Meaning` type is attached to declarations; the graph declaration requires the root purpose, graph-local purposes narrow it, and a relation purpose is domain-level. | `tests/distribution/test_meaning_language.py`; a second graph declaration is refused, and a limitation without a purpose is refused. | [Meaning](/book/part-2/01-meaning-and-purpose) |
| 10 | A planner emits; an executor owns one exact instruction kind and declares its resources. | `tests/kernel/test_kernel.py`; a duplicate kind, an unfed input or an unread output is refused, and a planner that executes fails. | [Extend](/book/part-4/01-the-kernel-and-extension) |
| 11 | The runtime owns resource providers; a toolchain has no `resources` field. | `tests/kernel/test_runtime_resources.py`; a missing resource or a listener error fails the run. | [Execute](/book/part-3/03-execution-and-outputs) |
| 12 | Generation is upstream and inert; the build never invokes it. | `tests/test_codegen_discovery.py`; an asset carries no generation field and `create_blueprint` never calls the generator. | [Generation](/book/part-2/09-generation) |
| 13 | Steps declare artifact ports; consumers declare types or patterns; priority orders assembly, not data dependency. | `tests/kernel/test_composition_contract.py`; a pattern consumer sees every matching producer, adding a producer leaves its declaration unchanged, and two same-type producers are refused. | [Composition](/book/part-2/07-composition) |
| 14 | A relation is a contract: `Definition` states grain and identity, `Meaning` states purpose, claims and limitations, and a field's `FieldDefinition` belongs to the field. A derived relation requires a contract; a source relation may omit it until a binding reads it. | `tests/distribution/test_relation_contract.py`; an incomplete contract, an empty definition, an unknown identity output and a derived relation without a purpose are refused, and the contract and field definitions round-trip through the document. | [Data](/book/part-2/03-source-and-rows) |
| 15 | A stage is private: it has a definition, no contract meaning and internal visibility; it is plan lineage, never a binding consumer. | `tests/distribution/test_relation_contract.py`; `StageOptions` has no meaning member, a stage row source is refused by a binding, and the stage transcribes with internal visibility and no meaning. | [Grain](/book/part-2/05-grain-and-projections) |
| 16 | A published relation is record-agnostic; a binding requires a meaning with a purpose that states the fulfilment. | `tests/distribution/test_authoring_api.py` and `tests/test_reference_structure.py`; a meaning-less binding is refused and no published relation names a record key or property. | [Bindings](/book/part-2/08-binding) |
| 17 | No schema version or migration path. | No version field exists; a plan document is recompiled, not migrated. | [Limits](/appendix/review/limits) |

## Evidence

`tests/kernel/test_toolchain_flow.py` runs the three verbs in order; `tests/test_architecture.py` enforces the imports behind row 8; `tests/kernel/test_kernel.py` covers rows 2 and 10; `tests/kernel/test_runtime_resources.py` covers row 11; `tests/kernel/test_composition_contract.py` covers row 13. Rows 14 to 16 guard the relation contract, stage privacy and binding fulfilment; no release test exercises them yet, so they are reviewed against the specifications they cite. A rule without a current test is still normative, but it is reviewed by reading rather than by a green run.

Artifacts that cross a boundary are documents before they are objects. Their shapes are in [Documents](/appendix/reference/documents).

## Limits

- The table describes the default distribution. A custom language or executor inherits these contracts only by using kernel types and the same refusals.
- A test proves a refusal exists, not that its message explains it.
- Data quality, planner performance and target behaviour are module limits, not pipeline contracts.
- A plan is ephemeral. There is no schema version, no compatibility negotiation and no migration path; recompile against the current model.
- `compile` is pure with respect to the blueprint, but not with respect to configuration: runtime fields and plan context can change the steps.

The DTO and planning boundary is in [Data and expressions](/appendix/developer/data-and-expressions).

## Next

[Assemble the blueprint](/book/part-3/01-linking-and-blueprint) — where linking stops and semantic validation starts.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-004 | Make compile a pure consumer of a separately assembled blueprint. | 2026-11-03 | accepted | `tests/kernel/test_toolchain_flow.py`; `docs/content/appendix/reference/compile.md` |
| D-005 | Make the workflow contract step-centric and instruction-based, with exact instruction kinds. | 2026-11-03 | accepted | `tests/kernel/test_kernel.py`; `docs/content/appendix/reference/compile.md` |
| D-006 | Use Key-backed role types for every identity that crosses pipeline boundaries. | 2026-11-04 | accepted | `tests/pipeline/test_pipeline_identity.py`; `docs/content/appendix/reference/compile.md` |
| D-008 | Let the linker own root selection and resolve the authoring reference closure before transcription. | 2026-11-04 | accepted | `tests/distribution/test_blueprint_linker.py`; `docs/content/appendix/developer/system-design.md#declarations-symbols-and-the-linker` |
| D-014 | Unify authoring around `Selection[T]` with owner-derived nullability. | 2026-11-05 | accepted | `tests/test_authoring_api.py`; `docs/content/book/part-2/04-values-and-nullability.md` |
| D-023 | Add meaning and graph as value languages with one graph purpose per project. | 2026-11-06 | accepted | `tests/distribution/test_meaning_language.py`; `docs/content/book/part-2/01-meaning-and-purpose.md` |
