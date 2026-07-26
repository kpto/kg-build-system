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

- **Separate meaning, data contracts, bindings, and execution.** Topology is
  abstract and independent of acquisition. Logical data tables describe stable
  input contracts; bound tables supply their physical locations and runtime
  configuration. Bindings express graph mappings over those declared values,
  but contain no adapters, execution code, or target behaviour.
- **Declarative where possible.** Models and bindings have portable structured
  representations, initially YAML and JSON.
- **One canonical intermediate representation (IR).** Python declarations and
  structured files must produce the same validated models.
- **Typed by default, dynamic when useful.** Python logical-table and field
  declarations enable static checking, while dynamic fields remain available as
  an explicit escape hatch.
- **SQL-first execution.** Bindings compile to DuckDB SQL rather than executing
  row-by-row Python transformations.
- **Target capabilities are explicit.** Target-specific features are namespaced
  annotations; they do not alter core graph semantics.

## 3. Layer 0: specification contracts

`Specification` is the shared, lowest-level class-based declaration concept.
It is a reusable declarative structural contract: a subclass states the shape
and meaning of something without acquiring data or executing a build. Topology
components, table shapes, projections, and other class-based declaration layers
may inherit it and reuse a contract through inheritance when re-specifying it.

The shared layer deliberately has no knowledge of topology properties, table
fields, binding expressions, or other layer-specific authoring constructs:

```python
class Specification(ABC):
    """A reusable declarative structural contract."""


class Specifier[T](ABC):
    """A typed declarative way to specify a value of type T."""


type SpecInput[T] = Specifier[T] | T
```

`SpecInput[T]` is the annotation of a declared contract member. It accepts a
typed, layer-specific `Specifier[T]` or a literal `T`. For example,
`PropertyRef[str]` and a binding `Expression[str]` are both
`Specifier[str]`, while a direct string is the literal case. A `Specifier` is
not itself a structural contract; it specifies one member of such a contract.

`Specification` need not itself be a dataclass. Each declaration layer owns
its own `dataclass_transform` configuration and field specifiers, allowing the
type checker to synthesize that layer's constructor without coupling the shared
layer to `PropertyRef`, `Field`, or any other descriptor. Framework metadata is
declared as `ClassVar` or left unannotated so that it is not a constructor
parameter. Standard `dataclass_transform` cannot filter generated constructor
parameters solely by the `SpecInput[...]` annotation; the layer's registered
field-specifier convention provides the intentionally loose authoring rule.

## 4. Layer 1: abstract KG topology

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

The MVP source of truth is Python class declarations. The topology layer
provides a `GraphComponent(Specification)` base configured with
`@dataclass_transform(field_specifiers=(PropertyRef, IdentifierRef))`.
Node and edge members are typed `SpecInput[T]` and use `PropertyRef[T]` or
`IdentifierRef[T]` in their class bodies, so a downstream binding can reference
`Target.symbol` directly as a typed property reference. The serialised JSON
representation is produced from those classes; the list-based IR is an internal
compiled form rather than the Python authoring API. JSON/YAML import and
bidirectional synchronisation are future capabilities.

Any declared node or edge can serve as a template. A subclass inherits its
properties, identifier, description, and annotations; it may add properties or
override an inherited property or identifier with the same attribute name.

## 5. Layer 2: abstract declarative binding

Defines a declarative acquisition and transformation expression that produces
the nodes, edges, identifiers, and properties declared by the topology model.

### Data contracts and bound inputs

Bindings operate over a small logical data model:

```text
Table → Field → DataType
```

A reusable table shape is a `TableContract(Specification)` with explicitly
named member declarations. The data layer owns its `field` specifier and
configures `TableContract` with its own
`@dataclass_transform(field_specifiers=(field,))`; the shared specification
layer does not import either construct. Members are typed `SpecInput[T]` and
may be scalar, optional, nested `Struct` values, or collections. A Python
attribute is a typed authoring handle for the
contract field name, allowing a source field such as `studyId` to be represented
as `study_id: SpecInput[str] = field(name="studyId")`.
`@table_template(name=..., description=...)` optionally attaches stable
template metadata without changing the reusable class. `@table(name=...)`
consumes one such class and returns a final generated table class typed as
`type[TableDeclaration[T]]`, a distinct named concrete table whose schema is
`T`.

Only generated `type[TableDeclaration[T]]` table classes are accepted by table
groups and source bindings. This makes binding a reusable shape, or inheriting
a concrete table, a static type error. Generated table metadata is exposed
through typed class methods, including `schema_type()`, `table_name()`,
`template_name()`, and `template_description()`.

`TableGroup` provides a named hierarchy of concrete table declarations and
nested groups.
Table and group names form a catalog path and can be referenced by source
bindings. Physical acquisition is separate: `bind_source` accepts either a
concrete table declaration, producing `BoundTable[T]`, or a group, producing
`BoundGroup[TableGroup]`. A group binding applies one `DataSourceConfig` to its
descendant tables, including location, format, partition layout, credential
reference, version, and provenance. Compilation expands `BoundGroup` into the
same canonical `BoundTable` definitions produced by direct table bindings.
Secrets are always referenced indirectly through runtime configuration or
environment-backed credentials.

Typed table shapes, optional template metadata, and generated concrete table
classes are authored manually in the MVP. Their field paths receive IDE
completion and static validation of field existence, expression input/output
types, node and edge property compatibility, and identifier and endpoint types.
A `DynamicTable` is the explicit alternative for ad hoc or evolving inputs:
`bound.field("studyId")` returns a
`DynamicField[Unknown]`, while an asserted type such as
`bound.field("score", as_type=float)` returns `DynamicField[float]`. `Unknown`
cannot silently satisfy an incompatible graph-property mapping; it is checked
during inspection or build.

Typed and dynamic declarations compile to the same table and field-reference
IR. Generating typed table declarations from external metadata is future work.

### Projections and value expressions

A projection is a logical data product whose output fields are inferred from
typed expressions. It may combine values from several bound tables. Authors
express the desired values and their cardinality, not joins, aliases, or a
physical query plan; the system resolves the required relational work.

`provide` is the portable, discoverable expression namespace:

- `provide.value` creates or transforms one value, including literals,
  concatenation, coalescing, casts, generated UUIDs, and conditional values;
- `provide.collection` explicitly expands or collects collection-valued fields;
- `provide.lookup.one` enriches a value with one matching record from another
  declared input.

Collection traversal never silently selects an item or duplicates rows.
`provide.collection.expand(...)` creates one output-row context per item;
multiple expansions require an explicit correlation or cartesian-product
policy. `provide.lookup.one(...)` requires a compatible key that identifies at
most one record; duplicates are diagnostics and `on_missing` declares absence
handling. The expression IR records field traversal, cardinality, lookup
semantics, and explicit ambiguity-resolution policies without exposing a query
language.

### Graph binding declaration

A graph binding is an immutable assignment from a projected table to one node
or edge type. It declares identifiers, endpoints, properties, mapping policies,
and provenance. A binding may instantiate a specification contract by assigning
an `Expression[T]` or literal `T` directly to a `SpecInput[T]` member. Bindings
use the same typed field paths, dynamic fields, and `provide.*` expressions as
projections:

```python
node_binding(
    target=Target,
    from_=AssociationRows,
    identifier=AssociationRows.target_id,
    properties={Target.symbol: AssociationRows.target_symbol},
)
```

The portable expression subset must compile deterministically to DuckDB SQL.
Python user-defined transformations are a later extension and are explicitly
outside the portable MVP subset.

## 6. Future design: model synchronization and code generation

Code generation is not part of the MVP. The model and IR boundaries should,
however, be designed so that it can be added later without changing their
meaning or public contracts.

Topology, table shapes and declarations, groups, and bindings share versioned
IR schemas.
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

## 7. Layer 3: compilation and build execution

Compilation is the boundary between authoring and execution. The `compile`
layer consumes validated topology, data, binding, and target declarations and
produces one immutable, target-specific `CompiledBuildDefinition`. It validates
topology-to-binding coverage and type compatibility; resolves expression,
cardinality, and lookup semantics; detects target capabilities; and records the
supported target annotations and actions. It retains physical locations and
credential references, but never credential values.

The `build` layer consumes only `CompiledBuildDefinition` plus `BuildRuntime`.
`BuildRuntime` supplies resolved credentials and operational settings such as
temporary storage, resource limits, logging, and optional approved environment
overrides. Build code does not import or interpret authoring declarations such
as `Node`, `Field`, `NodeBinding`, or `provide` expressions.

### Pipeline

1. Compile topology, data contracts, bound inputs, graph bindings, and a target
   declaration into `CompiledBuildDefinition`.
2. Validate target capabilities and produce clear diagnostics according to the
   configured annotation strictness policy.
3. Resolve runtime credentials and execution settings.
4. Lower compiled plans to DuckDB SQL and execute them with projection and
   filter pushdown.
5. Stream normalized node and edge records to the compiled target writer.
6. Apply compiled target actions such as indexes and constraints.
7. Emit a build report containing counts, diagnostics, provenance, and plan
   fingerprints.

### Target interface

Targets consume a stable graph record protocol and declare their capabilities.
A target declaration, including its serialisable configuration and credential
references, is compiled into `CompiledBuildDefinition`; secret values are
provided only through `BuildRuntime`. The initial MVP target should be a
file-based interchange output. Neo4j is the first database target and
demonstrates target annotations.

DuckDB owns relational work including scans, joins, filters, unnests,
aggregations, casts, and deterministic expression evaluation. The execution
layer should expose generated SQL and query plans for inspection.

## 8. Proposed monorepo layout

```text
kg_build_system/
  topology/          # graph types, annotations, topology IR and validation
  data/              # table shapes/declarations, groups, fields, bindings, projections and expressions
  binding/           # graph bindings and topology-to-data type rules
  compile/           # compilation, validation and CompiledBuildDefinition
  build/             # physical readers, DuckDB execution, targets and reports
demo/
  topology/          # demonstration graph declarations
  data/              # table contracts, bound inputs, projections and fixtures
  bindings/          # node and edge graph bindings
  build.py           # complete end-to-end graph build declaration
tests/
  topology/          # topology declarations and IR
  data/              # contracts, dynamic fields and projections
  binding/           # graph bindings and type validation
  build/             # SQL lowering, execution and targets
```

Packages may begin as modules in one distribution if that reduces MVP overhead;
the boundaries above are architectural contracts, not a requirement for early
independent publishing. The MVP interface is a Python API. Data-access
implementations and build-target integrations belong to `build`; neither
requires a separate top-level package.

The dependency direction is `compile` → (`topology`, `data`, `binding`) and
`build` → `compile.model`. Topology and data declarations are independent;
graph bindings are the first layer that references both. Build execution depends
only on the compiled-definition protocol and never on authoring declarations.

## 9. MVP scope

The MVP proves one end-to-end workflow with:

- a shared `Specification` abstraction for reusable class-based structural
  contracts, with each declaration layer owning its field specifiers and static
  authoring convention;
- class-based Python authoring for topology, with JSON export from the compiled
  topology IR;
- manually authored table shapes, optional named/described templates, final
  generated `TableDeclaration` classes, table groups, structs, explicitly named
  typed fields, and direct/group physical bindings for Parquet and CSV;
- dynamic tables and asserted dynamic fields, with `Unknown` guarded at build
  and inspection time;
- projections over one or more bound tables, including nested field paths,
  `provide.value` expressions, `provide.collection.expand(...)`, and singular
  `provide.lookup.one(...)` enrichment;
- immutable node and edge bindings that map projected values to typed topology
  references;
- target-specific compilation to `CompiledBuildDefinition`, then DuckDB SQL
  lowering and execution from that definition plus `BuildRuntime`;
- file output and a minimal Neo4j target;
- model validation, SQL inspection, and reproducible build reports;
- a self-contained, importable demonstration project that defines, binds, and produces a
  small graph demonstrating ontology and target annotations.

## 10. Deferred concerns

- distributed execution and scheduling;
- incremental and change-data-capture builds;
- arbitrary Python transformations inside SQL plans;
- a graphical model editor;
- automatic migration of deployed target schemas;
- optimization across independently authored bindings;
- support for every graph database or remote source;
- model synchronization, table-schema generation, and Python/YAML round trips.

## 11. Success criteria

The PoC succeeds when the demonstration graph, logical data contracts, bound
inputs, projections, and graph bindings validate; invalid typed or asserted
dynamic field references are caught before execution; expressions compile to
inspectable DuckDB SQL; and the demonstration pipeline produces equivalent file
and Neo4j graph outputs with the declared annotations applied where supported.
