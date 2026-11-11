---
title: Binding specification
summary: A binding maps one row context to one concrete record, supplies every property, and fixes a stable identity.
section: spec
perspective: spec
subject: binding
spec: SPEC-006
order: 60
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/distribution/languages/binding/service/public/builders.py
  - kg_build_system/distribution/languages/binding/service/_private/factories.py
  - kg_build_system/distribution/languages/binding/service/_private/symbols.py
  - kg_build_system/distribution/languages/binding/service/_private/transcription.py
  - kg_build_system/distribution/languages/binding/model/public/values.py
evidence:
  - tests/test_authoring_api.py
  - tests/distribution/test_binding_semantics.py
  - tests/distribution/test_typed_refs.py
  - docs/appendix/reference/bindings.md
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Bindings</span><a href="/appendix/subjects/binding">Overview</a><a href="/book/part-2/04-topology-and-bindings">Guide</a><a href="/appendix/spec/binding" class="active">Spec</a><a href="/appendix/reference/api">API</a><a href="/appendix/philosophy/binding-is-the-seam">Philosophy</a><a href="/appendix/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

## Requirement

- **R1.** `node_binding` MUST target a concrete `Node`; `edge_binding` MUST target a concrete `Edge`. An abstract category, a template or the wrong component kind MUST be refused.
- **R2.** A binding MUST use exactly one form: direct `build_key` plus `properties`, or row-derived `rows` plus `bind`. Supplying both forms, or only half of either, MUST be refused.
- **R3.** `rows=` MUST accept a row-source value and MUST NOT accept a `Table` or `Projection` class. `bind` MUST return `NodeValues` for a node and `EdgeValues` for an edge.
- **R4.** Every build key MUST be a present scalar `Selection`. A nullable, array, struct or bare-literal key MUST be refused. A key read from a nullable source field MUST be narrowed with `drop_null()` or deliberately defaulted.
- **R5.** Every declared property, including an inherited property, MUST be assigned exactly once. A missing, extra, bare-value or wrong-type property MUST be refused.
- **R6.** An edge binding MUST supply its own key, a `source_build_key` and a `target_build_key`. A null endpoint key MUST NOT ground the relation; the row MUST be dropped rather than given an invented endpoint.
- **R7.** A `source_node` or `target_node` token MUST be supplied when the declared side is abstract, MUST name a concrete node equal to or descending from that category, and MUST be an `endpoint(...)` token rather than a raw class. A concrete side MAY supply a token.
- **R8.** Binding identity MUST be the SHA-256 digest of the canonical binding document with `debug_name` and `python_ref` removed, truncated to 16 hexadecimal characters. A `debug_name` MAY prefix the identity string for display but MUST NOT enter the digest. Two bindings with the same identity MUST be refused.
- **R9.** One row the binding receives MUST produce one record. A binding MUST NOT aggregate, join, expand, deduplicate or merge; those decisions belong to a projection, row source or planner.
- **R10.** A binding MUST be the only declaration that imports both a data row source and a graph component; topology MUST NOT import data. Its optional semantics fragment MUST be a `Semantics`, MUST NOT be `GraphSemantics`, and MUST describe the mapping rather than the record's meaning.

## Evidence

| Evidence | Proves |
| --- | --- |
| `tests/test_authoring_api.py` | `rows=` accepts a row source and refuses the declaration class; the bind callable receives a typed row and returns `NodeValues`. |
| `tests/distribution/test_binding_semantics.py` | A binding carries one semantics fragment into the DTO and its rendered source, omits it when absent, and rejects the graph meaning root. |
| `tests/distribution/test_typed_refs.py` | A binding references its topology target, data source and expression operations as typed refs; the blueprint round-trips those references. |
| `docs/appendix/reference/bindings.md` | The factory arguments, key and property rules, endpoint tokens, identity inputs and duplicate refusal. |

## API

| Public name | Role |
| --- | --- |
| `node_binding(...)` | Maps one row context onto one concrete node. |
| `edge_binding(...)` | Maps one row context onto one concrete edge with two endpoint keys. |
| `NodeValues(build_key, properties)` | The row-derived node key and property values. |
| `EdgeValues(build_key, source_build_key, target_build_key, properties)` | The row-derived edge key, endpoint keys and property values. |
| `NodeBinding[N]` / `EdgeBinding[E]` | Frozen binding results accepted by compile. |
| `BindingOptions(annotations=..., semantics=...)` | Portable metadata attached to one binding. |
| `PythonRef` | Module, qualified name and signature for Python mode; excluded from the digest. |
| `endpoint(target)` / `Endpoint[N]` | A concrete node token for an abstract declared side. |
| `build_key` | The present scalar selection that identifies one record. |
| `source_build_key` / `target_build_key` | The edge's endpoint selections, each a present scalar. |
| `debug_name` | A display handle that prefixes identity but stays outside the digest. |
| `semantics` | One declaration fragment describing the mapping. |

## Limits

- A binding cannot merge or deduplicate records. Duplicate keys survive until a deduplication or merge planner runs.
- A property cannot be omitted because it is usually null. Nullability is declared at topology and supplied as a nullable selection.
- `alter_rows().drop_null()` filters the whole row, not one property. Use `default_to(...)` when the row remains meaningful without the value.
- Python mode carries a module and qualified name, not a callable body. It is an execution mode, not an escape from the declarative model.
- Binding identity includes the row plan. Two similar bindings over different grains are different identities.
- Bindings are discovered as module-level values. A binding created inside a function or stored only in a container is not discovered.
- A binding has no description. `debug_name` names a producer; annotations record facts about the binding.

## Rationale

The binding is the seam where a row becomes a record. Requiring one row, one target and one value per property keeps the grain explicit and prevents the seam from becoming a second design. Identity over the canonical document makes every mapping reviewable and makes an accidental duplicate a refusal rather than a silent second producer.

## Next

Read the [binding subject](/appendix/subjects/binding) for the authoring-level view.
