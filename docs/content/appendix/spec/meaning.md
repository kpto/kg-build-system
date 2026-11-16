---
title: Meaning specification
summary: One graph purpose, per-declaration meaning on two axes, contextless claims, and limitations owned by a purpose.
section: spec
perspective: spec
subject: meaning
spec: SPEC-007
order: 70
status: normative
verified: 2026-11-15
sources:
  - kg_build_system/distribution/languages/meaning/model/public/units.py
  - kg_build_system/distribution/languages/graph/model/public/options.py
  - kg_build_system/distribution/languages/graph/model/public/declarations.py
  - kg_build_system/distribution/languages/annotations/model/public/labels.py
  - kg_build_system/distribution/interpreter/model/public/graph_blueprint.py
evidence:
  - tests/distribution/test_meaning_language.py
  - tests/distribution/test_graph_language.py
  - tests/distribution/test_topology_meaning.py
  - tests/distribution/test_data_meaning.py
  - tests/distribution/test_binding_meaning.py
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Meaning and graph purpose</span><a href="/appendix/subjects/meaning">Overview</a><a href="/book/part-2/01-meaning-and-purpose">Guide</a><a href="/appendix/spec/meaning" class="active">Spec</a><a href="/appendix/reference/api">API</a><a href="/appendix/philosophy/semantic-hierarchy">Philosophy</a><a href="/appendix/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

## Requirement

- **R1.** A `Claim` MUST state an authored, contextless assertion about the subject. It MUST hold regardless of purpose and MUST NOT own limitations.
- **R2.** A `Limitation` MUST appear only inside a `Purpose`. A `Purpose` MUST own only `Limitation` values.
- **R3.** A `Meaning` value MUST carry at most one `Purpose` and any number of `Claim` values. It MUST carry at least one claim or one purpose.
- **R4.** A graph declaration MUST attach a `Meaning` value carrying a purpose. `GraphOptions.meaning` MUST NOT be absent and MUST have a purpose.
- **R5.** A project MUST declare zero or one `Graph`. A second graph declaration MUST be refused.
- **R6.** A node, edge or property MAY attach a `Meaning` value with a purpose. That purpose MUST narrow the graph purpose and MUST NOT redefine it.
- **R7.** A derived relation's contract MUST carry a `Meaning` whose purpose is domain-level. A source relation MAY attach one; a purpose attached there is domain-level too. That purpose MUST be statable without the graph's purpose, a node, an edge or a binding, and it MUST NOT be read as a narrowing of the graph purpose.
- **R8.** A declaration MUST carry at most one purpose. If it needs two incompatible purposes, the declaration MUST be split or one use MUST become a limitation.
- **R9.** A project with any graph-local purpose MUST declare a graph purpose. Claims MAY be attached without a graph declaration; a relation purpose is not a graph-local purpose and MUST NOT require one.
- **R10.** A node MUST accept at most one `NodeLabel`, and an edge MUST accept at most one `EdgeLabel`. A label of the wrong kind MUST be refused.
- **R11.** Meaning MUST remain separate from annotations. An annotation MUST NOT become a limitation, and a label MUST NOT stand in for a meaning.
- **R12.** A category meaning MUST stay local to the category and MUST NOT flow to a child declaration. Child meaning MUST be attached explicitly.
- **R13.** Every unit text MUST be non-empty.
- **R14.** The graph declaration MUST become the optional fifth blueprint field `graph_declaration`, carrying a `MeaningDTO` with the same document shape as every other declaration. A project with no graph declaration MUST publish `graph_declaration` as `None`.
- **R15.** A unit's text MUST answer the question its type owns. A definition, identity, grain, cardinality or measurement MUST be a claim; a prohibition, absence, exclusion or inference ceiling MUST be a limitation; an expected use MUST be a purpose.
- **R16.** A limitation MUST state the boundary, not the measurement that motivates it. When the measurement is authored, it MUST be a claim beside the same purpose or declaration.
- **R17.** A declaration with no positive use MUST carry claims only. A purpose MUST NOT be authored to satisfy the shape. Two declarations MAY share a purpose text only when their expected use is identical; a different subject or operation MUST have a different purpose.
- **R18.** A binding purpose MUST state the fulfilment it performs: which relation satisfies which record purpose, at which grain, identity and coverage, and where that fulfilment falls short. A binding MUST NOT omit its purpose, and a binding purpose MUST NOT be the parent of either side's purpose.
- **R19.** A declaration MUST author its meaning value at the declaration. A structural helper MAY accept a `Meaning` value and pass it through; it MUST NOT accept purpose, claim or limitation text. Meaning MUST NOT be assembled by a project-local helper.
- **R20.** A declaration that states no meaning MUST pass the `Omitted` marker explicitly; `None` MUST NOT be an authoring value. The graph declaration, a published contract and a binding MUST NOT accept `Omitted`.

## Evidence

| Evidence | Proves |
| --- | --- |
| `tests/distribution/test_meaning_language.py` | Unit shape, one-purpose rule, DTO and source round trip for the meaning value. |
| `tests/distribution/test_graph_language.py` | Required graph meaning with a purpose, one-graph refusal, and the graph declaration round trip. |
| `tests/distribution/test_topology_meaning.py` | Node and edge meaning fragments, local purposes, labels, and local category meanings. |
| `tests/distribution/test_omitted.py` | Explicit `Omitted` at every optional site, refusal where a declaration cannot opt out, and no meaning in the blueprint. |
| `tests/distribution/test_data_meaning.py` | Source relation, struct, derived relation and field meaning attachment. |
| `tests/distribution/test_binding_meaning.py` | Binding meaning and the absence of per-property binding meaning. |

## API

| Public name | Role |
| --- | --- |
| `Claim` | An authored, contextless assertion about the subject. |
| `Limitation` | What a purpose does not authorize. |
| `Purpose` | One expected use of the subject, owning its limitations. |
| `Meaning` | The one meaning value attached to a declaration; an optional purpose plus claims. |
| `Omitted` | The explicit marker for a declaration that states no meaning. |
| `is_omitted(value)` | Whether a value is the `Omitted` marker. |
| `Graph` | The project's at most one graph declaration. |
| `GraphOptions` | Graph name and the required meaning carrying the root purpose; it cannot opt out. |
| `NodeLabel` / `EdgeLabel` | One portable label of the matching component kind. |

## Limits

- There is no truth evaluation, revision, resolution, or cross-unit consistency check. The blueprint publishes authored units for consumers to compose.
- Unit fit is a review obligation. The type system enforces where a unit may sit, not whether its text answers the question that unit owns.
- There is one graph purpose and at most one purpose per declaration. A narrower graph use becomes a local purpose; an excluded inference becomes a limitation.
- A relation purpose is a peer of the graph purpose, not a narrowing of it. A relation may serve several consumers.
- A graph declaration is not a node, edge, asset, or reference participant.
- A `SourceRelationGroupOptions` carries no meaning, and a binding carries one meaning for the whole mapping.
- Units have no inheritance and no identity. A category fragment and a declaration fragment remain separate attachments.
- A shared relation has one domain purpose, not one purpose per consumer. Provenance is a separate axis.
- The graph declaration is special because its purpose is required, not because it carries a different value type.

## Rationale

The [semantic hierarchy](/appendix/philosophy/semantic-hierarchy) reads one root purpose downward through the record axis: topology states what a record is and what it is for, and bindings state how a relation fulfils it. The relation axis carries its own domain purpose, which is stated beside a definition rather than under the graph. Making purpose singular at the graph keeps every graph-local purpose accountable to one root without copying its text, while a relation remains usable by any consumer. Claims stay contextless so a reviewer can separate what the model asserts from where it applies.

## Next

Read the [meaning subject](/appendix/subjects/meaning) for the declaration-level view.
