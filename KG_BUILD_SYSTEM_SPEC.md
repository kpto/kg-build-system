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
expressions, projections, a three-tier topology hierarchy with category
endpoints, direct graph bindings, canonical blueprint schema version 3,
engine-neutral relational planning, DuckDB lowering, composable
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

                         create_blueprint ──> BuildBlueprint (schema v3)
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

The canonical vocabulary, as the unit names carried by a logical type, is:

```python
type UnitType = (
    bool | int | float | str | date | time | timestamp | uuid | CustomDataType
)
type DataType = UnitType | Struct | Array[DataType | None]
type AuthoringDataType = DataType | None
```

Canonical type names are uniformly lowercase: `bool int float str date time
timestamp uuid`, plus the nested `Array[T]` and `Struct{…}` above. The canonical
name is the identity carried by the logical type, the IR, the codecs and the
messages; a source type is *digested* into one of these names, and a source type
with no meaning-preserving canonical form is refused rather than coerced. A
capitalised name always marks a **representative type** instead: the class an
author writes in an annotation, which must be the very class of the value the
engine returns, because expressions, selections and property slots are
parameterised by it.

| Canonical | Representative | Class it denotes |
| --- | --- | --- |
| `bool`, `int`, `float`, `str` | `bool`, `int`, `float`, `str` | the builtins |
| `date` | `Date` | `datetime.date` |
| `time` | `Time` | `datetime.time` |
| `timestamp` | `Timestamp` | `datetime.datetime` |
| `uuid` | `Uuid` | `uuid.UUID` |

`Date`, `Time`, `Timestamp` and `Uuid` are exported by `kg_build_system.types` as
aliases of the stdlib classes, not as new classes. Normalization dispatches on class
identity, so the alias spelling and the stdlib spelling are one annotation and cannot
drift into two meanings.

`Array[T]` is the portable ordered-collection marker. It is deliberately not
`list[T]`, `Sequence[T]`, or a physical storage type. `Struct` declares a
portable nested record. `CustomDataType` identifies an application-defined
scalar by module and qualified name.

Authors express nullability with normal Python unions:

```python
Field[str | None]
Field[Timestamp | None]
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

A graph property is a scalar or a flat, homogeneous array of non-null scalars;
every canonical scalar above is valid in either position. Build and endpoint
keys stay non-null scalars, so an array becomes key material only through
`sorted().join()`. Nested arrays, arrays of structs, and arrays with null items
are refused at declaration: the first two are expanded or reified, and the third
is converted explicitly with `without_nulls()`. A target may narrow the item
types it can carry — Neo4j arrays hold primitives only, so temporal and uuid
items are refused there at compile.

Exact numerics, instants, durations and binary data are not canonical types:
`decimal(p, s)`, `instant`, `interval` and `binary` are deferred with their reasons
recorded, alongside `map` and `variant`, in
[`DUCKDB_TYPE_ACCEPTANCE_MATRIX.md`](DUCKDB_TYPE_ACCEPTANCE_MATRIX.md).

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

A field or graph property is described by a documentation string written
directly below its declaration, and an explicit `description` argument wins over
it:

```python
class InputTable(Table):
    identifier: Field[str] = field()
    """The caller-supplied row identifier."""

    label: Field[str] = field(description="Explicit description.")
    """Ignored: the explicit description wins."""
```

This is resolved once while the declaring class is created, so an inherited
member keeps the description of the class that declared it. Python discards such
a string literal rather than attaching it to anything, so it is recovered from
module source: a declaration whose module source cannot be read — a class built
by `exec`, or a module without a source file — simply resolves no member
description, exactly as if the documentation string had been omitted.

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
StrExpression            prepend, append, equals, replace,
                         before_separator, after_separator
BoolExpression           not_, and_, or_
CustomDataTypeExpression bindable custom scalar
ArrayExpression          bindable array value
StructExpression         bindable struct value
NullableExpression       bindable nullable value
```

Every canonical scalar expression carries `to_string()`, which renders it for key
material: bool, int, float, str, date, time, timestamp and uuid. Timestamps use
the framework's `T` separator; the other units use DuckDB's canonical cast.
Arrays and structs have no single text form and are refused. A nullable scalar
yields a nullable text expression; null policy stays at the selection.

The separator reader takes a separator and an optional 1-based occurrence:
`before_separator(separator, occurrence=1)` returns the text before that
appearance (the whole string when it does not appear), and
`after_separator(separator, occurrence=1)` returns the text after it, keeping
later separators (the empty string when it does not appear). The separator at
the cut is excluded by default; `include_separator=True` keeps it on the result
side. `equals` yields a Boolean predicate; `replace` replaces every literal
occurrence of its search text.

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
declared projection output, not the source implementation. Consequently,
projections may consume other projections without embedding or duplicating
their row plans.

Projection inputs are derived from expression references; there is no separate
input list. The projection dependency graph must be acyclic. Every projection
has one driving logical source. Additional sources require an explicit lookup
facility; implicit cross products are rejected.

## 7. Topology hierarchy and graph bindings

Topology declares graph meaning independently of input data:

```python
class InputNode(Node):
    label: PropertySlot[str] = property()
    description: PropertySlot[str | None] = property()


class ContainsEdge(Edge[InputNode, InputNode]):
    score: PropertySlot[float] = property()
```

Six public bases sit under one internal `@dataclass_transform` root in three
tiers: template (`NodeTemplate`/`EdgeTemplate`) shares property slots and
annotation flow and never enters the IR; category (`AbstractNode`/
`AbstractEdge[S, D]`) is a graph-visible parent recorded in the IR;
concrete (`Node`/`Edge[S, D]`) is bindable and terminal. `Edge` derives
from `AbstractEdge[S, D]` — that derivation is what makes endpoint descent
checkable, because `AbstractEdge`'s endpoint parameters are covariant while
`Edge`'s stay invariant. `Node` and `AbstractNode` are siblings under an
internal node-side root to which every endpoint-category parameter is bound,
so an edge-kind type argument is statically impossible. The hierarchy is a
tree: one category parent, any number of matching-kind mixins, and every
framework declaration in the MRO.

Canonical base order is templates, abstract parents, terminal base last.
Class creation enforces the same predicates order-insensitively: one direct
category parent, framework-lineage MRO, kind-paired templates and options,
and
endpoint descent — an edge inherits its endpoints from its abstract edge
parent and stays abstract when it re-declares nothing, while any re-declared
endpoint equals or descends from every abstract edge ancestor's.

```python
class Audited(NodeTemplate):
    options = NodeOptionsTemplate(annotations=(AuditTrail(track="audit"),))
    revision: PropertySlot[str] = property()


class EntityNode(AbstractNode):
    options = NodeOptions(annotations=(NodeLabel("Entity"),))
    title: PropertySlot[str] = property()


class RecordNode(Audited, EntityNode, Node): ...


class ContainsEdge(Weighted, AbstractEdge[EntityNode, EntityNode]):
    options = EdgeOptions(annotations=(EdgeLabel("CONTAINS"),))


class ContainsMetricEdge(ContainsEdge, Edge[EntityNode, MetricNode]): ...
# descended; the target category narrowed EntityNode -> MetricNode
```

Every tier declares `options`, and the options type identifies the tier:
`NodeOptions`/`EdgeOptions` (name, description, annotations) for IR-visible
classes, annotations-only `NodeOptionsTemplate`/`EdgeOptionsTemplate` for
templates. For an IR-visible class the effective name is own `options.name`
or own class name, never mixed; the effective description is own
`options.description` or own docstring, never inherited; effective
annotations are template options in C3 order — each template exactly once,
category parents included — then own `options.annotations`. A category's own
options stay on the category's IR entry, reachable through `parent`. Label
uniqueness is enforced against the effective set at class creation.

Target-neutral `NodeLabel` and `EdgeLabel` annotations optionally override the
computed semantic label of a graph component. At most one matching annotation
may be supplied. A target may interpret the effective label using its own
native vocabulary; the Neo4j target maps a node label to `:LABEL` and an edge
label to the relationship `:TYPE` header.

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

Each edge endpoint may name a category. An endpoint of an abstract declared
side is supplied with an `endpoint(...)` token naming a concrete component;
concrete declared endpoints default to the declaration, and an explicit
token naming the declared component stays valid. `edge_binding` overloads
require each token exactly when its declared endpoint is abstract, and the
token's covariance enforces category membership.

```python
edge_binding(
    target=ContainsMetricEdge,
    source_node=endpoint(RecordNode),
    build_key=...,
    source_build_key=...,
    target_build_key=...,
)
```

Endpoints reference the component, not a producer: identity is per component
and each binding names the endpoint pair it uses rather than the cross
product of the declared categories. Abstract components are never binding
targets.
Blueprint validation checks that a supplied endpoint is concrete and is equal
to or descends from the declared category through the IR parent chain.

A binding owns its complete relational row context. Expansions and filters in
one binding never alter another binding, even when both refer to the same
table or projection.

## 8. Names, options, and annotations

Every declaration has a stable logical name. Explicit `options.name` wins;
otherwise names are inferred in snake case. One matching tier suffix is removed,
for example `InputTable` becomes `input`, `InputNode` becomes `input`, and
`ContainsEdge` becomes `contains`. Topology declarations should name their tier
explicitly — `RecordNode`, `DocumentedAbstractNode`, `DocumentedNodeTemplate` —
and the matching suffix is stripped, so an abstract node and its template both
infer `documented`. Abstract components strip `AbstractNode`/`AbstractEdge`
before falling back to the terminal `Node`/`Edge` suffix; template suffixes
carry no logical name, since a template never enters the IR.

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

Definitions contain credential references, never resolved credentials. Every
required table has exactly one source in the blueprint supplied to compilation.

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
`BuildBlueprint` schema version 3 for inspection, serialization, and advanced
tooling. Normal builds call `compile` directly. A blueprint contains immutable
definitions for:

- structs and fields;
- final tables and fields;
- projections and output expressions;
- nodes, edges, and properties, including abstract categories flagged in the
  IR with their nearest abstract parent; the component closure walks binding
  targets, edge endpoints, and their full abstract chains;
- node and edge bindings, recording endpoint tokens that name a concrete
  component for an abstract declared side;
- source bindings;
- configured workflow modules.

Definitions use stable symbol IDs and logical names. Struct identity is the
`(module, qualname)` pair that `StructType` carries; the logical name is display,
so same-named structs from different modules are distinct declarations. The
blueprint contains no Python class objects or authoring domain objects. Its JSON
codec is deterministic and round-trippable.

Compilation IRs live in each owning domain's `ir.py`; they are not exported
from the root authoring API. Domain models never retain IR instances. Mapping
modules form the one-way boundary from domain models to compilation IRs.
Runtime workflow execution converts its serialized workflow IR into workflow
domain models before dispatching module business logic.

`compile` and `create_blueprint` support three declaration inputs: the calling
file's namespace when only `modules` is supplied, an explicit
`namespace_path`, or explicit `bindings` and `sources`. `compile` additionally
accepts a prebuilt `blueprint`. Every mode requires `modules`; those modules,
followed by the mandatory core module, are the complete module composition for
the operation. Namespace discovery recursively imports an importable Python
namespace and finds module-level binding and source objects. Re-exported
objects are deduplicated by identity. Discovery never invokes arbitrary
factories.

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
string, Boolean, and coalesce operations into inspectable SQL. Every runtime
relational artifact exposes a stable logical view. Core source, projection,
binding, and graph-aggregation views remain lazy so DuckDB can optimize through
the complete query chain and push projections and filters into physical scans.
When an upper workflow layer requests a reuse or snapshot boundary, the runtime
may instead back the same public view with a private materialized table. Which
relations deserve that boundary is unresolved; see
`WORKFLOW_RELATION_REUSE.md`.

## 12. Compilation, workflow, and execution

> [WORKFLOW_SUBPACKAGE_SPEC.md](WORKFLOW_SUBPACKAGE_SPEC.md) §1–7 — the workflow data model, assembly rules, contract, and execution.

The public `compile` API creates or accepts the canonical blueprint and appends
the mandatory core module after the configured extension modules. It validates
the blueprint schema version and compiles every registered module through the
compile-time capability interface.
The workflow domain assembles the ordered contributions into a
dependency-aware `WorkflowDefinition`, which the compiler freezes into a
`WorkflowContractIR`. The compiler does not import or bootstrap concrete module
implementations. `compile(blueprint=...)` remains available for advanced callers using
an auxiliary prebuilt blueprint, and an incomplete wiring is a build failure naming every
input it could not feed and every output nothing reads.

The workflow contract includes:

- a contract schema version;
- frozen module definitions, executable workflow steps, and resolved
  connections;
- inspectable SQL and other instruction data in each module's own variables;
- the workflow fingerprint;
- optional opaque compilation provenance containing the blueprint and its
  fingerprint.

Workflow does not interpret compilation provenance. Execution settings are
supplied through `BuildRuntime`. The contract never contains resolved
credentials.

The core module creates source-view, projection-view, binding-view, and graph
aggregation-view steps. Extension modules take artifacts by semantic
`ArtifactType` rather than temporary relation names. Current supplied modules
include exact duplicate collapse, compatible-fact merging, conflicting-value
validation, file output, meta-graph description, and Neo4j administrative-import
output.

The meta-graph module writes one JSON document describing the effective
topology: every component a binding targets, the abstract ancestors and edge
endpoint categories those components depend on, and nothing else. It records the
hierarchy by logical name (`parent`, `children`, `depth`) alongside each
component's debugging symbol ID, its effective semantic label and description,
its properties with normalized logical types, and per-component record counts.
Abstract categories are never binding targets and so produce no artifact of their own;
their count is the sum over their concrete descendants. The step takes the graph-record
artifact for each effective component, so a count reflects whatever stage last owned that
type — after collapse, merge, or validation when those modules are configured.

Each property also carries example values taken from those same records: up to
`example_limit` of the most common values per property, from DuckDB's
`approx_top_k` frequency sketch. Count and examples together form a single
aggregate query per component, so the relation is streamed once with memory that
does not depend on its size. Counts stay exact; examples are approximate and are
ordered canonically so two builds publish the same document. A category has no
rows of its own, so it inherits examples from its descendants by property name.
This makes the document data-bearing rather than pure metadata; it sits beside
`graph.jsonl`, which already holds every value.

The module also writes a companion page: one self-contained HTML file with d3
inlined and the same document embedded as JSON. It draws the topology as a
force-directed diagram in which every component is selectable — node components
and abstract categories as vertices, edge components as links between their
declared endpoints, with the is-a hierarchy drawn in a separate style — and the
selection panel shows description, semantic label, record counts, endpoints, and
the property table. It needs no network and no sibling files.

Static topology travels in the meta-graph module's variables, because a module
executor receives no blueprint.

`build` synchronously consumes only `WorkflowContractIR` and `BuildRuntime`. It
imports the module classes named in the contract, validates runtime
configuration, executes ready steps in dependency order, propagates failed or
skipped inputs, and verifies every returned artifact against its declared
output. Module executor construction and step handlers are synchronous;
compile-time module compilation remains a separate asynchronous lifecycle.

The output directory receives published artifacts, `workflow_contract.json`, and
`build_report.json`. It defaults to `build` beneath the current working
directory. The working directory defaults to `_workdir` beneath the selected
output directory; relative working-directory arguments are resolved beneath
that output directory. Temporary storage defaults to a system temporary directory. Runtime
credentials are resolved through runtime services. Credential values and their
option schemas are opaque to the blueprint and workflow contract. The module
owning a credentialed execution instruction defines and validates those
runtime-only options; resolved values never enter the contract.

The executor owns a DuckDB relation service that returns opaque runtime-only
`RelationRef` values. Every reference names a public view. A module may define a
lazy view or request a reuse/snapshot boundary, in which case the service creates
a private persistent table and exposes it through the same public view shape.
The service checkpoints once after each step that created materialized backing
tables. Modules use it for relation definition, queries, Parquet export, and
filesystem registration; physical table names and storage lifecycle policy do
not leak into consuming module implementations. All DuckDB operations and
result fetching are serialized through one service-owned worker thread. The
calling workflow thread waits in interruptible intervals; on Ctrl-C it invokes
DuckDB's connection interrupt, waits for the pending operation to settle, and
then propagates `KeyboardInterrupt`. Connection shutdown also runs on the
worker before the worker is joined.

`BuildRuntime` exposes four DuckDB controls:

- `duckdb_storage` is `"memory"` by default. In-memory databases and their spill
  files use the build's temporary directory. `"disk"` opens an ephemeral
  database and places spill files beneath the working directory for the build's
  duration.
- `duckdb_compression` defaults to `True` and controls lightweight column
  compression in either storage mode.
- `duckdb_memory_limit` accepts DuckDB size strings such as `"4GiB"`; when
  omitted, DuckDB retains its platform-derived default memory limit.
- `duckdb_threads` controls query parallelism when supplied.

The Neo4j target creates one export step per bound node or edge component. Each
step consumes exactly that component's terminal graph-record artifact and writes
one Parquet file. Parquet column names contain the `neo4j-admin database import`
headers directly: node IDs use stable per-component ID spaces, edge endpoints
reference those spaces, and component labels are written as `:LABEL` or
`:TYPE`. A final script step depends on every component export, aggregates their
row counts, publishes the bundle summary, and writes a standalone Python script
that locates a local `neo4j-admin` executable and runs a full Parquet import
without requiring this package at import time.

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
  workflow/          # domain models, assembly, compilation IRs, mapping, execution
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
- Describe a component or member by what it means in the graph, not by how the
  build derives it. A description states that a measurement can be deactivated,
  not that it is `not enabled` after an expansion.
- Keep topology and bindings discoverable in the compact node-first layout
  defined below.
- Name each topology tier explicitly in the class name — `RecordNode`,
  `DocumentedAbstractNode`, `ProvenancedNodeTemplate` — so the tier suffix
  is visible at every use site and is stripped from the logical name.
- Publish a grain as a projection when more than one binding needs it. A
  projection is a named row product, so the grain is what it publishes, and
  reaching a new grain with a further `expand` needs a further projection
  because a projection has one row plan. A one-step derivation over a scan the
  build already shares needs only a shared selection name, not a projection.
- Keep physical locations and provenance in source bindings.
- Treat generated packages, blueprint JSON, workflow contracts, and SQL as
  inspectable development artifacts.
- Check static contracts with Pyright as well as runtime behavior.

### Recommended graph-pipeline layout

Consumer projects should use a compact node-first package layout. A direct
child package of `topology/` represents one node. The node declaration lives in
that package's `__init__.py`, while its other public modules declare edges that
originate from that node. `bindings/` mirrors the same paths: its package
`__init__.py` contains the node binding and its edge modules contain the
corresponding edge bindings.

```text
graph_pipeline/
  build.py
  sources.py                              # physical source bindings
  data/
  table/
    __init__.py                         # generation requests, when used
    generated_contract/                 # generated Table/Struct package
      __init__.py
      .kbs-generation.json
    projections/                        # reusable logical data products
      __init__.py
      expanded_target.py
  topology/
    target/
      __init__.py                       # TargetNode
      has_association_by_overall_direct__disease.py
    disease/
      __init__.py                       # DiseaseNode
  bindings/
    target/
      __init__.py                       # TargetNode binding
      has_association_by_overall_direct__disease.py
    disease/
      __init__.py                       # DiseaseNode binding
```

An edge module name has the form
`<relationship_predicate>__<destination_node>.py`. Both parts use snake case,
and the double underscore visually separates the relationship from its
destination. For example:

```text
Target -[HAS_ASSOCIATION_BY_OVERALL_DIRECT]-> Disease

topology/target/has_association_by_overall_direct__disease.py
bindings/target/has_association_by_overall_direct__disease.py
```

The source node is implicit in the containing package, but the graph semantics
are not inferred from filesystem names. The edge declaration must still state
its endpoints through `Edge[TargetNode, DiseaseNode]`, and its effective graph
label remains declaration metadata. The layout is an authoring and discovery
convention rather than a second topology model.

Public edge modules should not be re-exported from the node package's
`__init__.py`; keeping imports directed from an edge module toward its endpoint
node packages avoids circular imports. Underscore-prefixed modules such as
`_shared.py` are reserved for private helpers and do not represent edges.
Templates and categories shared across node packages are first-class
declarations and live in a plain module directly under `topology/` (for
example `topology/common.py`); they carry no `bindings/` mirror because
abstract components and templates are never binding targets.

## 15. Delivery scope

### Implemented

- canonical logical types and type codecs;
- unified typed fields for scalars, structs, arrays, and custom scalar types;
- specialized expressions with explicit null and row semantics;
- nested `pick`, nested/shared `expand`, and projection chaining;
- three-tier topology hierarchy (templates, categories, concrete components)
  with category edge endpoints and per-binding endpoint tokens;
- direct typed node and edge bindings;
- annotations across declaration, binding, and source layers;
- immutable blueprint schema version 3 and deterministic JSON codecs;
- engine-neutral relational plans and DuckDB lowering;
- dependency-aware workflow contracts and execution reports;
- file graph output and supplied validation/merge/deduplication modules;
- an effective-topology meta-graph JSON document with hierarchy, labels,
  descriptions, property logical types, example values, and per-component record
  counts, plus a self-contained HTML page visualising the same document;
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
  physical schema can provide it. The type half of that item is now in scope and
  specified: the widened canonical vocabulary of §3 (`date time timestamp uuid`),
  the ingest **digest** gate that maps each DuckDB type onto a canonical type or
  refuses it with a recorded reason, and declared temporal promotion at generation
  time for a column whose reader cannot type it itself.
- explicitly **out** of that scope: comparison and filtering operators for the
  temporal and `uuid` types. Values of those types store, deduplicate, merge and
  export correctly, but no new expression operators are offered for them, and
  `decimal(p, s)`, `instant`, `interval`, `binary`, `map` and `variant` remain
  non-canonical.

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
