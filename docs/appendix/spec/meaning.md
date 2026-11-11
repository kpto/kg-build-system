---
title: Meaning specification
summary: One project purpose, contextless claims, and frames that own every limitation.
section: spec
perspective: spec
subject: meaning
spec: SPEC-007
order: 70
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/distribution/languages/semantics/model/public/units.py
  - kg_build_system/distribution/languages/graph/model/public/options.py
  - kg_build_system/distribution/languages/graph/model/public/declarations.py
  - kg_build_system/distribution/languages/annotations/model/public/labels.py
  - kg_build_system/distribution/interpreter/model/public/graph_blueprint.py
evidence:
  - tests/distribution/test_semantics_language.py
  - tests/distribution/test_topology_semantics.py
  - tests/distribution/test_data_semantics.py
  - tests/distribution/test_binding_semantics.py
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Semantics and graph purpose</span><a href="/appendix/subjects/meaning">Overview</a><a href="/book/part-2/05-meaning-and-purpose">Guide</a><a href="/appendix/spec/meaning" class="active">Spec</a><a href="/appendix/reference/api">API</a><a href="/appendix/philosophy/semantic-hierarchy">Philosophy</a><a href="/appendix/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

## Requirement

- **R1.** A `Claim` MUST state a contextless fact that holds regardless of purpose or frame. A `Limitation` MUST appear only inside a `Frame`, and a `Purpose` MUST appear only inside `GraphSemantics`.
- **R2.** A `Semantics` fragment MUST carry at least one claim or frame and MUST NOT carry a purpose. Its frames are read under the one graph purpose.
- **R3.** A `GraphSemantics` value MUST carry exactly one `Purpose`; its claims MAY be empty. A `GraphOptions.semantics` value MUST be a `GraphSemantics` carrying that purpose.
- **R4.** A declaration MUST attach `Semantics`, never `GraphSemantics`. The graph meaning root MUST belong to the graph declaration alone.
- **R5.** A project MUST declare zero or one `Graph`. A second graph declaration MUST be refused.
- **R6.** A node MUST accept at most one `NodeLabel`, and an edge MUST accept at most one `EdgeLabel`. A label of the wrong kind MUST be refused.
- **R7.** Semantics MUST remain separate from annotations and descriptions. A description MUST NOT become a claim, and an annotation MUST NOT become a limitation.
- **R8.** A category description MUST stay local to the category and MUST NOT flow to a child declaration. Child semantics MUST be attached explicitly.
- **R9.** Every unit text MUST be non-empty, and a `Frame` MUST own only `Limitation` values.
- **R10.** The graph declaration MUST become the optional fifth blueprint field `graph_declaration`, and a project with no graph declaration MUST publish `graph_declaration` as `None`.

## Evidence

| Evidence | Proves |
| --- | --- |
| `tests/distribution/test_semantics_language.py` | Unit shape, required purpose, and one-graph refusal. |
| `tests/distribution/test_topology_semantics.py` | Node and edge fragments, labels, and local category descriptions. |
| `tests/distribution/test_data_semantics.py` | Table, struct, projection, and field fragment attachment. |
| `tests/distribution/test_binding_semantics.py` | Binding fragments and the absence of per-property binding semantics. |

## API

| Public name | Role |
| --- | --- |
| `Claim` | A contextless statement. |
| `Limitation` | A condition a reader must know inside a frame. |
| `Frame` | The scope that owns limitations. |
| `Purpose` | The one expected use of the graph. |
| `Semantics` | A declaration fragment with claims and frames. |
| `GraphSemantics` | The meaning root: claims plus one purpose. |
| `Graph` | The optional project graph declaration. |
| `GraphOptions` | Graph name, description, and required semantics. |
| `NodeLabel` / `EdgeLabel` | One portable label of the matching component kind. |

## Limits

- There is no truth evaluation, revision, resolution, or cross-unit consistency check. The blueprint publishes authored units for consumers to compose.
- There is no second purpose and no declaration-level purpose. A narrower reading becomes a limitation inside a frame.
- A graph declaration is not a node, edge, asset, or reference participant.
- A `TableGroupOptions` carries no fragment, and a binding carries one fragment for the whole mapping.
- Units have no inheritance and no identity. A category fragment and a declaration fragment remain separate attachments.

## Rationale

The [semantic hierarchy](/appendix/philosophy/semantic-hierarchy) reads one purpose downward: topology states what a record is, and data and binding fragments state how this implementation supplies it. Making purpose graph-only keeps every lower statement accountable to one root without copying its text. Claims stay contextless so a reviewer can separate what the model asserts from where it applies.

## Next

Read the [meaning subject](/appendix/subjects/meaning) for the declaration-level view.
