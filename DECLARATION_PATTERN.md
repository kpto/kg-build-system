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


class Specifier[T](ABC):
    """A typed declarative way to specify a value of type T."""


type SpecInput[T] = Specifier[T] | T
```

`SpecInput[T]` is the type used for declared members. It permits either a
layer-specific `Specifier[T]`, such as a topology `PropertyRef[T]` or a binding
`Expression[T]`, or a literal `T`. `Specifier` is not a structural contract;
it is the typed object that may be assigned to one member of a contract.

`Specification` need not itself be a dataclass. Each layer owns its static
authoring convention and can use `dataclass_transform` to expose an
initializer that understands its registered field specifiers. Framework
metadata is `ClassVar` or unannotated, and therefore is not a constructor
parameter. Standard `dataclass_transform` does not filter members solely by a
`SpecInput[...]` annotation; that convention is intentionally enforced loosely
by each layer.

## 2. Topology

Topology declarations describe graph meaning only. Nodes and edges are
first-class `Specification` contracts; an edge has a source, target,
properties, and annotations. The topology layer owns `PropertyRef` and
`IdentifierRef` as its field specifiers:

```python
@dataclass_transform(field_specifiers=(PropertyRef, IdentifierRef))
class GraphComponent(Specification):
    pass


@node(description="A biological target.")
class Target(GraphComponent):
    id: SpecInput[str] = IdentifierRef[str]()
    symbol: SpecInput[str] = PropertyRef[str](nullable=False)
    name: SpecInput[str] = PropertyRef[str]()


@node(description="A disease or phenotype.")
class Disease(GraphComponent):
    id: SpecInput[str] = IdentifierRef[str]()


@edge(source=Target, target=Disease, description="Evidence-backed association.")
class AssociatedWith(GraphComponent):
    score: SpecInput[float] = PropertyRef[float](nullable=False)
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
Its members are typed as `SpecInput[T]`, and `field(...)` is the table-layer
`Specifier[T]` assigned in the class body. The `@table`
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
    id: SpecInput[str] = field(name="id")
    symbol: SpecInput[str] = field(name="symbol")
    name: SpecInput[str | None] = field(name="name")


@struct
class Evidence(TableContract):
    study_id: SpecInput[str] = field(name="studyId")
    score: SpecInput[float] = field(name="score")

@table_template(
    name="pharmacogenomics_annotation_shape",
    description="A reusable pharmacogenomics annotation row shape.",
)
class PharmacogenomicsAnnotation(TableContract):
    target: SpecInput[TargetDetails] = field(name="target")
    disease_ids: SpecInput[list[str]] = field(name="diseaseIds")
    study_id: SpecInput[str] = field(name="studyId")
    score: SpecInput[float] = field(name="score")
    evidence: SpecInput[list[Evidence]] = field(name="evidence")


@table(name="pharmacogenomics_annotation")
class OpenTargetsPharmacogenomicsAnnotation(PharmacogenomicsAnnotation):
    pass

@table_template(
    name="study_registry_shape",
    description="A reusable study-registry row shape.",
)
class StudyRegistry(TableContract):
    study_id: SpecInput[str] = field(name="studyId")
    title: SpecInput[str] = field(name="title")
    sponsor: SpecInput[str | None] = field(name="sponsor")


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

Typed table declarations are optional. Dynamic mode uses the same binding
pattern, but supplies a `DynamicTable` and resolves only the fields needed by
the build. This is the convenient default for ad hoc or evolving sources.

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
from the typed values assigned in its class body.

```python
@projection(inputs=(pharmacogenomics_release, study_registry_release))
class AssociationRows:
    target_id = field(PharmacogenomicsAnnotation.target.id)
    target_symbol = field(PharmacogenomicsAnnotation.target.symbol)
    target_name = field(PharmacogenomicsAnnotation.target.name)
    disease_id = field(provide.collection.expand(PharmacogenomicsAnnotation.disease_ids))
    study_id = field(PharmacogenomicsAnnotation.study_id)
    score = field(PharmacogenomicsAnnotation.score)
    study_title = field(
        provide.lookup.one(
            PharmacogenomicsAnnotation.study_id,
            in_=study_registry_release,
            key=StudyRegistry.study_id,
            on_missing="null",
        ).title,
    )
```

For example, `AssociationRows.score` is inferred as `Field[float]` and is a
typed, referenceable field. Use named projected tables when they are reused,
documented, tested, or materialised independently; a one-use local relation
expression is also valid.

## 4. Bindings and provided values

`provide` is the discoverable namespace for transforming values and producing
generated values. It has three subnamespaces: `value` for scalar expressions,
`collection` for collection operations, and `lookup` for keyed record
enrichment. Each operation creates a typed, immutable value declaration. IDE
completion on `provide.` exposes these three categories.

```python
provide.value.literal("pharmacogenomics_annotation::")
provide.value.concat("annotation::", AssociationRows.study_id)
provide.value.coalesce(AssociationRows.target_name, "unknown")
provide.value.uuid()
```

Typed field paths and dynamic fields are already valid `ValueInput`s. They
are accepted directly in projections, graph mappings, and `provide.*` calls:

```python
target_id = field(PharmacogenomicsAnnotation.target.id)
source = provide.value.concat("annotation::", AssociationRows.study_id)
target_endpoint = AssociationRows.disease_id
```

```text
ValueInput[T] = FieldPath[T] | DynamicField[T] | Value[T] | compatible literal T
```

When a specification contract is instantiated as a binding shape, its
`SpecInput[T]` members accept a binding `Expression[T]` or literal `T` directly.
The original topology or table field specifiers remain class-body declarations;
the binding layer interprets the supplied expressions against that structural
contract.

### Intention-oriented expressions, navigation, and cardinality

The value-expression system is shared by projections and graph bindings. A
projection uses expressions to define a logical data product; a graph binding
uses the same expressions to provide identifiers, endpoints, properties, and
other mapping values. In both contexts, an expression states what a value
means, not a physical query plan.

A projection names the bound tables from which its expressions may draw
values, making their declared references available for typed navigation. A
graph binding consumes the resulting projected values. The author does not
select joins, aliases, or any other execution mechanism; the compiler resolves
the physical relational operations needed to obtain a declared value.

`provide.lookup.one(...)` obtains a singular related record from another
declared input using a compatible key. It expresses an enrichment relationship,
not an execution plan. The target key must identify at most one record;
duplicate matches are diagnostics. `on_missing` declares the intended absence
policy, so the `AssociationRows.study_title` example above is inferred as
`Field[str | None]`.

A reference has declared cardinality. Navigating a singular reference produces
a singular value (which may be absent when the reference is optional).
Navigating a collection does not silently choose one value or duplicate a row:
the author must resolve its cardinality deliberately.

```python
# One projected output row for every disease ID on an annotation.
disease_id = field(provide.collection.expand(PharmacogenomicsAnnotation.disease_ids))

# A graph binding may use the same expression language for a generated ID.
identifier = provide.value.concat("annotation::", AssociationRows.study_id)

# One collection-valued output for values gathered from several input rows.
evidence_ids = field(provide.collection.collect(AssociationEvidence.id))
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

A graph binding is an immutable assignment from a projected table to one graph
component. It describes graph mapping, not acquisition or a physical query
plan.

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
    from_=AssociationRows,
    identifier=AssociationRows.target_id,
    properties={
        Target.symbol: AssociationRows.target_symbol,
        Target.name: AssociationRows.target_name,
    },
)


annotation_associated_with_disease: Final[EdgeBinding[AssociatedWith]] = edge_binding(
    target=AssociatedWith,
    from_=AssociationRows,
    identifier=provide.value.uuid(),
    source=provide.value.concat("pharmacogenomics_annotation::", AssociationRows.study_id),
    target_endpoint=AssociationRows.disease_id,
    properties={
        AssociatedWith.score: AssociationRows.score,
    },
)
```

Topology supplies edge type, endpoint types, property types, and annotations.
Bindings supply source values, identifiers, endpoints, and mapping policies.
Binding modules mirror the topology layout: node bindings live with their node,
and edge bindings live beneath their source node's `edges/` directory.

## Future: compiled build definition

The intended connection between layers is:

```text
topology declarations ─┐
                       ├─→ binding declarations ─┐
data declarations ─────┘                         ├─→ compile ─→ CompiledBuildDefinition ─→ build
target declaration ──────────────────────────────┘
```

Topology and data declarations are independent. Bindings are the first layer
that references both. A build declaration collects them with a target
declaration, including serialisable target configuration and credential
references. `compile` validates the complete declaration and produces one
immutable, target-specific `CompiledBuildDefinition`.

`build` consumes only `CompiledBuildDefinition` plus `BuildRuntime`. The latter
supplies resolved credentials and operational settings such as logging,
temporary storage, and resource limits; it never changes graph meaning or
contains declarations. This boundary lets execution lower the compiled plan to
DuckDB and invoke target writers without importing authoring classes or
interpreting `provide` expressions. Derived navigation and coverage/provenance
diagnostics are future inspection features, not artifacts that authors
maintain.
