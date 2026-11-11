---
title: Linking specification
summary: Linking indexes every declaration, walks the reachable closure and transcribes each symbol once.
section: spec
perspective: spec
subject: linking
spec: SPEC-009
order: 90
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/distribution/interpreter/service/_private/link.py
  - kg_build_system/distribution/interpreter/service/internal/adapters/kernel_linker.py
  - kg_build_system/kernel/model/public/language.py
  - kg_build_system/kernel/model/public/symbol.py
  - kg_build_system/distribution/model/public/refs.py
evidence:
  - tests/distribution/test_blueprint_linker.py
  - tests/distribution/test_graph_blueprint.py
  - tests/distribution/test_blueprint_source.py
  - tests/test_architecture.py
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Linking and the blueprint</span><a href="/subjects/linking">Overview</a><a href="/pipeline/link">Guide</a><a href="/spec/linking" class="active">Spec</a><a href="/reference/documents">API</a><a href="/philosophy/semantic-hierarchy">Philosophy</a><a href="/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

## Requirement

- **R1.** `BlueprintLinker.ORDER` MUST be exactly `expressions`, `asset`, `data`, `topology`, `binding`, `graph`. The first five languages MUST be present; `graph` MUST remain optional.
- **R2.** The linker MUST index every declaration before roots apply and MUST refuse a duplicate language name or a duplicate key within one language.
- **R3.** Roots MUST select languages, not individual declarations. The walk MUST expand the closure from authoring values through `get_references`.
- **R4.** A `Declaration` MUST NOT carry a key. `compute_key` MUST derive it, and a `Symbol` MUST carry key, kind, value, and references.
- **R5.** `transcribe` MUST run once per reachable declaration, dependencies first, and its produced key MUST equal the indexed key.
- **R6.** The linker MUST refuse an unknown reference and a reference cycle.
- **R7.** `GraphBlueprint` MUST have exactly five fields: `graph`, `data`, `assets`, `bindings`, and `graph_declaration`. The declaration field MUST be optional.
- **R8.** Every cross-symbol field MUST be a typed ref encoded as `[language, role, *key]`. A bare cross-symbol string MUST NOT appear.
- **R9.** A codec round trip MUST be judged by canonical document equality, not source text equality. Decoding MUST NOT validate the blueprint.
- **R10.** `blueprint_to_source` MUST render in the order graph declaration, asset, topology, data, binding.

## Evidence

| Evidence | Proves |
| --- | --- |
| `tests/distribution/test_blueprint_linker.py` | Root selection, closure, duplicate key, unknown reference, and cycle refusals. |
| `tests/distribution/test_graph_blueprint.py` | The five-field blueprint and the optional graph declaration. |
| `tests/distribution/test_blueprint_source.py` | Render order and canonical round-trip equality. |
| `tests/test_architecture.py` | Language and DTO boundaries that keep linking independent. |

## API

| Public name | Role |
| --- | --- |
| `BlueprintLinker` | The kernel linker adapter for graph blueprints. |
| `ORDER` | The fixed six-language transcription order. |
| `create_blueprint` | Composes the default languages and linker. |
| `GraphBlueprint` | The frozen five-field semantic model. |
| `Declaration` | An authoring candidate with no key. |
| `Symbol` | A linked key, kind, value, and resolved references. |
| `SymbolRef` | A language-and-key pair naming one symbol. |
| `SymbolContext` | Read-only access to symbols already transcribed. |
| `Key` | One symbol key within a language. |
| `Language` | The discover, key, transcribe, and render protocol. |
| `blueprint_to_document` / `blueprint_from_document` | Canonical codec. |
| `blueprint_to_source` | Renders the blueprint back to authoring source. |
| `NodeRef` / `EdgeRef` / `RelationRef` / `FieldRef` / `PropertyRef` / `AssetRef` / `OperationRef` | Role-typed cross-symbol references. |

## Limits

- Linking is whole-namespace, not incremental. A declaration that no root reaches contributes nothing.
- Roots select languages, not keys. There is no per-declaration include list.
- A linked symbol is not a delivered type. The blueprint carries layer DTOs, not the symbol graph.
- The graph declaration is optional. A project without one has no project-level graph semantics.
- `get_identity` is dormant on the normal path, so its multi-claim refusal is not a routine check.
- Linking reads no source data and compiles no steps. It resolves declarations into a validated semantic model.

## Rationale

The linker is the one stage allowed to decide what a build contains, which keeps the [pipeline contracts](/review/contracts) from collapsing build into compile or execute. Indexing everything and transcribing only the closure makes reachability explicit while preserving the authored dependency order. Typed refs keep the delivered model semantic rather than a symbol table, so consumers see roles instead of linker internals.

## Next

Read the [linking subject](/subjects/linking) for the pipeline-level view.
