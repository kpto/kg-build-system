# Knowledge Graph Build System — Unified Specification

## 1. Purpose and status

This is the canonical specification for the Knowledge Graph Build System. It
describes the implemented authoring model, canonical intermediate
representations, compilation workflow, and execution boundary.

The system builds knowledge graphs from typed logical data contracts. Graph
meaning is independent of physical acquisition, and both are independent of
target-specific execution. Python is the authoring surface, canonical frozen
objects are the portable definition format, and DuckDB is the first relational
engine.

The current implementation includes typed nested data declarations, typed
expressions, projections, direct graph bindings, canonical blueprint schema
version 2, engine-neutral relational planning, DuckDB lowering, composable
workflow modules, file and Neo4j administrative-import output, and edit-time
generated data-contract packages.

## 2. Core model

```text
topology ──────── graph components and scalar properties
data contracts ── logical tables, unified fields, structs, projections
expressions ───── typed values plus local row effects
bindings ──────── expressions mapped into graph components
sources ───────── physical locations and credential references
modules ───────── compilation and execution extensions
```

```text
Python declarations/sources/modules/settings ──> compile ──> WorkflowContractIR
                                                     │
runtime configuration ─────────────────> build <─────┘

                         create_blueprint ──> BuildBlueprint (schema v2)
                         auxiliary inspection and serialization boundary
```

Topology, data contracts, expressions, and bindings are reusable logical
declarations. Sources, modules, settings, and runtime configuration are
composition choices.

### Principles

- Separate graph meaning, data acquisition, relational planning, and execution.
- Use one logical-type domain model in authoring and map it explicitly into a
  structurally equivalent compilation IR model.
- Make invalid operations unavailable through specialized expression types.
- Represent field references as expressions rather than as a parallel value
  hierarchy.
- Keep null behavior and row-producing behavior explicit.
- Compile authoring objects into immutable IR containing no Python class
  objects.
- Plan each projection and binding as a self-contained relational product.
- Preserve portable annotations without requiring the core to interpret them.
- Store credential references in definitions and resolved secrets only at
  runtime.

## 3. Canonical logical types

The author-facing vocabulary is:

```python
type UnitType = bool | int | float | str | CustomDataType
type DataType = UnitType | Struct | Array[DataType | None]
type AuthoringDataType = DataType | None
```

`Array[T]` is the portable ordered-collection marker. It is deliberately not
`list[T]`, `Sequence[T]`, or a physical storage type. `Struct` declares a
portable nested record. `CustomDataType` identifies an application-defined
scalar by module and qualified name.

Authors express nullability with normal Python unions:

```python
Field[str | None]
Field[Array[int] | None]
Field[Array[str | None]]
Field[Array[str | None] | None]
```

The framework normalizes these into immutable logical types:

```text
UnitType(name)
CustomType(module, qualname)
StructType(module, qualname)
ArrayType(item)
NullableType(value)
```

`Nullable[T]` is an internal typing marker corresponding to
`NullableType(T)`. Authors do not use it in declarations. Canonical nullable
types are flattened and never wrap another `NullableType`.

Graph properties and graph identity keys must be scalar. Build and endpoint
keys must additionally be non-null. Arrays and structs remain valid expression
values but cannot be graph properties or keys.

## 4. Unified fields and data declarations

Every table or struct member uses the same descriptor:

```python
class Field[T]: ...

def field[T](
    *,
    name: str | None = None,
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> Field[T]: ...
```

There are no separate scalar, struct, or collection field classes.

```python
class LocationStruct(Struct):
    city: Field[str] = field()
    room: Field[str | None] = field()


class EventStruct(Struct):
    code: Field[str] = field()
    labels: Field[Array[str | None] | None] = field()


class InputTable(Table):
    identifier: Field[str] = field()
    label: Field[str] = field()
    description: Field[str | None] = field()
    optional_count: Field[int | None] = field()
    optional_flag: Field[bool | None] = field()
    location: Field[LocationStruct | None] = field()
    events: Field[Array[EventStruct] | None] = field()
```

Descriptor access produces a typed selection. Its structural specialization is
selected from the normalized logical type, and `.expression` exposes the
matching bindable calculation family to static analysis.

Final declaration bases are `Table`, `Struct`, `Projection`, and `TableGroup`.
`TableTemplate` remains available for reusable table shapes carrying framework
metadata. Only final `Table` declarations may be source-bound or placed in
table groups.

Framework `options` values are class metadata, not fields or constructor
arguments. Descriptions default to class docstrings unless explicitly
overridden.

## 5. Selections and typed expressions

Field access produces a `ValueSelection[T]`. Selections represent a location
in a logical product and own structural navigation, row expansion, and null
policy. Their `.expression` property exposes the bindable calculation for the
selected value. A field reference is one expression-model variant; it is not a
parallel value-reference hierarchy.

Selection families are specialized by logical shape:

```text
ValueSelection[T]       scalar selection
ArraySelection[T]       expand
StructSelection[T]      pick
NullableSelection[T]    default_to, where_present, nullable pick/expand
```

Bindable expression families expose calculation operations only:

```text
IntExpression            add, sub
FloatExpression          add, sub
StrExpression            prepend, append
BoolExpression           not_, and_, or_
CustomDataTypeExpression bindable custom scalar
ArrayExpression          bindable array value
StructExpression         bindable struct value
NullableExpression       bindable nullable value
```

Calculations preserve the most specific useful expression family:

```python
InputTable.identifier.expression.prepend("input::")
InputTable.optional_count.default_to(0).expression.add(1)
InputTable.optional_flag.where_present().expression.not_()
```

Portable literals are created with `value_expression(...)`. Null, empty-array,
and all-null-array literals require an explicit logical type. Struct and custom
type values cannot be embedded as literals.

### Struct selection

Struct navigation uses `pick` with a selector:

```python
city = InputTable.location.pick(lambda value: value.city)
```

Fields read through the selector are temporary member selections associated
with their declaring struct. The parent selection turns the selected member
into a normal selection backed by a canonical field reference or
`struct_field` operation. Temporary member state cannot cross a terminal
authoring boundary.

Nullability propagates through the whole path. Selecting a required field from
a nullable struct produces a nullable result. Selecting an already-nullable
field does not create nested nullability:

```python
InputTable.location.pick(lambda value: value.city)  # nullable string
```

### Array expansion

`expand()` explicitly converts an array selection into one row per item:

```python
event = InputTable.events.expand()
label = event.pick(lambda value: value.labels).expand()
```

A nullable array produces no rows when null. Item nullability is independent:
expanding `Array[T | None]` produces a nullable item selection.

Each `expand()` records an explicit `expand` operation with a stable scope derived from
the logical field path. Repeated expressions with the same scope share one
expansion. Nested scopes are planned parent-first.

### Null handling

A `NullableSelection` owns null policy. Its bindable `NullableExpression`
deliberately exposes no null-policy or type-specific operations:

- `default_to(value)` replaces null and returns a non-null selection;
- `where_present()` filters the containing relational product when the value
  is null and returns a non-null selection.

These operations differ semantically. `default_to` preserves the row;
`where_present` adds a local filter row effect. A projection or binding owns
that effect, so it cannot change a sibling product.

## 6. Projections

A projection is a named logical data product. Its outputs use
`projection_field(...)`:

```python
event = InputTable.events.expand()


class EventProjection(Projection):
    input_id = projection_field(InputTable.identifier)
    code = projection_field(event.pick(lambda value: value.code))
    label = projection_field(
        event.pick(lambda value: value.labels).expand().default_to("unknown")
    )
```

Reading `EventProjection.code` returns a field-reference selection for the
materialized projection output, not the source implementation. Consequently,
projections may consume other projections without embedding or duplicating
their row plans.

Projection inputs are derived from expression references; there is no separate
input list. The projection dependency graph must be acyclic. Every projection
has one driving logical source. Additional sources require an explicit lookup
facility; implicit cross products are rejected.

## 7. Topology and graph bindings

Topology declares graph meaning independently of input data:

```python
class InputNode(Node):
    label: PropertySlot[str] = property()
    description: PropertySlot[str | None] = property()


class ContainsEdge(Edge[InputNode, InputNode]):
    score: PropertySlot[float] = property()
```

Target-neutral `NodeLabel` and `EdgeLabel` annotations optionally override the
computed semantic label of a graph component. At most one matching annotation
may be supplied. A target may interpret the effective label using its own native
vocabulary; the Neo4j target maps a node label to `:LABEL` and an edge label to
the relationship `:TYPE` header.

```python
class InputNode(Node):
    options = NodeOptions(annotations=(NodeLabel("Input"),))


class ContainsEdge(Edge[InputNode, InputNode]):
    options = EdgeOptions(annotations=(EdgeLabel("CONTAINS"),))
```

`PropertySlot[T]` is the static constructor contract for an authoring
selection or expression of type `T`. Property declarations remain separate metadata; graph
properties do not inherit from expression objects.

Selections and expressions bind directly. Terminal declaration APIs normalize
selections immediately and store only bindable expressions. There is no
`bind(...)` wrapper:

```python
input_binding = node_binding(
    target=InputNode,
    build_key=InputTable.identifier.expression.prepend("input::"),
    properties=InputNode(
        label=InputTable.label,
        description=InputTable.description,
    ),
)
```

`node_binding` requires a non-null scalar build key. `edge_binding` requires
non-null scalar build, source, and target keys. Keys may use any supported
scalar type. Property inputs must exactly match their declared logical
type, except that a non-null value may satisfy a nullable property.

A binding owns its complete relational row context. Expansions and filters in
one binding never alter another binding, even when both refer to the same
table or projection.

## 8. Names, options, and annotations

Every declaration has a stable logical name. Explicit `options.name` wins;
otherwise names are inferred in snake case. One matching terminal layer suffix
is removed, for example `InputTable` becomes `input`, `InputNode` becomes
`input`, and `ContainsEdge` becomes `contains`.

Field, property, and projection-field names default to their Python attribute
name converted to snake case. One trailing underscore escapes a reserved
framework attribute such as `options`.

Annotations are frozen dataclass values with a stable `namespace` and
`annotation_id`. Their fields become JSON-compatible arguments. Annotations
may be attached to declarations, fields, properties, projections, bindings,
and sources. The blueprint stores only the portable namespace, ID, and frozen
arguments; it never stores the annotation Python class.

Unknown annotations are preserved. Module compilers receive the complete
annotated blueprint and may interpret any annotations they recognize.

## 9. Table groups and physical sources

`TableGroup` gives final tables a named nested catalog structure. Groups may
contain final tables or other groups. Empty groups, cycles, duplicate table
inclusion, and duplicate catalog paths are rejected.

`bind_source` associates a final table or group with a physical configuration:

```python
source = bind_source(
    target=InputTable,
    config=DataSourceConfig(
        location="data/input.json",
        format=InputFormat.JSON,
        version="2026-08",
    ),
)
```

Group source bindings require a layout using `{group_path}` and
`{table_name}`. They expand into canonical per-table source definitions.

Definitions contain credential references, never resolved credentials. A
concrete compilation resolves every required table to exactly one effective
source. Explicit compile-time source overrides replace matching blueprint
sources without mutating logical declarations.

## 10. Canonical expression and blueprint IR

Expression authoring uses an immutable domain expression tree. Compilation
maps that tree into a separate, engine-neutral expression IR tree:

```text
LiteralExpression
FieldReferenceExpression(source, path)
OperationExpression(operator, arguments, parameters)
```

Every domain expression carries its logical type and may retain authoring-time
`RowSemantics`, but expression IR records only the explicit expression syntax
and normalized logical type. `expand` and `where_present` remain ordinary explicit
operations. Relational planning derives expansion identities, ordering, and
filters from that syntax; planner scopes and traversal hints never enter the
blueprint. The compiler maps logical types, expressions, annotations, data
declarations, topology, bindings, and workflow definitions into domain-owned
IRs. Codecs serialize only those IRs and frozen JSON values.

The auxiliary `create_blueprint` function validates declarations and produces
`BuildBlueprint` schema version 2 for inspection, serialization, and advanced
tooling. Normal builds call `compile` directly. A blueprint contains immutable
definitions for:

- structs and fields;
- final tables and fields;
- projections and output expressions;
- nodes, edges, and properties;
- node and edge bindings;
- source bindings;
- configured workflow modules.

Definitions use stable symbol IDs and logical names. The blueprint contains no
Python class objects or authoring domain objects. Its JSON codec is
deterministic and round-trippable.

Compilation IRs live in each owning domain's `ir.py`; they are not exported
from the root authoring API. Domain models never retain IR instances. Mapping
modules form the one-way boundary from domain models to compilation IRs.
Runtime workflow execution converts its serialized workflow IR into workflow
domain models before dispatching module business logic.

`compile(namespace_path=...)` recursively imports an importable Python
namespace and discovers module-level binding and source objects while creating
its internal blueprint. The auxiliary `create_blueprint` exposes the same
discovery boundary. Re-exported objects are deduplicated by identity. Discovery
never invokes arbitrary factories.

## 11. Relational planning and DuckDB lowering

Canonical expressions lower in two stages:

```text
expression outputs
      │
      v
RelationPlan(scans, expands, filters, outputs)
      │
      v
engine-specific DuckDB SQL
```

`lower_product` plans one projection or binding. It derives its driving scan,
deduplicates shared expansions, orders nested expansions parent-first, and
collects `where_present` filters. Plans remain independent of SQL syntax.

The DuckDB engine lowers scans, struct access, `UNNEST`, filters, numeric,
string, Boolean, and coalesce operations into inspectable SQL. Relational
products are materialized as temporary tables so downstream projections and
bindings reference stable relations.

## 12. Compilation, workflow, and execution

The public `compile` API creates the canonical blueprint internally and appends
the mandatory core module after the configured extension modules. It validates
blueprint schema version 2, resolves effective sources and overrides, and
compiles every registered module through the compile-time capability interface.
The workflow domain then assembles the ordered contributions into one
dependency-aware `WorkflowContractIR`. The compiler does not import or
bootstrap concrete module implementations. `compile(blueprint=...)` remains
available for advanced callers using an auxiliary prebuilt blueprint.

The workflow contract includes:

- a contract schema version;
- frozen module definitions, executable workflow steps, and resolved
  connections;
- effective source instructions and inspectable SQL in module-owned step
  payloads;
- the workflow fingerprint;
- optional opaque compilation provenance containing the blueprint, its
  fingerprint, compilation settings, and overrides.

Workflow does not interpret compilation provenance. Execution settings are
supplied through `BuildRuntime`. The contract never contains resolved
credentials.

The core module creates source-materialization, projection, binding, and graph
aggregation steps. Extension modules claim artifacts by semantic
`ArtifactRole` rather than temporary relation names. Current supplied modules
include exact duplicate collapse, compatible-fact merging, conflicting-value
validation, file output, and Neo4j administrative-import output.

`build` consumes only `WorkflowContractIR` and `BuildRuntime`. It imports the module
classes named in the contract, validates runtime configuration, executes ready
steps in dependency order, propagates failed or skipped inputs, and verifies
every returned artifact against its declared output slot.

The output directory receives published artifacts, `workflow_contract.json`, and
`build_report.json`. The working directory defaults to the output directory;
temporary storage defaults to a system temporary directory. Runtime
credentials are resolved through runtime services. Credential values and their
option schemas are opaque to the blueprint and workflow contract. The module
owning a credentialed execution instruction defines and validates those
runtime-only options; resolved values never enter the contract.

Runtime relational intermediates live in a compressed in-memory DuckDB
database. The executor owns a DuckDB relation service that materializes
persistent tables, returns opaque runtime-only `RelationRef` values, and
checkpoints once after each step that created relations. Modules request
materialization and use the service for queries, Parquet export, and filesystem
registration; compression and storage lifecycle policy do not leak into module
implementations. DuckDB applies lightweight column compression to checkpointed
tables and spills constrained data into the build's temporary directory.
`BuildRuntime.duckdb_memory_limit`
accepts DuckDB size strings such as `"4GiB"`; when omitted, DuckDB retains its
platform-derived default memory limit. `BuildRuntime.duckdb_compression`
controls in-memory table compression and defaults to `True`.
`BuildRuntime.duckdb_threads` continues to control query parallelism.

The Neo4j target consumes terminal graph-record artifacts and writes one
Parquet file per node or edge component. Parquet column names contain the
`neo4j-admin database import` headers directly: node IDs use stable
per-component ID spaces, edge endpoints reference those spaces, and component
labels are written as `:LABEL` or `:TYPE`. The bundle also contains a
standalone Python script that locates a local `neo4j-admin` executable and runs
a full Parquet import without requiring this package at import time.

## 13. Edit-time generated packages

Data contracts may be generated at edit time from typed, inert requests in an
author-owned package `__init__.py`. Generated tables and structs are ordinary
final declarations and participate in blueprint compilation exactly like
handwritten declarations.

Compilation never invokes providers or repairs stale generated content.
`kbs generate --check` is the canonical freshness check. The complete request,
ownership, check, watch, and pruning contract is defined in
`EDIT_TIME_GENERATED_PACKAGE_SPEC.md`.

## 14. Project organization and practices

```text
kg_build_system/
  annotations/       # annotation domain model and compilation IR
  types/             # logical-type domain model, IR, mapping, and codecs
  expressions/       # authoring domain tree plus compilation IR and mapping
  table/             # data-contract domain models and compilation IRs
  topology/          # topology domain models and compilation IRs
  binding/           # binding domain models and compilation IRs
  compile/           # blueprint aggregate, compiler, codecs, and contracts
  relational/        # engine-neutral planning and plan IRs
  engines/duckdb/    # SQL lowering
  modules/           # core, operators, and targets
  workflow/          # domain models, compilation IRs, mapping, execution
  code_generation/   # edit-time generated packages
demo/                 # importable end-to-end example
tests/                # runtime and static typing contracts
```

Authoring practices:

- Use `Field[T]` for every logical table and struct member.
- Express nullability with `T | None`; do not use internal `Nullable[T]` in
  declarations.
- Use `pick` and `expand` so nested selection and row production remain explicit.
- Choose `default_to` versus `where_present` deliberately.
- Keep topology and bindings discoverable in a node-first layout.
- Use projections to name reusable data products and isolate expansion scopes.
- Keep physical locations and provenance in source bindings.
- Treat generated packages, blueprint JSON, workflow contracts, and SQL as
  inspectable development artifacts.
- Check static contracts with Pyright as well as runtime behavior.

## 15. Delivery scope

### Implemented

- canonical logical types and type codecs;
- unified typed fields for scalars, structs, arrays, and custom scalar types;
- specialized expressions with explicit null and row semantics;
- nested `pick`, nested/shared `expand`, and projection chaining;
- direct typed node and edge bindings;
- annotations across declaration, binding, and source layers;
- immutable blueprint schema version 2 and deterministic JSON codecs;
- engine-neutral relational plans and DuckDB lowering;
- dependency-aware workflow contracts and execution reports;
- file graph output and supplied validation/merge/deduplication modules;
- Neo4j administrative-import Parquet bundles and standalone import scripts;
- edit-time generated table and table-group packages;
- an importable demo combining deep nesting, null handling, expansions, and
  multiple projection layers.

### Remaining extensions

- explicit lookup planning with uniqueness and missing-match diagnostics;
- grouping and collection aggregation;
- dynamic fields guarded by an `Unknown` type;
- broader target capability checks and ontology annotations;
- richer source schema metadata, including nested-member nullability where the
  physical schema can provide it.

### Future

- additional generation providers and schema formats;
- distributed, scheduled, incremental, and change-data-capture builds;
- arbitrary non-portable Python transformations;
- target migrations and additional database targets;
- graphical editing and cross-product optimization.

## 16. Success criteria

The implemented vertical slice succeeds when one importable demo:

1. obtains a typed table contract from edit-time generation;
2. declares deep nested fields and nullable top-level values;
3. composes nested expansions and chained projections;
4. normalizes typed selections and expressions directly into node and edge bindings;
5. compiles to deterministic blueprint JSON, a frozen workflow, and
   inspectable DuckDB SQL;
6. executes to deterministic normalized graph records with a build report.

The broader MVP succeeds when the same blueprint can be composed with multiple
valid sources and equivalent file/database targets while preserving normalized
graph records, annotations, diagnostics, and fingerprints.
