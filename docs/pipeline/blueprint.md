---
title: Assemble the blueprint
summary: The blueprint is the semantic model of one graph, carried as graph, data, assets, bindings and an optional graph declaration.
section: pipeline
order: 20
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/distribution/interpreter/model/public/graph_blueprint.py
  - kg_build_system/distribution/model/public/refs.py
  - kg_build_system/distribution/interpreter/service/_private/codec.py
  - kg_build_system/distribution/interpreter/service/_private/create.py
  - docs/developer/system-design.md
subject: linking
perspective: guide
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Linking and the blueprint</span><a href="/subjects/linking">Overview</a><a href="/pipeline/blueprint" class="active">Guide</a><a href="/spec/linking">Spec</a><a href="/reference/documents">API</a><a href="/philosophy/semantic-hierarchy">Philosophy</a><a href="/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

> [!lede]
> The blueprint is the handoff between declarations and execution. It keeps graph meaning and row meaning, and drops the linker's working state.

## What it is

`GraphBlueprint` is the public handle for one linked graph. It has exactly five fields:

| Field | Type | Holds |
| --- | --- | --- |
| `graph` | `GraphPartDTO` | nodes and edges |
| `data` | `DataPartDTO` | structs, relations and projections |
| `assets` | `AssetPartDTO` | logical source assets |
| `bindings` | tuple of `NodeBindingDTO` / `EdgeBindingDTO` | row-to-record mappings |
| `graph_declaration` | `GraphDeclarationDTO` or `None` | project-level graph semantics |

Language DTOs are internal names. The blueprint is a frozen public value: no owner, service or Python authoring path crosses with it.

Every field that crosses a symbol boundary is a typed ref from `distribution/model/public/refs.py`: `NodeRef`, `EdgeRef`, `RelationRef`, `FieldRef`, `PropertyRef`, `AssetRef` and `OperationRef`. A ref document is `[language, role, *key segments]`. No bare cross-symbol string is allowed. Expressions are inline fragments, not symbols; their leaves are typed refs.

<figure class="kb-plate">
  <img src="/_assets/artifacts.svg" alt="Declarations become a symbol graph, then a blueprint, then a workflow plan, then a report.">
  <figcaption>The blueprint is the semantic middle. It keeps graph and row meaning; the symbol graph stays behind.</figcaption>
</figure>

## Rules

- `graph` holds `GraphPartDTO(nodes, edges)`. `data` holds `DataPartDTO(structs, relations, projections)`. `assets` holds `AssetPartDTO`. `bindings` is a tuple of node and edge bindings.
- `graph_declaration` is optional. A project may carry zero graph declarations, in which case the field is `None`.
- `blueprint_to_document` and `blueprint_from_document` are the codec. In the document, `graph` and `data` are always objects; `assets` and `bindings` are arrays; `graph_declaration` is omitted when absent.
- Decode accepts the legacy `binding` key for bindings and assets as `{"assets": [...]}`. Decoding does not validate: it reconstructs whatever the document states.
- Round trip means blueprint to rendered source to `create_blueprint` to an equivalent blueprint, judged by canonical document equality. It does not preserve the original text, class names, module layout or callable bodies.
- `blueprint_to_source` renders in the order graph declaration, assets, topology, data, binding. That order is not the linker's order.
- Assembly validates the blueprint before returning it. A document decoded with `blueprint_from_document` does not pass through that validation.

## Example

```python
from pathlib import Path

from kg_build_system import create_blueprint
from kg_build_system.distribution.interpreter.service.internal import (
    blueprint_from_document,
    blueprint_to_document,
)

blueprint = create_blueprint(namespace_path=Path("reference_project"))
document = blueprint_to_document(blueprint)
restored = blueprint_from_document(document)

print(document.keys())                       # graph, data, assets, bindings
print(len(blueprint.graph.nodes))            # topology nodes
print(blueprint.graph_declaration is None)   # zero graph declarations is legal
assert blueprint_to_document(restored) == document
```

The document form and its layer members are specified in [Documents and codecs](/reference/documents).

## Limits

- A blueprint is semantic, not executable. It has no components, steps, connections or runtime fields.
- It carries no source text, class names, module layout or callable bodies. Round trip equivalence is canonical document equality, not byte equality.
- Decoding is not validation. A hand-edited document can produce a blueprint that assembly would refuse.
- Codec compatibility covers the tested document shapes, not every legacy or future form.
- `assets` and `bindings` may both be empty. The blueprint does not require a source or a mapping.
- Layer DTOs are internal names. Consumers should use the public handle and its typed refs, not layer internals.

## Next

[Compile a plan](/pipeline/plan) — how the semantic model becomes executable steps.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-004 | Make compile a pure consumer of a separately assembled blueprint. | 2026-11-03 | accepted | `tests/kernel/test_toolchain_flow.py` |
| D-006 | Use Key-backed role types for every identity that crosses pipeline boundaries. | 2026-11-04 | accepted | `tests/pipeline/test_pipeline_identity.py` |
| D-031 | Build the blueprint from symbols and typed refs; group feature code into modules and type execution resources. | 2026-11-04 | accepted | `tests/distribution/test_typed_refs.py` |
