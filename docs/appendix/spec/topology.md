---
title: Topology specification
summary: Topology declares concrete nodes, directed edges, categories, templates, and flat typed properties before any row arrives.
section: spec
perspective: spec
subject: topology
spec: SPEC-005
order: 50
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/distribution/languages/topology/model/public/declarations.py
  - kg_build_system/distribution/languages/topology/service/_private/class_creation.py
  - kg_build_system/distribution/languages/topology/service/_private/transcription.py
  - kg_build_system/distribution/languages/topology/model/public/options.py
  - kg_build_system/distribution/languages/topology/model/public/values.py
evidence:
  - tests/distribution/test_topology_semantics.py
  - tests/test_reference_build.py
  - docs/appendix/reference/topology.md
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Topology</span><a href="/appendix/subjects/topology">Overview</a><a href="/book/part-2/04-topology-and-bindings">Guide</a><a href="/appendix/spec/topology" class="active">Spec</a><a href="/appendix/reference/api">API</a><a href="/appendix/philosophy/meaning-first">Philosophy</a><a href="/appendix/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

## Requirement

- **R1.** `Node` MUST declare a concrete, bindable and terminal component. `AbstractNode` MUST declare a graph-visible category that produces no records and MUST NOT be a binding target.
- **R2.** `Edge[Source, Target]` MUST declare a directed relation between two node-side declarations. Direction MUST come from the type-argument order and MUST NOT be stored as a property.
- **R3.** `AbstractEdge[Source, Target]` MUST declare a relationship family. A concrete child MAY keep or narrow the endpoints; a widened endpoint MUST be refused. An `endpoint(...)` token MUST be required only when the declared side is abstract and MUST name a concrete descendant.
- **R4.** `PropertySlot[T]` MUST accept a scalar or a flat, homogeneous array of non-null scalars. A nested array, an array of structs or a bare struct MUST be refused, and `T | None` MUST declare an optional value.
- **R5.** `property()` MUST default the external name to snake case and the description to the adjacent docstring; an explicit `name` or `description` MUST override the default. Property names MUST be unique within a component.
- **R6.** `NodeTemplate` and `EdgeTemplate` MUST be inert: they MUST NOT become graph components, receive a logical name or key, become binding targets or become edge endpoints. Their property slots and annotations MUST flow to the host.
- **R7.** The base order MUST be templates first, at most one abstract category parent in the middle, and the terminal concrete base last. A second abstract parent or a parent of the wrong kind MUST be refused.
- **R8.** A concrete component MUST be terminal and MUST NOT be subclassed. A category or concrete component MUST NOT inherit from a concrete component.
- **R9.** A component MUST carry at most one label of its matching kind; a node label on an edge or an edge label on a node MUST be refused. A component name MUST be unique across nodes and edges.
- **R10.** A category's label and description MUST stay local and MUST NOT flow to a concrete child. Template annotations MUST flow, and a category's semantics MUST remain its own attachment.

## Evidence

| Evidence | Proves |
| --- | --- |
| `tests/distribution/test_topology_semantics.py` | Node, edge and property fragments reach the topology DTO; a template contributes its semantics; a category keeps its own and does not share it with a child. |
| `tests/test_reference_build.py` | The reference hierarchy of templates, categories and concrete nodes and edges compiles into a blueprint and publishes a successful build. |
| `docs/appendix/reference/topology.md` | The base order, endpoint narrowing, template options, label rules, property shape and category reachability. |

## API

| Public name | Role |
| --- | --- |
| `Node` | Concrete terminal component; the only node binding target. |
| `AbstractNode` | Graph-visible category; no records and not bindable. |
| `Edge[Source, Target]` | Concrete directed relation; endpoint order is the direction. |
| `AbstractEdge[Source, Target]` | Relationship category; a child keeps or narrows the pair. |
| `PropertySlot[T]` | One declared property slot over a graph value type. |
| `property(...)` | Declares a slot with name, description, annotations and semantics. |
| `NodeTemplate` / `EdgeTemplate` | Inert mixins that share slots and annotations. |
| `NodeOptions` / `EdgeOptions` | Component name, description, annotations and semantics. |
| `NodeOptionsTemplate` / `EdgeOptionsTemplate` | Identity-free options for a template. |
| `NodeLabel` / `EdgeLabel` | One portable label of the matching component kind. |
| `Endpoint` / `endpoint(target)` | A concrete node token for an abstract edge side. |
| `GraphScalar` / `GraphArray` / `GraphValue` | The accepted property value vocabulary. |

## Limits

- An abstract category produces no records. Its meta-graph count is the sum of its descendants' records.
- A template cannot declare identity, a key or a binding, and it never enters the blueprint.
- A property cannot hold a nested object. Reify the nested value as nodes and edges, or as a flat scalar when the meaning is genuinely flat.
- A concrete component is terminal. A declaration that mixes node and edge lineage, or inherits a concrete component, is refused.
- Two concrete components in different families may share a property name; they do not share the slot.
- A category with no bound descendant and no bound edge endpoint is not published, because nothing in the graph refers to it.
- Topology declares no cardinality and reads no data. Multiplicity comes from the binding key and the source grain.

## Rationale

Topology is the design surface: it states what a record is before any row supplies a value. Categories share meaning while templates share structure, and keeping those roles separate stops a data shortcut from becoming model design. Reading the hierarchy downward makes each concrete component accountable to the category above it without copying that category's label or description.

## Next

Read the [topology subject](/appendix/subjects/topology) for the declaration-level view.
