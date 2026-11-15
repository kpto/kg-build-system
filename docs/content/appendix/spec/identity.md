---
title: Identity specification
summary: Keys, role-typed references and canonical documents carry every identity across build, compile and execute.
section: spec
perspective: spec
subject: identity
spec: SPEC-015
order: 150
status: normative
verified: 2026-11-15
sources:
  - kg_build_system/kernel/model/public/key.py
  - kg_build_system/kernel/model/public/symbol.py
  - kg_build_system/kernel/model/public/workflow.py
  - kg_build_system/distribution/model/public/refs.py
  - kg_build_system/distribution/interpreter/service/_private/codec.py
evidence:
  - tests/pipeline/test_pipeline_identity.py
  - tests/distribution/test_typed_refs.py
  - tests/distribution/test_graph_blueprint.py
  - tests/distribution/test_blueprint_source.py
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Identity, references and documents</span><a href="/appendix/subjects/identity">Overview</a><a href="/book/part-3/01-linking-and-blueprint">Guide</a><a href="/appendix/spec/identity" class="active">Spec</a><a href="/appendix/reference/documents">API</a><a href="/appendix/philosophy/semantic-hierarchy">Philosophy</a><a href="/appendix/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

## Requirement

- **R1.** Every pipeline identity MUST be a role type over `Key`, and a `Key` MUST be a tuple of string segments. A formatted display string MUST NOT be parsed back into an identity.
- **R2.** `SymbolRef` MUST pair one language name with one `Key`. A typed reference MUST wrap a `SymbolRef`, and its document MUST be `[language, role, *key segments]`.
- **R3.** `StepId` MUST contain exactly one component id and one step name. `Component.version` MUST NOT enter the `StepId`, and a dotted name MUST remain one key segment.
- **R4.** `OpeningId` MUST include direction, step, and opening name, so an input and an output with one name remain distinct.
- **R5.** `ArtifactType` MUST contain at least two concrete segments and MUST NOT contain a wildcard. `ArtifactPattern` MUST match `*` within any segment and `**` only as the final segment.
- **R6.** `InstructionKind` MUST contain exactly one operation and one engine and MUST compare by exact equality.
- **R7.** A binding identity digest MUST be computed from the canonical binding document with `debug_name` and `python_ref` removed. A present `debug_name` MUST prefix the digest but MUST NOT enter it.
- **R8.** The blueprint document MUST carry top-level `graph`, `data`, `assets`, and `bindings`, with optional `graph_declaration`. The `data` member MUST expose `source_relations` and `derived_relations`; neither key MAY be named `relations` or `projections`. The plan document MUST carry `components`, `steps`, `connections`, and `provenance`. The report document MUST carry `published_artifacts`, `recovered_failures`, `unresolved_failures`, and `provenance`.
- **R9.** A codec round trip MUST produce canonical-document equality, not original text equality. Decoding MUST NOT validate the model, and the encoder MUST preserve the omit-versus-null rule for each member.

## Evidence

| Evidence | Proves |
| --- | --- |
| `tests/pipeline/test_pipeline_identity.py` | Step, opening, artifact, instruction, and document identities; duplicate and direction refusals. |
| `tests/distribution/test_typed_refs.py` | Every role type wraps a `SymbolRef` and round-trips `[language, role, *key]`. |
| `tests/distribution/test_graph_blueprint.py` | The blueprint document shape and the optional graph declaration round trip. |
| `tests/distribution/test_blueprint_source.py` | Rendered source recreates the blueprint from identity-bearing declarations. |

The two data keys and the stage visibility are normative before their release test; they are reviewed by reading the interface in [The relation contract](/appendix/developer/relation-contract).

## API

| Name | Shape | Carries |
| --- | --- | --- |
| `Key` | Tuple of strings | Hierarchical identity with child, prefix, and pattern operations. |
| `SymbolRef` | `(language, key)` | One symbol in one language. |
| `NodeRef`, `EdgeRef`, `RelationRef`, `FieldRef`, `PropertyRef`, `AssetRef`, `OperationRef` | `SymbolRef` plus role | A typed reference whose document is `[language, role, *key]`. |
| `StepId` | `(component, name)` | One logical step; excludes component version. |
| `OpeningId` | `(step, direction, name)` | One input or output port. |
| `ArtifactType` | `Key` with at least two concrete segments | One concrete artifact. |
| `ArtifactPattern` | `Key` with wildcard segments | One accepted artifact shape. |
| `InstructionKind` | `(operation, engine)` | One exact dispatch key. |
| `binding_identity` | Canonical document digest | A binding's stable identity, including its meaning. |
| Blueprint, plan, report documents | Top-level member sets | The canonical cross-boundary artifacts; the data member carries the two relation keys. |

## Limits

- Keys carry no arity or segment rules. `Key.from_document` checks only that every item is a string, so the owning role type states its own arity.
- Display names and `__str__` are for reading; no codec parses them.
- `FieldRef` and `PropertyRef` split the final key segment at its last dot. The split is a display convenience, not a second identity.
- A binding digest is truncated to 16 hexadecimal characters. A debug name changes the identity string without changing the digest.
- Canonical equality ignores key order, whitespace, and omitted optional members; it does not compare original bytes.
- Decoding does not re-link, cross-validate, or check plan executability. Validation belongs to the pipeline.
- A final `**` matches zero or more remaining segments; without `**`, pattern and key lengths must agree.
- Omit-versus-null is asymmetric: some absent members are omitted, while required-valued members are written as explicit `null`.

## Rationale

Identity is authored, not guessed: a reference names its language, role, and key, and no reader has to parse a delimiter string to recover it. Role types keep the semantic hierarchy explicit while a canonical document keeps the wire shape stable. This follows [explainability is authored](/appendix/philosophy/explainability-is-authored): the model states what each reference means.

## Next

[Identity subject](/appendix/subjects/identity) — the subject index entry for keys, typed references, and canonical documents.
