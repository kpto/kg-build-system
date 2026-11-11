---
title: Link declarations
summary: The linker indexes every declaration, walks the reachable closure and transcribes each symbol once, dependencies first.
section: pipeline
order: 10
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/distribution/interpreter/service/_private/link.py
  - kg_build_system/distribution/interpreter/service/internal/adapters/kernel_linker.py
  - kg_build_system/kernel/model/public/language.py
  - kg_build_system/kernel/model/public/symbol.py
  - docs/developer/system-design.md
subject: linking
perspective: guide
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Linking and the blueprint</span><a href="/subjects/linking">Overview</a><a href="/pipeline/link" class="active">Guide</a><a href="/spec/linking">Spec</a><a href="/reference/documents">API</a><a href="/philosophy/semantic-hierarchy">Philosophy</a><a href="/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

> [!lede]
> Linking is the only stage that decides what a build contains. Declarations are candidates; roots seed a walk; only the reachable closure becomes symbols.

## What it is

`build(namespace)` is the kernel's whole contribution: it hands the declared languages and the namespace to the linker. The kernel does not discover, key, order or transcribe.

The distribution's `BlueprintLinker` does five things:

| Stage | Result |
| --- | --- |
| Index | Every declaration is keyed within its language. |
| Select roots | Root languages become the starting points. |
| Walk | `get_references` on authoring values extends the closure. |
| Order | A dependencies-first pass fixes transcription order. |
| Transcribe | Each reachable declaration becomes one `Symbol`. |

A `Declaration` has no key; `compute_key` derives it. A `Symbol` carries key, kind, value and references. The symbol graph is linker IR, not the delivered model: the blueprint is assembled from the transcribed values.

## Rules

- `BlueprintLinker.ORDER` is exactly `expressions`, `asset`, `data`, `topology`, `binding`, `graph`. The first five are required; `graph` is optional. A namespace may declare at most one `Graph`.
- Roots default to every language. When roots are given, they seed only those languages, so the graph declaration appears only when `graph` is named.
- Every declaration is indexed before roots apply. A duplicate key within a language is refused, including a duplicate on an unreachable declaration.
- `get_references` receives the authoring value and returns direct dependencies. The linker expands the closure and overwrites `Symbol.references` with its resolved edges; what `transcribe` returned is advisory.
- `transcribe` runs once per reachable declaration, dependencies first, with a read-only `SymbolContext`. The produced key must equal the indexed key.
- The closure walk refuses a reference to a symbol outside the index. Ordering is one global depth-first pass; a revisit while a node is open is a reference cycle.
- `get_identity` exists but is dormant on the normal path. Languages build references from authoring metadata instead of asking a resolver to identify values.
- The linker refuses a duplicate language name, a missing required language, an unknown root language, a duplicate key, an unknown reference, a reference cycle and more than one graph.

## Example

```python
from pathlib import Path

from kg_build_system import create_blueprint

blueprint = create_blueprint(namespace_path=Path("reference_project"))
```

`create_blueprint` composes the six languages and `BlueprintLinker()` and calls `build(namespace)`. For a narrower closure, construct the toolchain with `BlueprintLinker(roots=("binding",))`; linking then keeps declarations reachable from bindings, and includes the graph declaration only when `graph` is also named.

## Limits

- A declaration that no root reaches contributes nothing. Linking is whole-namespace, not incremental.
- Roots select languages, not individual keys. There is no per-declaration include list.
- A linked symbol is not a delivered type. The blueprint carries layer DTOs, not the symbol graph.
- The graph declaration is optional. A project without one has no project-level graph semantics.
- `get_identity` does not participate, so the multi-claim identity refusal is not a normal-path check.
- Linking resolves the closure, assembles the model and validates the blueprint; it reads no source data and compiles no steps.

## Next

[Assemble the blueprint](/pipeline/blueprint) — what the transcribed DTOs become.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-008 | Let the linker own root selection and resolve the authoring reference closure before transcription. | 2026-11-04 | accepted | `tests/distribution/test_blueprint_linker.py` |
| D-009 | Use one verb per transformation; make render the reverse of transcribe and move codecs out of Language. | 2026-11-03 | accepted | `tests/test_naming.py` |
| D-004 | Make compile a pure consumer of a separately assembled blueprint. | 2026-11-03 | accepted | `tests/kernel/test_toolchain_flow.py` |
