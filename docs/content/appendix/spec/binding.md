---
title: Binding specification
summary: A binding is the fulfilment between a relation and a record; it requires a meaning with a purpose and reads only a published relation.
section: spec
perspective: spec
subject: binding
spec: SPEC-006
order: 60
status: normative
verified: 2026-11-15
sources:
  - kg_build_system/distribution/languages/binding/service/public/builders.py
  - kg_build_system/distribution/languages/binding/service/_private/factories.py
  - kg_build_system/distribution/languages/binding/service/_private/symbols.py
  - kg_build_system/distribution/languages/binding/service/_private/transcription.py
  - kg_build_system/distribution/languages/binding/model/public/values.py
evidence:
  - tests/test_authoring_api.py
  - tests/distribution/test_binding_meaning.py
  - tests/distribution/test_typed_refs.py
  - docs/content/appendix/reference/bindings.md
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Bindings</span><a href="/appendix/subjects/binding">Overview</a><a href="/book/part-2/08-binding">Guide</a><a href="/appendix/spec/binding" class="active">Spec</a><a href="/appendix/reference/api">API</a><a href="/appendix/philosophy/binding-is-fulfilment">Philosophy</a><a href="/appendix/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

## Requirement

- **R1.** `node_binding` MUST target a concrete `Node`; `edge_binding` MUST target a concrete `Edge`. An abstract category, a template or the wrong component kind MUST be refused.
- **R2.** A binding MUST use exactly one form: direct `build_key` plus `properties`, or row-derived `rows` plus `bind`. Supplying both forms, or only half of either, MUST be refused.
- **R3.** `rows=` MUST accept a bindable `RelationRowSource` or a derived row-source value; it MUST refuse a `StageRowSource` and MUST NOT accept a `SourceRelation` or `DerivedRelation` class. `bind` MUST return `NodeValues` for a node and `EdgeValues` for an edge.
- **R4.** Every build key MUST be a present scalar `Selection`. A nullable, array, struct or bare-literal key MUST be refused. A key read from a nullable source field MUST be narrowed with `drop_null()` or deliberately defaulted.
- **R5.** Every declared property, including an inherited property, MUST be assigned exactly once. A missing, extra, bare-value or wrong-type property MUST be refused.
- **R6.** An edge binding MUST supply its own key, a `source_build_key` and a `target_build_key`. A null endpoint key MUST NOT ground the relation; the row MUST be dropped rather than given an invented endpoint.
- **R7.** A `source_node` or `target_node` token MUST be supplied when the declared side is abstract, MUST name a concrete node equal to or descending from that category, and MUST be an `endpoint(...)` token rather than a raw class. A concrete side MAY supply a token.
- **R8.** Binding identity MUST be the SHA-256 digest of the canonical binding document with `name` and `python_ref` removed, truncated to 16 hexadecimal characters. A `name` MAY prefix the identity string for display but MUST NOT enter the digest. Two bindings with the same identity MUST be refused.
- **R9.** One row the binding receives MUST produce one record. A binding MUST NOT aggregate, join, expand, deduplicate or merge; those decisions belong to a derived relation, row source or planner.
- **R10.** A binding MUST be the only declaration that imports both a data row source and a graph component; topology MUST NOT import data. Its `Meaning` MUST be present, MUST carry a `Purpose`, and MUST describe the fulfilment: it MUST name the record's use in a clause, then state how the relation answers that use — which relation, at which grain, identity and coverage — and where it falls short. A row recipe or a restatement of the record's purpose MUST NOT be accepted as a fulfilment. It owns neither the relation's meaning nor the record's meaning.
- **R11.** A binding MUST read only a published relation: a `SourceRelation` or a `DerivedRelation`. It MUST refuse a `StageRowSource` at construction and by the type checker. A source relation read directly by a binding MUST declare a contract, so the binding has a grain and identity to check.
- **R12.** The fulfilment MUST be judged on four checks: the relation grain matches the record grain, the relation carries the record identity, the relation coverage matches the record purpose, and the relation meaning fits the record meaning. A failed structural check MUST change the design, not the binding.

## Evidence

| Evidence | Proves |
| --- | --- |
| `tests/test_authoring_api.py` | `rows=` accepts a row source and refuses the declaration class; the bind callable receives a typed row and returns `NodeValues`. |
| `tests/distribution/test_binding_meaning.py` | A binding's meaning reaches the DTO and its rendered source, and carries a local purpose when supplied. |
| `tests/distribution/test_typed_refs.py` | A binding references its topology target, data source and expression operations as typed refs; the blueprint round-trips those references. |
| `docs/content/appendix/reference/bindings.md` | The factory arguments, key and property rules, endpoint tokens, identity inputs and duplicate refusal. |

The required-purpose, published-relation and stage-refusal rows are normative before their release tests; they are reviewed by reading the interface in [The relation contract](/appendix/developer/relation-contract), not by a green run.

## API

| Public name | Role |
| --- | --- |
| `node_binding(...)` | Maps one row context onto one concrete node. |
| `edge_binding(...)` | Maps one row context onto one concrete edge with two endpoint keys. |
| `rows` | A bindable published-relation or derived row source; a `StageRowSource` is refused. |
| `NodeValues(build_key, properties)` | The row-derived node key and property values. |
| `EdgeValues(build_key, source_build_key, target_build_key, properties)` | The row-derived edge key, endpoint keys and property values. |
| `NodeBinding[N]` / `EdgeBinding[E]` | Frozen binding results accepted by compile. |
| `BindingOptions(annotations=..., meaning=...)` | Portable metadata attached to one binding. |
| `PythonRef` | Module, qualified name and signature for Python mode; excluded from the digest. |
| `endpoint(target)` / `Endpoint[N]` | A concrete node token for an abstract declared side. |
| `build_key` | The present scalar selection that identifies one record. |
| `source_build_key` / `target_build_key` | The edge's endpoint selections, each a present scalar. |
| `name` | A display handle that prefixes identity but stays outside the digest. |
| `meaning` | One required declaration value describing the fulfilment; it must carry a purpose. |

## Limits

- A binding cannot merge or deduplicate records. Duplicate keys survive until a deduplication or merge planner runs.
- A property cannot be omitted because it is usually null. Nullability is declared at topology and supplied as a nullable selection.
- `alter_rows().drop_null()` filters the whole row, not one property. Use `default_to(...)` when the row remains meaningful without the value.
- Python mode carries a module and qualified name, not a callable body. It is an execution mode, not an escape from the declarative model.
- Binding identity includes the row plan and the fulfilment meaning. Two similar bindings over different grains or different purposes are different identities.
- Bindings are discovered as module-level values. A binding created inside a function or stored only in a container is not discovered.
- A binding has no description. `name` names a producer; annotations record facts about the binding.
- A simple one-to-one fulfilment is legal. A vacuous one is not: if the relation already carries the record's key, properties or endpoints, the design happened on the relation side and the binding is a copy.
- The framework cannot prove an honest fulfilment. The record-agnostic relation guard catches the mechanical copy; review judges whether coverage and meaning fit.
- A binding purpose is not a local purpose under the graph. It states the adequacy between two peer purposes.

## Rationale

The binding is the fulfilment where a published relation is offered to a record. Requiring one row, one target and one value per property keeps the grain explicit and prevents the fulfilment from becoming a second design. Requiring a meaning with a purpose makes the adequacy claim reviewable: a binding without one is plumbing. Identity over the canonical document makes every mapping reviewable and makes an accidental duplicate a refusal rather than a silent second producer.

## Next

Read the [binding subject](/appendix/subjects/binding) for the authoring-level view.
