# Knowledge Graph Build System — MVP Specification

## 1. Purpose

Build a modular knowledge graph compilation system that separates:

1. the desired graph topology,
2. declarative bindings to that topology, and
3. execution against a concrete build target.

The system evolves the Open Targets adapter's typed, declarative approach, but
is source-agnostic, target-agnostic, and SQL-first. The MVP is a Python monorepo
with DuckDB as its compute engine.

## 2. Design principles

- **Separate meaning, declaration, and execution.** Topology is abstract and
  independent of acquisition. Binding is an abstract declarative expression:
  it may name concrete data locations and connection parameters, but contains
  no adapters, execution code, or target behaviour.
- **Declarative where possible.** Models and bindings have portable structured
  representations, initially YAML and JSON.
- **One canonical intermediate representation (IR).** Python declarations and
  structured files must produce the same validated models.
- **Typed by default, dynamic when useful.** Python table-schema classes enable
  static checking, while string-based dynamic bindings remain available as an
  explicit escape hatch.
- **SQL-first execution.** Bindings compile to DuckDB SQL rather than executing
  row-by-row Python transformations.
- **Target capabilities are explicit.** Target-specific features are namespaced
  annotations; they do not alter core graph semantics.

## 3. Layer 1: abstract KG topology

Defines what the resulting graph means, independently of its source data.

### Core concepts

- Node type: stable name, identifier policy, properties, and constraints.
- Edge type: stable name, source and target node types, properties, direction,
  and cardinality where known.
- Property: name, scalar or collection type, nullability, and documentation.
- Annotation: a semantic or target-specific class instance, such as
  `OntologyTerm(...)` or `Neo4jIndex()`. An element holds an ordered list of
  annotations.

Reusable annotation templates may hold common configuration. For example,
`SO = Ontology("http://purl.obolibrary.org/obo/so.owl", id="so")` is
serialised once, and `SO("0000704")` creates an annotation that references the
`so` template rather than repeating its URI.

Annotations cover both semantic mappings and target hints, for example:

- ontology term or CURIE mapping;
- provenance and licence metadata;
- Neo4j indexes, uniqueness constraints, or full-text indexes on individual
  properties;
- target-specific label or naming overrides.

Target annotations use namespaced keys such as `ontology.term` and
`neo4j.index` so unknown annotations can be preserved without being interpreted
by the core model.

### Representation

The MVP source of truth is Python class declarations. Node and edge properties
are typed `PropertyRef[T]` class attributes, so a downstream binding can
reference `Target.symbol` directly as a typed property reference. The serialised JSON
representation is produced from those classes; the list-based IR is an internal
compiled form rather than the Python authoring API. JSON/YAML import and
bidirectional synchronisation are future capabilities.

## 4. Layer 2: abstract declarative binding

Defines a declarative acquisition and transformation expression that produces
the nodes, edges, identifiers, and properties declared by the topology model.

### Binding primitives

Bindings operate on a small logical data model:

- input relation, including file paths, URLs, connection details, and format
  options;
- dataset or table within an input;
- column, including nested structs and collections;
- logical data type and nullability;
- relational operations such as filtering, projection, joining, grouping, and
  collection expansion.

Input relations are leaf expressions in the binding rather than a separate
source model. A binding may therefore be self-contained, including the physical
locations and connection parameters needed to acquire its data. Secrets should
be referenced indirectly through runtime configuration or environment-backed
credentials rather than embedded in a portable binding.

Bindings contain no data-access implementation or target behavior. The compute
layer interprets their input and transformation expressions.

### Typed schemas

Python classes represent the logical tables and columns used by a binding. In
the MVP they are authored manually. Bindings that reference them receive IDE
completion and static validation of:

- dataset and column existence;
- expression input/output types;
- node and edge property compatibility;
- identifier and endpoint types.

The same binding model also permits dynamic references such as
`column("targets.id")`. This mode requires no generated schema or structured
binding file and is validated at build or inspection time instead of by a
static type checker.

Generating source-schema classes from external metadata is part of the future
code generation design, not the MVP. Topology declarations themselves are
already statically referenceable in the MVP.

### Binding declaration

A binding selects a topology element and declares:

- input relations and connection options;
- joins, filters, projections, and collection expansion;
- expressions for IDs, endpoints, labels, and properties;
- deduplication and null-handling policies;
- provenance information.

The portable expression subset must compile deterministically to DuckDB SQL.
Python user-defined transformations are a later extension and are explicitly
outside the portable MVP subset.

## 5. Future design: model synchronization and code generation

Code generation is not part of the MVP. The model and IR boundaries should,
however, be designed so that it can be added later without changing their
meaning or public contracts.

Topology, logical table schemas, and bindings share versioned IR schemas.
Tooling should eventually support both directions:

- Python model → YAML/JSON;
- YAML/JSON → generated typed Python;
- external schema metadata → generated Python table-schema classes.

Synchronization should be explicit and fast, with a watch mode for
near-real-time regeneration during development. Generated artifacts contain
provenance and a content hash. If both authoring views change since the last
synchronization, the tool reports a conflict rather than silently choosing one.

Future code generation will not attempt arbitrary Python round-tripping. Only
declarations made through the supported model API are serializable;
handwritten runtime logic remains Python-only.

## 6. Layer 3: compute and target execution

The compute layer consumes validated topology and binding IRs plus build-target
and runtime configuration. It owns integration with concrete storage systems,
DuckDB, and output technologies.

### Pipeline

1. Load and validate models.
2. Resolve binding input expressions and detect target capabilities.
3. Check topology-to-binding coverage and type compatibility.
4. Compile each binding into a DuckDB SQL plan.
5. Execute plans with projection and filter pushdown.
6. Stream normalized node and edge records to the target writer.
7. Apply supported target annotations such as indexes and constraints.
8. Emit a build report containing counts, diagnostics, provenance, and plan
   fingerprints.

### Target interface

Targets consume a stable graph record protocol and declare their capabilities.
The initial MVP target should be a file-based interchange output. Neo4j is the
first database target and demonstrates target annotations. Unsupported target
annotations produce clear diagnostics according to a configurable strictness
policy.

DuckDB owns relational work including scans, joins, filters, unnests,
aggregations, casts, and deterministic expression evaluation. The execution
layer should expose generated SQL and query plans for inspection.

## 7. Proposed monorepo layout

```text
packages/
  topology/          # graph types, annotations, IR and validation
  binding/           # acquisition and transformation expressions and type rules
  compute/           # physical data access, DuckDB execution and target writers
demo-pipeline/
  topology/          # demonstration graph definition
  bindings/          # source-to-graph bindings
  data/               # small reproducible input datasets
  config/            # runtime credentials, compute and target configuration
  output/            # produced graph artifacts and build report
tests/
```

Packages may begin as modules in one distribution if that reduces MVP overhead;
the boundaries above are architectural contracts, not a requirement for early
independent publishing. The MVP interface is a Python API. Data-access
implementations and build-target integrations belong to `compute`; neither
requires a separate top-level package.

The dependency direction is `compute` → `binding` → `topology`. Neither
declarative layer depends on `compute`.

## 8. MVP scope

The MVP proves one end-to-end workflow with:

- class-based Python authoring for topology, with JSON export from the compiled
  topology IR;
- Parquet and CSV physical inputs;
- manually authored typed column references and dynamic references;
- row selection, projection, joins, filters, expressions, and list expansion;
- DuckDB SQL compilation and execution;
- file output and a minimal Neo4j target;
- model validation, SQL inspection, and reproducible build reports;
- a self-contained demonstration pipeline that defines, binds, and produces a
  small graph demonstrating ontology and target annotations.

## 9. Deferred concerns

- distributed execution and scheduling;
- incremental and change-data-capture builds;
- arbitrary Python transformations inside SQL plans;
- a graphical model editor;
- automatic migration of deployed target schemas;
- optimization across independently authored bindings;
- support for every graph database or remote source;
- model synchronization, table-schema generation, and Python/YAML round trips.

## 10. Success criteria

The PoC succeeds when the demonstration graph and its bindings validate,
invalid typed column references are caught before execution, bindings compile
to inspectable DuckDB SQL, and the demonstration pipeline produces equivalent
file and Neo4j graph outputs with the declared annotations applied where
supported.
