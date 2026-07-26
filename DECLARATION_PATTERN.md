# Declarative topology, data, and bindings

This note describes the intended authoring model. Examples show the desired
public API, not necessarily functionality implemented today.

## 1. Specification contracts

`Specification` is the lowest-level class-based declaration concept. A class
that inherits it is a reusable declarative structural contract: it states the
shape and meaning of something without acquiring data or executing work. The
topology and data layers each provide their own concrete specification base
classes, and may reuse a contract by inheritance when re-specifying it.

The common layer is deliberately unaware of topology properties, table fields,
and other layer-specific descriptors:

```python
class Specification(ABC):
    """A reusable declarative structural contract."""


class Declaration[T](ABC):
    """A typed declaration for a member whose resolved type is T."""
```

`Declaration[T]` is the type used for declared members. Its type argument is
the member's resolved type. A topology `Property[T]`, table `Field[T]`, and
binding `Expression[T]` are concrete declarations. A declaration is not a
structural contract; it specifies one member of a contract.

`Specification` need not itself be a dataclass. Each layer owns its static
authoring convention and can use `dataclass_transform` to expose an
initializer that understands its registered field specifiers. Framework
metadata is `ClassVar` or unannotated, and therefore is not a constructor
parameter. Standard `dataclass_transform` does not filter members solely by a
`Declaration[...]` annotation; that convention is intentionally enforced loosely
by each layer.

## 2. Topology

Topology declarations describe graph meaning only. Nodes and edges are
first-class `Specification` contracts; an edge has a source, target,
properties, and annotations. The topology layer owns `property` as its field
specifier:

```python
@dataclass_transform(field_specifiers=(property,))
class GraphComponent(Specification):
    pass


@node(description="A biological target.")
class Target(GraphComponent):
    id: Declaration[str] = property(name="id")
    symbol: Declaration[str] = property(name="symbol", nullable=False)
    name: Declaration[str] = property(name="name")


@node(description="A disease or phenotype.")
class Disease(GraphComponent):
    id: Declaration[str] = property(name="id")


@edge(source=Target, target=Disease, description="Evidence-backed association.")
class AssociatedWith(GraphComponent):
    score: Declaration[float] = property(name="score", nullable=False)
```

Topology files may be organised by source node, while the compiled IR retains
one graph-level node registry and one graph-level edge registry.

```text
topology/
  nodes/
    target/
      target.py
      edges/
        associated_with_disease.py
```

## 3. Data layer

The data layer is source-independent. A table is a named, top-level collection
of records: it can be bound to a physical source, used as a projection input,
and compiled into a reusable contract. Its structural hierarchy is:

```text
Table → Field → DataType
```

`Field` is used rather than `Column` because a field may be scalar, optional,
nested, or collection-valued. `Struct` declares a reusable nested record
shape; it is not independently bound to a physical source. An ordinary Python
class inheriting the data layer's `TableContract` is a reusable table shape.
`TableContract` inherits `Specification` and registers `field` as its own
field specifier; the shared specification layer does not import or define it.
Its members are typed as `Declaration[T]`, and `field(...)` is the table-layer
declaration assigned in the class body. The `@table`
decorator consumes such a class and returns a final generated table class typed
as `type[TableDeclaration[T]]`: a distinct, named concrete table contract whose
schema is `T`.

```python
@dataclass_transform(field_specifiers=(field,))
class TableContract(Specification):
    pass
```

Every field declares its exact contract name explicitly. The Python attribute
is the typed authoring handle, so it may use Python naming conventions even
when the contract name does not.

```python
@struct
class TargetDetails(TableContract):
    id: Declaration[str] = field(name="id")
    symbol: Declaration[str] = field(name="symbol")
    name: Declaration[str | None] = field(name="name")


@struct
class Evidence(TableContract):
    study_id: Declaration[str] = field(name="studyId")
    score: Declaration[float] = field(name="score")

@table_template(
    name="pharmacogenomics_annotation_shape",
    description="A reusable pharmacogenomics annotation row shape.",
)
class PharmacogenomicsAnnotation(TableContract):
    target: Declaration[TargetDetails] = field(name="target")
    disease_ids: Declaration[list[str]] = field(name="diseaseIds")
    study_id: Declaration[str] = field(name="studyId")
    score: Declaration[float] = field(name="score")
    evidence: Declaration[list[Evidence]] = field(name="evidence")


@table(name="pharmacogenomics_annotation")
class OpenTargetsPharmacogenomicsAnnotation(PharmacogenomicsAnnotation):
    pass

@table_template(
    name="study_registry_shape",
    description="A reusable study-registry row shape.",
)
class StudyRegistry(TableContract):
    study_id: Declaration[str] = field(name="studyId")
    title: Declaration[str] = field(name="title")
    sponsor: Declaration[str | None] = field(name="sponsor")


@table(name="study_registry")
class OpenTargetsStudyRegistry(StudyRegistry):
    pass
```

`@table_template` attaches a template name and description but preserves the
class unchanged, so templates retain ordinary Python inheritance. Reusable
shape classes cannot be bound directly. Applying `@table` generates a final
table class that inherits its schema and is typed as
`type[TableDeclaration[OpenTargetsPharmacogenomicsAnnotation]]`. Its metadata
is available through `table_name()`, `schema_type()`, `template_name()`, and
`template_description()` class methods. Only generated table classes are
accepted by table groups and source bindings. This makes binding a reusable
shape, or inheriting a concrete table, a static type error rather than an
authoring convention.

`TableGroup` provides a named hierarchy of concrete table declarations and
nested groups.
The group and table names form a catalog path, while Python attributes expose
typed authoring handles:

```python
@table_group(name="output")
class OpenTargetsOutput:
    pharmacogenomics_annotation = include(OpenTargetsPharmacogenomicsAnnotation)
```

Physical location, format, credentials, version, provenance, and partition
layout belong to a configured source binding. `bind_source` accepts either a
single concrete table declaration or a group; group configuration is inherited
by all descendant tables. Many physical sources may bind the same concrete
table declaration or group contract.

```python
# A group binding discovers the partitioned Parquet datasets beneath the named
# `output` group and exposes its typed bound tables.
open_targets_release: Final[BoundGroup[OpenTargetsOutput]] = bind_source(
    target=OpenTargetsOutput,
    config=DataSourceConfig(
        location="s3://example/open-targets/2025-01",
        format=InputFormat.PARQUET,
        layout=PartitionedParquetLayout(files="{group_path}/{table_name}/**/*.parquet"),
        credentials=environment_credential("PHARMACOGENOMICS_S3"),
        version="2025-01",
    ),
)

# A standalone table can be bound directly.
study_registry_release = bind_source(
    target=OpenTargetsStudyRegistry,
    config=DataSourceConfig(
        location="s3://example/study-registry/2025-01.parquet",
        format=InputFormat.PARQUET,
    ),
)

pharmacogenomics_release = open_targets_release.pharmacogenomics_annotation
```

`BoundGroup` is an authoring convenience. Compilation expands it into the same
canonical `BoundTable` definitions produced by direct table bindings. A
projection may therefore combine values from independently declared table
contracts regardless of whether they originated in a direct or group binding.

### Nested fields and collections

Nested access produces a typed `FieldPath`:

```python
PharmacogenomicsAnnotation.target.symbol  # FieldPath[str]
PharmacogenomicsAnnotation.disease_ids    # FieldPath[list[str]]
PharmacogenomicsAnnotation.evidence.score # FieldPath[list[float]]
```

The type of a field expresses both its value shape and any nullability:

```python
Field[str | None]         # field itself may be absent
Field[list[str]]          # collection of non-null strings
Field[list[str] | None]   # collection itself may be absent
Field[list[str | None]]   # collection items may be absent
```

Traversing a collection preserves collection cardinality. It never silently
selects one item or duplicates a row; authors resolve cardinality explicitly
with portable value expressions such as `provide.collection.expand(...)` or
`provide.collection.collect(...)`.

### Dynamic tables and fields

Typed table declarations are the path demonstrated by the MVP. Dynamic mode is
an optional feature for ad hoc or evolving sources; it uses the same binding
pattern, but supplies a `DynamicTable` and resolves only the fields needed by
the build.

```python
annotations = bind_source(
    target=DynamicTable(),
    config=DataSourceConfig(
        location="s3://example/pharmacogenomics.csv",
        format=InputFormat.CSV,
    ),
)

study_id = annotations.field("study_id")                  # DynamicField[Unknown]
score = annotations.field("score", as_type=float)         # DynamicField[float]
```

An unasserted dynamic field has type `Unknown`, not `Any`, so it cannot
silently satisfy an incompatible graph-property mapping. The compiler validates
its physical path and any asserted type during inspection or build. Typed and
dynamic tables compile to the same internal table and field-reference IR.

A projected table is a logical data product. Its output fields are inferred
from the typed values assigned through the projection layer's
`projected_field(...)` declaration helper. This is deliberately distinct from
the data-layer `field(...)` helper used to declare fields on table contracts.
Projections reference only final concrete table declarations, never reusable
templates or structs. The compiler derives their logical table requirements
from those references, so the projection decorator has no separate `inputs`
argument. The requirements can then be resolved to physical source bindings.
Projections can still be reused with different source configurations.

```python
@projection
class AssociationTable:
    target_id = projected_field(OpenTargetsPharmacogenomicsAnnotation.target.id)
    target_symbol = projected_field(OpenTargetsPharmacogenomicsAnnotation.target.symbol)
    target_name = projected_field(OpenTargetsPharmacogenomicsAnnotation.target.name)
    disease_id = projected_field(
        provide.collection.expand(OpenTargetsPharmacogenomicsAnnotation.disease_ids)
    )
    study_id = projected_field(OpenTargetsPharmacogenomicsAnnotation.study_id)
    score = projected_field(OpenTargetsPharmacogenomicsAnnotation.score)
    study_title = projected_field(
        provide.lookup.one(
            OpenTargetsPharmacogenomicsAnnotation.study_id,
            in_=OpenTargetsStudyRegistry,
            key=OpenTargetsStudyRegistry.study_id,
            on_missing="null",
        ).title,
    )
```

For example, `AssociationTable.score` is inferred as `Field[float]` and is a
typed, referenceable field. Use named projected tables when they are reused,
documented, tested, or materialised independently; a one-use local relation
expression is also valid.

## 4. Bindings and provided values

`provide` is the discoverable namespace for transforming values and producing
generated values. It has three subnamespaces: `value` for scalar expressions,
`collection` for collection operations, and `lookup` for keyed record
enrichment. Each operation creates a typed, immutable value declaration. IDE
completion on `provide.` exposes these three categories.

`provide` is also callable. Calling `provide(value)` normalises a compatible
literal, typed field path, or dynamic field into an `Expression[T]`; supplying
an `Expression[T]` returns that expression unchanged. This gives bindings one
explicit, concise way to supply a simple expression without making literals or
table fields direct binding-member assignments.

```python
provide(AssociationTable.target_symbol)                 # Expression[str]
provide("unknown")                                      # Expression[str]
provide.value.literal("pharmacogenomics_annotation::")
provide.value.concat("annotation::", AssociationTable.study_id)
provide.value.coalesce(AssociationTable.target_name, "unknown")
provide.value.uuid()
```

Typed field paths and dynamic fields are valid `ProvideInput`s. They are
accepted directly in projections and as operands to `provide.*` calls; graph
bindings receive the resulting `Expression[T]`:

```python
target_id = projected_field(OpenTargetsPharmacogenomicsAnnotation.target.id)
source_build_key = provide.value.concat("annotation::", AssociationTable.study_id)
target_build_key = provide(AssociationTable.disease_id)
```

```text
ProvideInput[T] = FieldPath[T] | DynamicField[T] | Expression[T] | compatible literal T
```

Typed field paths and dynamic fields are operands for `provide.*` calls, not
direct binding-member assignments. When a specification contract is
instantiated as binding `properties`, its `Declaration[T]` members accept only
an `Expression[T]` created through `provide`. The original topology or table
field specifiers remain class-body declarations; the binding layer interprets
the supplied expressions against that structural contract.

### Intention-oriented expressions, navigation, and cardinality

The value-expression system is shared by projections and graph bindings. A
projection uses expressions to define a logical data product; a graph binding
uses the same expressions to provide build keys, properties, and other mapping
values. In both contexts, an expression states what a value
means, not a physical query plan.

A projection's referenced final table declarations determine the logical tables
from which its expressions may draw values, making their declared references
available for typed navigation. A graph binding consumes the resulting
projected values. Physical source bindings are supplied only when the reusable
graph definition is composed into a build. The author does not
select joins, aliases, or any other execution mechanism; the compiler resolves
the physical relational operations needed to obtain a declared value.

`provide.lookup.one(...)` obtains a singular related record from another
declared input using a compatible key. It expresses an enrichment relationship,
not an execution plan. The target key must identify at most one record;
duplicate matches are diagnostics. `on_missing` declares the intended absence
policy, so the `AssociationTable.study_title` example above is inferred as
`Field[str | None]`.

A reference has declared cardinality. Navigating a singular reference produces
a singular value (which may be absent when the reference is optional).
Navigating a collection does not silently choose one value or duplicate a row:
the author must resolve its cardinality deliberately.

```python
# One projected output row for every disease ID on an annotation.
disease_id = projected_field(
    provide.collection.expand(OpenTargetsPharmacogenomicsAnnotation.disease_ids)
)

# A graph binding may use the same expression language for a generated build key.
build_key = provide.value.concat("annotation::", AssociationTable.study_id)

# One collection-valued output for values gathered from several input rows.
study_ids = projected_field(
    provide.collection.collect(OpenTargetsPharmacogenomicsAnnotation.study_id)
)
```

`provide.collection.expand(...)` repeats the sibling scalar values for each
collection item. When an expression contains more than one expansion, the author must
declare whether items are correlated or form a cartesian product. Likewise, if
more than one declared reference path could supply a value, the author must
select the intended path explicitly; the compiler never guesses.

The compiled expression IR records table roles, reference traversal,
cardinality, and any explicit ambiguity-resolution policy. It remains
independent of the compute engine; lowering it to DuckDB or another execution
backend is an implementation concern.

The portable vocabulary includes:

- typed field paths, dynamic fields, and declared reference navigation;
- `provide.collection.expand(...)` and `provide.collection.collect(...)` for
  cardinality;
- `provide.lookup.one(...)` for singular, key-based record enrichment;
- `provide.value.concat(...)`, `provide.value.coalesce(...)`,
  `provide.value.cast(...)`, and `provide.value.literal(...)` for scalar values;
- `provide.value.present(...)`, `provide.value.when(...)`, and explicit ambiguity
  resolution where needed.

These expressions are intention-oriented and portable. They state which values
are required and how their cardinality is handled; they do not expose a query
language or execution plan.

A graph binding is an immutable assignment from the logical tables referenced
by its expressions to one graph component. It describes graph mapping, not
acquisition, provenance, target configuration, or a physical query plan. The
compiler derives its logical input requirements from those expressions, so
bindings do not declare a separate `from_` argument.

Binding declarations mirror the node-first topology layout, so graph
components and their data mappings are easy to find together:

```text
bindings/
  nodes/
    target/
      target.py
      edges/
        associated_with_disease.py
```

```python
target_from_pharmacogenomics: Final[NodeBinding[Target]] = node_binding(
    target=Target,
    build_key=provide(AssociationTable.target_id),
    properties=Target(
        symbol=provide(AssociationTable.target_symbol),
        name=provide(AssociationTable.target_name),
    ),
)


annotation_associated_with_disease: Final[EdgeBinding[AssociatedWith]] = edge_binding(
    target=AssociatedWith,
    build_key=provide.value.uuid(),
    source_build_key=provide.value.concat("pharmacogenomics_annotation::", AssociationTable.study_id),
    target_build_key=provide(AssociationTable.disease_id),
    properties=AssociatedWith(
        score=provide(AssociationTable.score),
    ),
)
```

Topology supplies edge type, endpoint types, property types, and annotations.
Bindings supply source values, build keys, and mapping policies. Build keys are
not topology identifiers or persisted graph properties: a target may use them
to discover or connect records during a build and then discard them.
The `properties` argument instantiates the target graph-component contract with
expressions created through `provide` for its declared properties; it does not
use a dictionary keyed by `Property` objects. Binding modules mirror the topology
layout: node bindings live with their node, and edge bindings live beneath their
source node's `edges/` directory.

## 5. Compiled definitions and build execution

The intended connection between layers is:

```text
topology declarations ─┐
                       ├─→ compile_graph ─→ CompiledGraphDefinition ─┐
data declarations ─────┘                                               ├─→ compile_build ─→ CompiledBuildDefinition ─→ build
graph bindings ─────────┘                                               │
source bindings, target, and build configuration ───────────────────────┘
```

Topology and data declarations are independent. Graph bindings are the first
layer that references both, but remain abstract: they neither acquire data nor
declare provenance. `compile_graph` validates those declarations and produces
an immutable `CompiledGraphDefinition` containing the graph mapping and its
logical table requirements. It can be reused with different physical sources,
targets, and build configurations.

A source binding is the separate concrete binding between a logical table
contract and physical data. `compile_build` composes a `CompiledGraphDefinition`
with source bindings, a target declaration, and serialisable build configuration
into an immutable, target-specific `CompiledBuildDefinition`. It records source
provenance, physical locations, and credential references, but never credential
values. This is the reproducible artifact accepted by the build system.

`build` consumes only `CompiledBuildDefinition` plus `BuildRuntime`. The latter
supplies resolved credentials and operational settings such as logging,
temporary storage, and resource limits; it never changes graph meaning or
contains declarations. This boundary lets execution lower the compiled plan to
DuckDB and invoke target writers without importing authoring classes or
interpreting `provide` expressions. Derived navigation and coverage/provenance
diagnostics are future inspection features, not artifacts that authors
maintain.

For the MVP, package organisation follows the same layer boundaries:

```text
kg_build_system/
  specification/     # shared Specification, Declaration, and Expression foundations
  topology/          # topology authoring, definitions, codecs, and local logic
  data/              # data authoring, definitions, codecs, and local logic
  binding/           # bindings, provide expressions, codecs, and local logic
  compile/           # CompiledGraphDefinition and CompiledBuildDefinition composition
  build/             # generic execution, DuckDB, sources, and reports
  targets/
    file/            # file-target annotations, lowering, and writer
    neo4j/           # Neo4j annotations, lowering, and writer
```

Each declaration layer is an independent system. It owns its authoring API,
small immutable definitions, serialization, and logic required directly by its
features; no horizontal model, validation, or serialization package is needed
for the MVP. `compile` is the first deliberately cross-layer system, while each
target package owns its target-specific annotations and implementation. The MVP
prioritises feature delivery over comprehensive correctness infrastructure.
