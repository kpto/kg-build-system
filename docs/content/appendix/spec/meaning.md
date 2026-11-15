---
title: Meaning specification
summary: One root purpose, local purposes that narrow it, contextless claims, and limitations owned by a purpose.
section: spec
perspective: spec
subject: meaning
spec: SPEC-007
order: 70
status: normative
verified: 2026-11-15
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
<div class="kb-views"><span class="kb-views-subject">Semantics and graph purpose</span><a href="/appendix/subjects/meaning">Overview</a><a href="/book/part-2/01-meaning-and-purpose">Guide</a><a href="/appendix/spec/meaning" class="active">Spec</a><a href="/appendix/reference/api">API</a><a href="/appendix/philosophy/semantic-hierarchy">Philosophy</a><a href="/appendix/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

## Requirement

- **R1.** A `Claim` MUST state an authored, contextless assertion about the subject. It MUST hold regardless of purpose and MUST NOT own limitations.
- **R2.** A `Limitation` MUST appear only inside a `Purpose`. A `Purpose` MUST own only `Limitation` values.
- **R3.** A `Semantics` value MUST carry at most one `Purpose` and any number of `Claim` values. It MUST carry at least one claim or one purpose.
- **R4.** A graph declaration MUST attach a `Semantics` value carrying a purpose. A `GraphOptions.semantics` value MUST NOT be absent and MUST have a purpose.
- **R5.** A project MUST declare zero or one `Graph`. A second graph declaration MUST be refused.
- **R6.** A non-graph declaration MAY attach a `Semantics` value with a purpose. That local purpose MUST narrow the graph purpose and MUST NOT redefine it.
- **R7.** A declaration MUST carry at most one purpose. If it needs two incompatible purposes, the declaration MUST be split or one use MUST become a limitation.
- **R8.** A project with any local purpose MUST declare a graph purpose. Claims MAY be attached without a graph declaration; local purposes MAY NOT.
- **R9.** A node MUST accept at most one `NodeLabel`, and an edge MUST accept at most one `EdgeLabel`. A label of the wrong kind MUST be refused.
- **R10.** Semantics MUST remain separate from annotations and descriptions. A description MUST NOT become a claim, and an annotation MUST NOT become a limitation.
- **R11.** A category description MUST stay local to the category and MUST NOT flow to a child declaration. Child semantics MUST be attached explicitly.
- **R12.** Every unit text MUST be non-empty.
- **R13.** The graph declaration MUST become the optional fifth blueprint field `graph_declaration`, carrying the same `Semantics` document shape as every other declaration. A project with no graph declaration MUST publish `graph_declaration` as `None`.
- **R14.** A unit's text MUST answer the question its type owns. A definition, identity, grain, cardinality or measurement MUST be a claim; a prohibition, absence, exclusion or inference ceiling MUST be a limitation; an expected use MUST be a purpose.
- **R15.** A limitation MUST state the boundary, not the measurement that motivates it. When the measurement is authored, it MUST be a claim beside the same purpose or declaration.
- **R16.** A declaration with no positive use MUST carry claims only. A purpose MUST NOT be authored to satisfy the shape. Two declarations MAY share a purpose text only when their expected use is identical; a different subject or operation MUST have a different purpose.
- **R17.** A binding purpose MUST state the mapping it performs, and a data purpose MUST NOT be the parent of a topology purpose.
- **R18.** A declaration MUST author its semantics value at the declaration. A structural helper MAY accept a `Semantics` value and pass it through; it MUST NOT accept purpose, claim or limitation text. Meaning MUST NOT be assembled by a project-local helper.

## Evidence

| Evidence | Proves |
| --- | --- |
| `tests/distribution/test_semantics_language.py` | Unit shape, required graph purpose, one-purpose rule and one-graph refusal. |
| `tests/distribution/test_topology_semantics.py` | Node and edge fragments, local purposes, labels, and local category descriptions. |
| `tests/distribution/test_data_semantics.py` | Table, struct, projection, and field fragment attachment. |
| `tests/distribution/test_binding_semantics.py` | Binding fragments and the absence of per-property binding semantics. |

## API

| Public name | Role |
| --- | --- |
| `Claim` | An authored, contextless assertion about the subject. |
| `Limitation` | What a purpose does not authorize. |
| `Purpose` | One expected use of the subject, owning its limitations. |
| `Semantics` | The one meaning value attached to a declaration; an optional purpose plus claims. |
| `Graph` | The optional project graph declaration. |
| `GraphOptions` | Graph name, description, and required semantics carrying the root purpose. |
| `NodeLabel` / `EdgeLabel` | One portable label of the matching component kind. |

## Limits

- There is no truth evaluation, revision, resolution, or cross-unit consistency check. The blueprint publishes authored units for consumers to compose.
- Unit fit is a review obligation. The type system enforces where a unit may sit, not whether its text answers the question that unit owns.
- There is one root purpose and at most one purpose per declaration. A narrower use becomes a local purpose; an excluded inference becomes a limitation.
- A graph declaration is not a node, edge, asset, or reference participant.
- A `TableGroupOptions` carries no fragment, and a binding carries one fragment for the whole mapping.
- Units have no inheritance and no identity. A category fragment and a declaration fragment remain separate attachments.
- A shared data declaration has one local purpose, not one purpose per consumer. Its purpose is not the parent of a topology purpose; provenance is a separate axis.
- There is no `GraphSemantics` type and no `Frame` type. The graph declaration is special because of its declaration rule, not because of a separate semantics value.

## Rationale

The [semantic hierarchy](/appendix/philosophy/semantic-hierarchy) reads one root purpose downward: topology states what a record is and what it is for, and data and binding fragments state how this implementation supplies it. Making purpose singular at the graph keeps every local purpose accountable to one root without copying its text. Claims stay contextless so a reviewer can separate what the model asserts from where it applies.

## Next

Read the [meaning subject](/appendix/subjects/meaning) for the declaration-level view.
