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
class ValueRef[T]:
    """A typed value reference with no table or field metadata."""


class TablePathValueRefMetadata:
    """Table, path, traversal, and declaration metadata."""


class TablePathValueRef[T](ValueRef[T]):
    _metadata: TablePathValueRefMetadata


class Field[T](TablePathValueRef[T]):
    """A scalar (or scalar-list) table field."""


class StructField[T: Struct](TablePathValueRef[T]):
    """A structured value, navigated through ``member`` or ``m``."""


class CollectionField[T](TablePathValueRef[list[T]]):
    """A collection of structs, navigated through ``element`` or ``e``."""


class PropertySlot[T]:
    """A graph-component constructor slot."""


class ExpressionBinding[T](PropertySlot[T]):
    expression: Expression[T]


class Expression[T]:
    """A portable value computation."""
```

`ValueRef[T]` never inherits from, or is cast into, `Expression[T]` or
`PropertySlot[T]`. `bind(...)` is the explicit graph-slot boundary:

```python
def bind[T](value: T | ValueRef[T] | Expression[T]) -> ExpressionBinding[T]: ...
```

The graph layer owns the only constructor transform. It is keyword-only and
accepts `ExpressionBinding[T]` values through the `PropertySlot[T]` subtype:

```python
@dataclass_transform(field_specifiers=(property,), kw_only_default=True)
class GraphComponent(ABC):
    pass
```

Final declarations are layer base classes: `Node`, `Edge[S, T]`, `Table`,
`Struct`, `Projection`, and `TableGroup`. Table and struct members are
explicitly annotated `Field[T]`, `StructField[T]`, or `CollectionField[T]`;
graph members use `PropertySlot[T]`, and projections use `ProjectedField[T]`.
Reusable
shapes may remain ordinary Python mixins; `TableTemplate` and
`GraphComponent` are optional bases when a reusable shape needs framework
metadata such as annotations.

Framework metadata is `ClassVar` or unannotated, so it is not an author-facing
constructor parameter.

Property nullability is expressed only by its type: `PropertySlot[str]` is
required and `PropertySlot[str | None]` is nullable. The `property()` factory
has no `nullable` argument.

### Declaration names, options, and annotations

Every declaration has a stable logical name. An explicit `name=` wins;
otherwise the system derives a snake-case name from the declaring Python class
or member. Fields, properties, and projected fields infer their names from
their Python attribute, so `targetID` becomes `target_id`.

Class declarations remove one terminal suffix that identifies their own layer
before snake-casing. The supported suffixes are `Node`, `Edge`, `Table`,
`TableTemplate` (or `Template`), `Struct`, `TableGroup`, `Projection`, and
`ComponentTemplate` (or `Template`). For example, `TargetNode` becomes
`target`, `AssociatedWithEdge` becomes `associated_with`, and
`EvidenceRelease2025_06TableGroup` becomes `evidence_release_2025_06`.
Only a matching terminal suffix for the declaration's own layer is removed;
a table named `TargetNode` therefore remains `target_node`. A suffix-only
class name such as `Node` is invalid unless an explicit name is provided.

Each final declaration may provide a class-level `options` value. It is
framework metadata, never a field, property, projected field, or constructor
argument. Descriptions default to the class docstring; an explicit
`options.description` overrides that default.

```python
class TargetNode(Node):
    """A biological target."""

    options = NodeOptions()
    symbol: PropertySlot[str] = property()

class AssociationEdge(Edge[TargetNode, DiseaseNode]):
    score: PropertySlot[float] = property()
```

`Edge[S, T]` declares its endpoints through type arguments. A trailing
underscore escapes the reserved `options` class attribute: `options_` becomes
the external member name `options`; only one terminal underscore is removed.

Annotations are portable, serialisable semantic metadata. Every annotation is
a dataclass subclass of `Annotation` with a stable `namespace` and
`annotation_id`; its dataclass fields are the arguments:

```python
@dataclass(frozen=True)
class Index(Annotation):
    namespace = "index"
    annotation_id = "index"
    unique: bool = False

class TargetNode(Node):
    options = NodeOptions(annotations=[Index(unique=True)])
```

Options use `annotations`, not an unstructured metadata map. Annotations are
additive through reusable shapes and final declarations. They are supported on
components, properties, tables/templates/structs/fields, projections/projected
fields, table groups, bindings, and source bindings. Compiled IR serialises an
annotation as `namespace`, `annotation_id`, and JSON arguments; it never
serialises an annotation Python class.

## 4. Topology

Topology declares graph meaning independently of source data. Nodes and edges
are first-class `GraphComponent` contracts. Edges declare source, target,
properties, direction, cardinality where known, and annotations.

```python
class TargetNode(Node):
    """A biological target."""
    symbol: PropertySlot[str] = property()
    name: PropertySlot[str | None] = property()
    description: PropertySlot[str | None] = property()


class DiseaseNode(Node):
    """A disease or phenotype."""
    name: PropertySlot[str] = property()
    description: PropertySlot[str | None] = property()


class AssociatedWithEdge(Edge[TargetNode, DiseaseNode]):
    """Evidence-backed association."""
    score: PropertySlot[float] = property()
```

Annotations express semantics or target hints: ontology terms, indexes,
constraints, naming overrides, and similar metadata. A namespace is not an
access-control boundary: every module compiler receives the complete compiled
annotation graph and may interpret any annotation it recognises. A
module-specific annotation conventionally uses the owning module's ID as its
namespace. The core preserves unknown annotations.

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

### Supported declaration value types

The framework owns a closed portable scalar vocabulary:

```python
type Scalar = str | int | float | bool
```

Collections are expressed directly as `list[T]`; physical source collections
are list-shaped.
`Field[T]` accepts only a `Scalar` or `Scalar | None`; collections use
`CollectionField[T]`. `StructField[S]` and `CollectionField[S]` admit nested
records, while `CollectionField[T]` also supports scalar items. Maps, tuples,
sets, nested collections, arbitrary Python classes, and `Any` are not
declaration types.

`PropertySlot[T]` and `bind(...)` accept only `Scalar` or `Scalar | None`:
graph properties cannot be collections or structs. Expression literals use
the same vocabulary. Runtime declaration validation enforces the contract for
dynamic Python authoring, while the generic declaration types make invalid
annotations visible to a static type checker at edit time.

`Field` represents scalar values. `StructField` represents one nested `Struct`;
`CollectionField` represents a scalar or `Struct` collection. A `Struct` is a reusable nested record shape; it stores
`TablePathValueRefMetadata` only while serving navigation and is never a
`ValueRef`, so it cannot be bound independently.
Every final table or struct derives from its layer base class. A field's external name
defaults to its snake-case Python attribute; authors provide `name=` only when
the physical or external spelling differs. The Python attribute remains a
typed authoring handle.

```python
class TargetDetailsStruct(Struct):
    id: Field[str] = field()
    symbol: Field[str] = field()
    description: Field[str | None] = field()


class PharmacogenomicsAnnotationTableTemplate(TableTemplate):
    options = TableTemplateOptions(description="Reusable pharmacogenomics input shape.")
    target: StructField[TargetDetailsStruct] = struct_field()
    disease_ids: CollectionField[str] = collection_field(name="diseaseIds")
    study_id: Field[str] = field(name="studyId")
    score: Field[float] = field()


class OpenTargetsPharmacogenomicsAnnotationTable(
    PharmacogenomicsAnnotationTableTemplate, Table,
):
    pass
```

`TableTemplate` is optional: ordinary mixins remain valid when they do not
need declaration options. `Table` creates a distinct final table class. Only final
concrete tables may be grouped, used in projections, or source-bound. This
prevents binding a reusable shape or inheriting a concrete table accidentally.

Table field descriptors are themselves `TablePathValueRef` values. Structured
navigation first yields a non-value `Struct` proxy, then a typed value
reference at a terminal field:

```python
OpenTargetsPharmacogenomicsAnnotationTable.target          # ValueRef[TargetDetailsStruct]
OpenTargetsPharmacogenomicsAnnotationTable.target.m         # TargetDetailsStruct, not a ValueRef
OpenTargetsPharmacogenomicsAnnotationTable.target.m.symbol  # ValueRef[str]
OpenTargetsPharmacogenomicsAnnotationTable.disease_ids    # ValueRef[list[str]]
```

Types distinguish nullable fields, nullable collections, and nullable items:

```python
Field[str | None]
CollectionField[str]
CollectionField[str | None]
```

Graph properties use the same type-driven convention. A nullable table field
may be bound directly to a `PropertySlot[T | None]`; a JSON `null` remains a
null graph-record value. It cannot be bound to a required `PropertySlot[T]`
without an explicit expression that establishes a non-null value.

Navigating a collection preserves its cardinality: it cannot select an item or
duplicate a row implicitly.

Collection navigation uses an explicit element proxy. The resulting field path
retains every collection segment rather than requiring an author to introduce
a temporary item variable. `expand` requests row-context expansion for that
path; compilation derives and shares the required parent-first unnests:

```python
class AssociationTable(Table):
    evidence: CollectionField[EvidenceStruct] = collection_field()


AssociationTable.evidence.e.disease_id  # collection-valued ValueRef[str]
AssociationTable.evidence.e.labels      # collection-valued ValueRef[list[str]]
```

## 6. Table groups and physical sources

`TableGroup` provides named nested groups of concrete tables. Group and table
names form a catalog path, while Python attributes remain typed handles.
Groups may include only final tables or other table groups. Empty groups,
cycles, duplicate final-table inclusion, and duplicate catalog paths are
rejected.

```python
class OpenTargetsOutputTableGroup(TableGroup):
    options = TableGroupOptions(
        members=(OpenTargetsPharmacogenomicsAnnotationTable,),
    )
```

`bind_source` attaches a final table or table group to physical configuration: location,
format, partition layout, credential reference, version, and provenance. Group
bindings expand to canonical `BoundTable` definitions.

```python
open_targets_release = bind_source(
    target=OpenTargetsOutputTableGroup,
    config=DataSourceConfig(
        location="s3://example/open-targets/2025-01",
        format=InputFormat.PARQUET,
        layout="{group_path}/{table_name}/**/*.parquet",
        credentials=environment_credential("PHARMACOGENOMICS_S3"),
        version="2025-01",
    ),
    options=SourceBindingOptions(annotations=[...]),
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
class AssociationProjection(Projection):
    target_id = projected_field(OpenTargetsPharmacogenomicsAnnotationTable.target.m.id)
    target_symbol = projected_field(OpenTargetsPharmacogenomicsAnnotationTable.target.m.symbol)
    disease_id = projected_field(
        collection.expand(OpenTargetsPharmacogenomicsAnnotationTable.disease_ids)
    )
    study_id = projected_field(OpenTargetsPharmacogenomicsAnnotationTable.study_id)
```

Portable expression namespaces are direct authoring APIs:

```python
value.literal(AssociationProjection.target_symbol)       # Expression[str]
value.literal("unknown")                                 # Expression[str]
value.concat("annotation::", AssociationProjection.study_id)
value.coalesce(AssociationProjection.target_name, "unknown")
```

```text
ExpressionInput[T] = T | ValueRef[T] | DynamicField[T] | Expression[T]
```

`ValueRef[T]` and `Expression[T]` are deliberately different types.
`TablePathValueRef[T]` is the table-owned implementation of `ValueRef[T]` and
keeps its table/path details inside `_metadata`; the expressions package knows
only the portable `ValueRef[T]` contract. `StructField.m` and
`CollectionField.e` return a `Struct` proxy, not a `ValueRef`, so an
intermediate struct cannot be supplied to an expression. A terminal member,
such as `StudyTable.details.m.description`, is a `ValueRef[str | None]`.
`Expression[T]` represents a portable value computation. A value reference
never becomes an expression or graph-property slot through inheritance or
casting.

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

Authors reference nested terminal fields without managing temporary unnest
items. For example, the compiler recognises the shared `evidence` prefix and
lowers the two requested expansions into a parent-first plan:

```python
class EvidenceProjection(Projection):
    disease_id = projected_field(collection.expand(Association.evidence.e.disease_id))
    evidence_label = projected_field(collection.expand(Association.evidence.e.labels))
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
    target=TargetNode,
    build_key=value.literal(AssociationProjection.target_id),
    properties=TargetNode(symbol=bind(AssociationProjection.target_symbol)),
    options=BindingOptions(annotations=[...]),
)

annotation_associated_with_disease = edge_binding(
    target=AssociatedWithEdge,
    build_key=value.deterministic_uuid(AssociationProjection.study_id),
    source_build_key=value.concat("annotation::", AssociationProjection.study_id),
    target_build_key=value.literal(AssociationProjection.disease_id),
    properties=AssociatedWithEdge(score=bind(AssociationProjection.score)),
)
```

`properties` instantiates the graph contract with `ExpressionBinding[T]`
values created by `bind(...)`; it is not a dictionary keyed by property
objects. Build keys are build-time identity handles, not topology identifiers
or persisted graph properties.

`BindingOptions` and `SourceBindingOptions` attach annotations to the concrete
mapping and acquisition choices respectively. They do not alter graph meaning
unless a compiler module recognises and lowers their annotations.

An executable build must declare or inherit policies for null keys, duplicate
keys, node property conflicts, edge deduplication, and generated identities.
Generated portable IDs must be deterministic from declared stable inputs and a
namespace. Random UUIDs are excluded from reproducible builds.

## 9. Compilation and execution

`create_blueprint` consumes a complete set of topology, data declarations,
projections, graph bindings, default source bindings, and post-processing
declarations. It produces an immutable `BuildBlueprint`, validates
compatibility and resolves expression/cardinality semantics. Incomplete work remains Python source rather than becoming a
partially-specified document IR.

It serialises every annotation into canonical immutable IR. The blueprint and
contract preserve annotations without interpretation; annotations contribute to
their fingerprints. During `compile_blueprint`, every module compiler receives
the complete annotated blueprint and may derive serialisable workflow-step
payloads from annotations in any namespace. Runtime receives only the frozen
resulting workflow and does not resolve annotation classes.

`compile_blueprint` combines a blueprint with optional source/target selections
and serialisable compilation settings. It resolves permitted source, target, and lowering
overrides without mutating graph semantics and creates an immutable
target-specific `BuildContract`. The contract contains effective source
versions and credential references, DuckDB SQL, target-writing instructions,
binding origins, and blueprint/execution-plan fingerprints. It never
contains resolved credentials.

A contract contains one dependency-aware execution plan. Its relational steps
produce binding, aggregation, and normalised component relations; validation
steps emit diagnostics; terminal target-write steps consume final graph
relations. Each binding step owns its complete relational row context, so a
projection expansion used by one binding cannot change another binding's
semantics.

`build` consumes only `BuildContract` and `BuildRuntime`.
`BuildRuntime` supplies resolved credentials plus operational settings such as
temporary storage, resource limits, and logging. The build layer does not
interpret authoring classes, graph bindings, or expression values. It executes
the contract's relational and diagnostic steps, then performs only its terminal
target-write steps.

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
  table/             # contracts, sources, projections
  binding/           # graph bindings and expression constructors
  compile/           # abstract and concrete definitions
  build/             # DuckDB execution and reports
  targets/file/      # interchange output
  targets/neo4j/     # Neo4j output
demo/                 # importable end-to-end example
tests/                # feature-oriented tests by layer
```

Dependencies flow `specification` → (`topology`, `table`) → `binding` →
`compile` → `build`; targets depend on compiled/build protocols, never the
reverse.

Authoring practices:

- Keep topology and graph bindings discoverable in a node-first layout.
- Let contract fields use inferred snake-case names; use explicit external
  names only where the source spelling differs.
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

### Implemented MVP extensions

- table templates, nested table groups, and group source bindings;
- universal serialisable annotations across declaration, binding, and source
  layers; module compilers can inspect and interpret preserved annotations.

### Remaining MVP extensions

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
The demo includes nullable target, disease, and study descriptions with both
populated and JSON-null fixture values, demonstrating type-driven nullability
through its compiled graph records.

The MVP succeeds when the same declared graph can be composed with valid
sources and file/Neo4j targets, producing equivalent normalised graph records
and applying supported annotations according to capability policy.
