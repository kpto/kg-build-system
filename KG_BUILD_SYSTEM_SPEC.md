# Knowledge Graph Build System — Unified Specification

## 1. Purpose and status

This is the canonical specification for the Knowledge Graph Build System. It
centralises the model, public declaration patterns, compilation architecture,
and authoring practices.

The system builds knowledge graphs from declared logical data contracts. It
separates graph meaning from physical input sources and from concrete build
execution. Python is the MVP authoring surface and DuckDB is the initial
relational engine.

The architecture below is intentionally larger than the first deliverable.
Features are classified as foundation, MVP extension, or future work so that
the system's direction does not become a commitment to build everything first.

## 2. Core model

```text
topology ──────── graph types, properties, constraints, annotations
data contracts ── logical tables, fields, structs, projections
bindings ──────── values mapped into graph components
sources ───────── physical locations and credential references
build ─────────── compiled target-specific execution
```

```text
topology declarations ─┐
data declarations ─────┼─> create_blueprint ─> BuildBlueprint ─┐
graph bindings ────────┘                                        ├─> compile_blueprint ─> BuildContract ─> build
default sources, target, compilation settings ──────────────────┘
```

Topology, data contracts, and bindings are reusable declarations. Sources,
targets, and build configuration are concrete composition choices.

### Principles

- Separate meaning, acquisition, and execution.
- Use typed declarations by default; dynamic fields are explicit and never
  silently become `Any`.
- Declare values, cardinality, and lookups—not joins or query plans.
- Compile every authoring surface to canonical, immutable IRs.
- Express target features as namespaced annotations.
- Store credential references in definitions and resolved credentials only in
  runtime configuration.

## 3. Foundation: specifications and declarations

The authoring surface has no shared `Specification` or `Declaration` base.
It separates source-field references, portable computations, and graph-slot
bindings so that static typing reflects their distinct roles:

```python
class FieldPath[T]:
    """A typed logical reference produced by table or struct navigation."""


class Field[T]:
    @overload
    def __get__(self, instance: None, owner: type | None = None) -> FieldPath[T]: ...
    @overload
    def __get__(self, instance: object, owner: type | None = None) -> Self: ...


class PropertySlot[T]:
    """A graph-component constructor slot."""


class ExpressionBinding[T](PropertySlot[T]):
    expression: Expression[T]


class Expression[T]:
    """A portable value computation."""
```

`FieldPath[T]` never inherits from, or is cast into, `Expression[T]` or
`PropertySlot[T]`. `bind(...)` is the explicit graph-slot boundary:

```python
def bind[T](value: T | FieldPath[T] | Expression[T]) -> ExpressionBinding[T]: ...
```

The graph layer owns the only constructor transform. It is keyword-only and
accepts `ExpressionBinding[T]` values through the `PropertySlot[T]` subtype:

```python
@dataclass_transform(field_specifiers=(property,), kw_only_default=True)
class GraphComponent(ABC):
    pass
```

Tables, structs, and projections are ordinary decorated Python classes. Their
members are explicitly annotated `Field[T]` or `ProjectedField[T]`; no shared
contract base class is required.

Framework metadata is `ClassVar` or unannotated, so it is not an author-facing
constructor parameter.

## 4. Topology

Topology declares graph meaning independently of source data. Nodes and edges
are first-class `GraphComponent` contracts. Edges declare source, target,
properties, direction, cardinality where known, and annotations.

```python
@node(description="A biological target.")
class Target(GraphComponent):
    symbol: PropertySlot[str] = property(name="symbol", nullable=False)
    name: PropertySlot[str | None] = property(name="name")


@node(description="A disease or phenotype.")
class Disease(GraphComponent):
    name: PropertySlot[str] = property(name="name", nullable=False)
    description: PropertySlot[str | None] = property(name="description")


@edge(source=Target, target=Disease, description="Evidence-backed association.")
class AssociatedWith(GraphComponent):
    score: PropertySlot[float] = property(name="score", nullable=False)
```

Annotations express semantics or target hints: ontology terms, indexes,
constraints, naming overrides, and similar metadata. They use namespaced keys
such as `ontology.term` and `neo4j.index`. The core preserves unknown
annotations; targets interpret only what they support.

Components can be templates: subclasses inherit properties, descriptions, and
annotations and may add or override properties. Source files may be node-first
for discoverability while compiled topology uses graph-level registries.

```text
topology/
  nodes/target/
    target.py
    edges/associated_with_disease.py
```

## 5. Logical data contracts

The source-independent data hierarchy is:

```text
Table → Field → DataType
```

`Field` may be scalar, optional, nested, or collection-valued. A `Struct` is a
reusable nested record shape; it cannot be bound independently. A
Every table or struct is an ordinary decorated class. Every field has an
explicit external name; the Python attribute remains a typed authoring handle.

```python
@struct
class TargetDetails:
    id: Field[str] = field(name="id")
    symbol: Field[str] = field(name="symbol")


@table_template(name="pharmacogenomics_annotation_shape")
class PharmacogenomicsAnnotation:
    target: Field[TargetDetails] = field(name="target")
    disease_ids: Field[list[str]] = field(name="diseaseIds")
    study_id: Field[str] = field(name="studyId")
    score: Field[float] = field(name="score")


@table(name="pharmacogenomics_annotation")
class OpenTargetsPharmacogenomicsAnnotation(PharmacogenomicsAnnotation):
    pass
```

`@table_template` preserves a reusable Python class and adds stable metadata.
`@table` creates a distinct final table class. Only final
concrete tables may be grouped, used in projections, or source-bound. This
prevents binding a reusable shape or inheriting a concrete table accidentally.

Nested navigation creates typed field paths:

```python
OpenTargetsPharmacogenomicsAnnotation.target.symbol  # FieldPath[str]
OpenTargetsPharmacogenomicsAnnotation.disease_ids    # FieldPath[list[str]]
```

Types distinguish nullable fields, nullable collections, and nullable items:

```python
Field[str | None]
Field[list[str]]
Field[list[str] | None]
Field[list[str | None]]
```

Navigating a collection preserves its cardinality: it cannot select an item or
duplicate a row implicitly.

Nested navigation may continue through a collection. The resulting field path
retains every collection segment rather than requiring an author to introduce
a temporary item variable. `expand` requests row-context expansion for that
path; compilation derives and shares the required parent-first unnests:

```python
Association.evidence.element.disease_id  # collection-valued FieldPath[str]
Association.evidence.element.labels      # collection-valued FieldPath[list[str]]
```

## 6. Table groups and physical sources

`TableGroup` provides named nested groups of concrete tables. Group and table
names form a catalog path, while Python attributes remain typed handles.

```python
@table_group(name="output")
class OpenTargetsOutput:
    pharmacogenomics_annotation = include(OpenTargetsPharmacogenomicsAnnotation)
```

`bind_source` attaches a table or group to physical configuration: location,
format, partition layout, credential reference, version, and provenance. Group
bindings expand to canonical `BoundTable` definitions.

```python
open_targets_release = bind_source(
    target=OpenTargetsOutput,
    config=DataSourceConfig(
        location="s3://example/open-targets/2025-01",
        format=InputFormat.PARQUET,
        layout=PartitionedParquetLayout(files="{group_path}/{table_name}/**/*.parquet"),
        credentials=environment_credential("PHARMACOGENOMICS_S3"),
        version="2025-01",
    ),
)
```

Many sources may be capable of binding a logical table, but a concrete build
must resolve each required table to exactly one bound table or issue an
ambiguity diagnostic. Source selection belongs to build composition, never to
projection semantics.

Dynamic tables are optional. An unasserted dynamic field is `Unknown`, not
`Any`, and cannot silently satisfy an incompatible graph property mapping:

```python
annotations = bind_source(target=DynamicTable(), config=csv_config)
study_id = annotations.field("study_id")                 # DynamicField[Unknown]
score = annotations.field("score", as_type=float)        # DynamicField[float]
```

Typed and dynamic declarations compile to the same table and field-reference
IR.

## 7. Projections and value expressions

A projection is a logical data product. Its fields are inferred from
`projected_field(...)`, distinct from contract `field(...)`. It references
final concrete tables and derives its logical input requirements from its
expressions; it has no separate `inputs` argument.

```python
@projection
class AssociationTable:
    target_id = projected_field(OpenTargetsPharmacogenomicsAnnotation.target.id)
    target_symbol = projected_field(OpenTargetsPharmacogenomicsAnnotation.target.symbol)
    disease_id = projected_field(
        collection.expand(OpenTargetsPharmacogenomicsAnnotation.disease_ids)
    )
    study_id = projected_field(OpenTargetsPharmacogenomicsAnnotation.study_id)
```

Portable expression namespaces are direct authoring APIs:

```python
value.literal(AssociationTable.target_symbol)            # Expression[str]
value.literal("unknown")                                 # Expression[str]
value.concat("annotation::", AssociationTable.study_id)
value.coalesce(AssociationTable.target_name, "unknown")
```

```text
ExpressionInput[T] = T | FieldPath[T] | DynamicField[T] | Expression[T]
```

`FieldPath[T]` and `Expression[T]` are deliberately different types.
Navigation of a table or struct member produces a `FieldPath[T]`, which is a
typed logical reference and does **not** inherit from `Expression[T]`. An
`Expression[T]` represents a portable value computation. A field path never
becomes an expression or graph-property slot through inheritance or casting.

The expression namespaces accept `ExpressionInput[T]` directly and normalize
their inputs internally. `bind(...)` is the separate graph-property-slot
boundary: it accepts an `ExpressionInput[T]` and returns an
`ExpressionBinding[T]`. Canonical bindings and compiled IR retain expressions,
never disguised field paths.

- `value` provides `literal`, `concat`, `coalesce`, `cast`, `present`,
  and `when`.
- `collection` resolves cardinality through `expand` and `collect`.
- `lookup.one` declares singular key-based enrichment.

`expand` makes one output-row context per item and repeats sibling scalar
values. Its null/empty policy must be explicit. Multiple expansions require a
declared `correlated` or `cartesian` policy. `collect` must require an explicit
grouping context rather than infer one. `lookup.one` requires a key that
identifies at most one record; duplicates are diagnostics and `on_missing`
declares absence semantics.

Authors reference nested fields directly; they do not manage intermediate
unnest items. For example, the compiler recognises the shared `evidence`
prefix and lowers the two requested expansions into a parent-first plan:

```python
@projection
class EvidenceTable:
    disease_id = projected_field(collection.expand(Association.evidence.element.disease_id))
    evidence_label = projected_field(collection.expand(Association.evidence.element.labels))
```

This expresses one expansion over `evidence` followed by one over each
evidence record's `labels`; the authoring declaration contains no temporary
row-context variable or target-specific unnest plan.

The expression IR records table roles, traversal, cardinality, lookup meaning,
and ambiguity resolution without exposing a SQL query plan.

## 8. Graph bindings and identity

A graph binding maps expressions to a declared node or edge. It neither
acquires data nor selects a target. Its logical inputs are derived from the
expressions it uses.

```python
target_from_pharmacogenomics = node_binding(
    target=Target,
    build_key=value.literal(AssociationTable.target_id),
    properties=Target(symbol=bind(AssociationTable.target_symbol)),
)

annotation_associated_with_disease = edge_binding(
    target=AssociatedWith,
    build_key=value.deterministic_uuid(AssociationTable.study_id),
    source_build_key=value.concat("annotation::", AssociationTable.study_id),
    target_build_key=value.literal(AssociationTable.disease_id),
    properties=AssociatedWith(score=bind(AssociationTable.score)),
)
```

`properties` instantiates the graph contract with `ExpressionBinding[T]`
values created by `bind(...)`; it is not a dictionary keyed by property
objects. Build keys are build-time identity handles, not topology identifiers
or persisted graph properties.

An executable build must declare or inherit policies for null keys, duplicate
keys, node property conflicts, edge deduplication, and generated identities.
Generated portable IDs must be deterministic from declared stable inputs and a
namespace. Random UUIDs are excluded from reproducible builds.

## 9. Compilation and execution

`create_blueprint` consumes a complete set of topology, data declarations,
projections, graph bindings, default source bindings, and post-processing
declarations. It produces an immutable `BuildBlueprint`, validates
compatibility, resolves expression/cardinality semantics, and records stable
debug symbols. Incomplete work remains Python source rather than becoming a
partially-specified document IR.

`compile_blueprint` combines a blueprint with a target and serialisable
compilation settings. It resolves permitted source, target, and lowering
overrides without mutating graph semantics and creates an immutable
target-specific `BuildContract`. The contract contains effective source
versions and credential references, DuckDB SQL, target-writing instructions,
debug-symbol references, and blueprint/execution-plan fingerprints. It never
contains resolved credentials.

A contract contains one ordered `BindingExecutionPlan` per graph binding,
followed by compiler-internal component relations that DuckDB uses to
normalise records and emit diagnostics. Each binding plan owns its complete
relational row context, so a projection expansion used by one binding cannot
change another binding's semantics.

`build` consumes only `BuildContract` and `BuildRuntime`.
`BuildRuntime` supplies resolved credentials plus operational settings such as
temporary storage, resource limits, and logging. The build layer does not
interpret authoring classes, graph bindings, or expression values. It executes
the contract's DuckDB normalisation and diagnostic relations, then streams
only final graph records to the target writer.

Execution:

1. Create the reusable build blueprint.
2. Compile and validate the concrete build contract.
3. Resolve runtime credentials and operational settings.
4. Lower each binding to a self-contained, inspectable DuckDB record plan.
5. Execute relational work with scan, filter, and projection pushdown.
6. Stream the resulting normalised node and edge records to a target writer.
7. Apply supported target actions and emit counts, diagnostics, provenance, and
   plan fingerprints.

DuckDB owns scans, joins, unnests, aggregations, casts, and deterministic
expression evaluation. Arbitrary Python transformations are outside the
portable MVP.

## 10. Targets, organisation, and practices

Targets consume a stable normalised graph-record protocol and declare their
capabilities. Unsupported annotations follow a declared strictness policy:
error, warning, or preserve-without-action. The initial target is a file
interchange writer; Neo4j is the first database target.

```text
kg_build_system/
  specification/     # shared foundations
  topology/          # graph declarations and codecs
  data/              # contracts, sources, projections
  binding/           # graph bindings and expression constructors
  compile/           # abstract and concrete definitions
  build/             # DuckDB execution and reports
  targets/file/      # interchange output
  targets/neo4j/     # Neo4j output
demo/                 # importable end-to-end example
tests/                # feature-oriented tests by layer
```

Dependencies flow `specification` → (`topology`, `data`) → `binding` →
`compile` → `build`; targets depend on compiled/build protocols, never the
reverse.

Authoring practices:

- Keep topology and graph bindings discoverable in a node-first layout.
- Use explicit external names for all contract fields.
- Use templates for reusable shape and final tables for inputs/bindings.
- Make collection, lookup, missing-value, and identity policy explicit.
- Keep physical sources and provenance in source bindings; keep secrets only in
  runtime configuration.
- Treat compiled definitions and generated SQL as inspectable development
  artifacts.

## 11. Delivery scope

### First vertical slice

- specification/declaration foundations and class-based topology;
- typed scalar/nested tables with one concrete CSV or Parquet source per table;
- simple projections, scalar expressions, and one explicit `expand`;
- deterministic node/edge identity with duplicate and conflict policy;
- both compiled definitions, inspectable DuckDB SQL, file output, and an
  importable demonstration.

### MVP extensions

- table templates/groups and group source bindings;
- `lookup.one` uniqueness diagnostics and `collect` with explicit grouping;
- dynamic fields guarded by `Unknown`;
- build reports, target capability checks, ontology annotations, and minimal
  Neo4j output.

### Future

- YAML/JSON import, code generation, and explicit synchronisation;
- schema generation from external metadata;
- distributed, scheduled, incremental, and CDC builds;
- arbitrary Python transformations, target migrations, additional databases,
  graphical editing, and cross-binding optimisation.

## 12. Success criteria

The first slice succeeds when a demo declares topology, typed input contracts,
a source, projection, and node/edge bindings; compiles them to inspectable SQL;
and writes a deterministic file graph with diagnostics and provenance.

The MVP succeeds when the same declared graph can be composed with valid
sources and file/Neo4j targets, producing equivalent normalised graph records
and applying supported annotations according to capability policy.
