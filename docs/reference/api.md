# Public API

The authoring surface is imported from `kg_build_system`; supplied modules come
from `kg_build_system.modules` and the type vocabulary from
`kg_build_system.types`. This page is a task-ordered lookup; each group links to
the concept page that explains it.

!!! note "Import paths"
    `register_module` and the built-in modules are in `kg_build_system.modules`; `Array`, `Date`, `Time`, `Timestamp`, `Uuid`, and `CustomDataType` are also in `kg_build_system.types`. See [Type vocabulary](types.md) and the [Glossary](glossary.md).

## Declare graph topology

Topology is independent of input data: each declaration names a graph
component, its properties, and — for an edge — its endpoint categories.

| Name | Purpose | Key arguments |
| --- | --- | --- |
| `Node` / `AbstractNode` | Concrete bindable node; graph-visible category node | Subclass with `options` and `PropertySlot` properties |
| `Edge[S, D]` / `AbstractEdge[S, D]` | Concrete edge; graph-visible category edge | Two node-side type arguments |
| `NodeTemplate` / `EdgeTemplate` | Inert mixins sharing slots and annotations | Matching-kind mix in the MRO |
| `NodeOptions(name=None, description=None, annotations=())` / `NodeOptionsTemplate(annotations=())` | Node identity and annotations; the template form is annotations only | Set as the class variable `options` |
| `EdgeOptions(...)` / `EdgeOptionsTemplate(annotations=())` | The same for edges | Set as `options` |
| `PropertySlot[T]` / `property(*, name=None, description=None, annotations=())` | Declare one scalar or flat-array graph property | `T` is the accepted authoring type |
| `endpoint(target)` | Name a concrete node for an abstract edge endpoint | A concrete `Node` class; returns `Endpoint[N]` |

```python
from kg_build_system import (
    AbstractNode, Edge, EdgeLabel, EdgeOptions, Node, NodeLabel, NodeOptions,
    PropertySlot, property,
)

class AssetNode(AbstractNode):
    options = NodeOptions(annotations=(NodeLabel("Asset"),))
    summary: PropertySlot[str] = property()

class SiteNode(AssetNode, Node):
    options = NodeOptions(annotations=(NodeLabel("Site"),))
    name: PropertySlot[str] = property()

class LinkedEdge(Edge[AssetNode, AssetNode]):
    options = EdgeOptions(annotations=(EdgeLabel("LINKED"),))
    since: PropertySlot[str | None] = property()
```

Base order is template, category parent, terminal base last. One direct
category parent, no concrete parent, matching-kind templates only. See
[Topology](../concepts/topology.md).

## Declare data contracts

A table is a typed row shape and a bindable source; a source struct is a nested
record; a computed struct is a value record whose members act as type witnesses
when it is carried by a row.

| Name | Purpose | Key arguments |
| --- | --- | --- |
| `Table` / `Struct` | Final bindable row shape / composable nested source record | Subclass; `options` and `Field[T]` members |
| `ComputedStruct` | Value-record declaration usable as `Field[T]`; its `computed_field` members are type witnesses when carried by a row, not evaluated values | Subclass; `computed_field` members and `StructOptions` |
| `TableGroup` | Named hierarchy of final tables and nested groups | Class attributes or `options.members` |
| `Field[T]` | Typed member descriptor | Annotation names the value type |
| `field(*, name=None, description=None, annotations=())` | Declare a source-backed member (table column or source struct member) | External `name` defaults to the attribute name |
| `computed_field(value, *, name=None, description=None, annotations=())` | Declare a projection output, or a computed struct member's type witness | A selection or expression |
| `TableOptions(...)` / `StructOptions(...)` / `ProjectionOptions(...)` | Identity, description and annotations | `name`, `description`, `annotations` |
| `TableGroupOptions(members=(), name=None, description=None, annotations=())` | Group members and metadata | `members` plus identity |
| `StructTemplate` / `StructOptionsTemplate(annotations=())` | Reusable field-and-annotation mixin for `Table`, `Struct` and `ComputedStruct` hosts | Annotations-only template options |

```python
from kg_build_system import Field, Struct, Table, TableGroup, TableOptions, field
from kg_build_system.types import Array

class ContactStruct(Struct):
    email: Field[str] = field()

class SiteTable(Table):
    options = TableOptions(name="sites")
    site_id: Field[str] = field()
    name: Field[str] = field()
    parent_site: Field[str] = field()
    contact: Field[ContactStruct] = field()
    tags: Field[Array[str]] = field()

class SiteGroup(TableGroup):
    sites = SiteTable
```

Every source field reads as a nullable selection, whatever its declaration says;
narrow with `alter_rows().drop_null()` or `default_to(...)`. A `ComputedStruct`
declares `computed_field` members and is never a table or row source; as
`Field[T]` its member expressions are type witnesses, and `extract` reads the
member from the carrier row. `Field[SomeTable]` and `Field[SomeProjection]` are
refused; a field type must be a value record. An explicit `description` wins over
the documentation string below the member, and `computed_field` reads that string
too. `StructTemplate` shares members with `Table`, `Struct` and `ComputedStruct`
but never becomes a row source. See
[Data contracts](../concepts/data-contracts.md).

## Read and transform rows

Field access produces a **selection**. A selection owns null policy and
structural navigation; `.expression` exposes the bindable calculation.

| Name | Purpose | Key arguments |
| --- | --- | --- |
| `ValueSelection[T]` | Present scalar selection | Produced by narrowing or by a non-null expression |
| `NullableSelection[T]` | Nullable selection; what every source field access returns | Adds `default_to`, `drop_null`, `extract`, `alter_rows` |
| `ArraySelection[T]` | Present array selection | Produced by narrowing a nullable array |
| `StructSelection[S]` | Present nested-record selection | Produced by narrowing or `expand` |
| `.extract(selector)` | Read one declared struct member | Callable receiving a symbolic struct instance |
| `.alter_rows()` | One-shot handle for the row effects available on this selection | No arguments |
| `.alter_rows().expand()` | Produce one row per array item | No arguments |
| `.alter_rows().drop_null()` | Drop rows whose value is null and return a present selection | No arguments |
| `.alter_rows().drop_if(predicate)` | Keep rows whose value satisfies the predicate | Callable receiving the selection and returning a `BoolExpression` |
| `.default_to(value)` | Replace null and keep the row | Non-null fallback |
| `.transform_items(selector)` | Apply one expression to every item, without expanding | Callable receiving the item expression |
| `.drop_null_items()` / `.sort()` / `.unique()` | Clean, order, deduplicate array items | No arguments; requires a present `ArraySelection` |
| `.concat(separator)` | Join non-null string items | `separator: str`; requires a present array |
| `.at(index)` | Select one array item, 0-based; nullable on out-of-bounds | `index: int` or integer expression |
| `.slice(start, end)` | Select a 0-based, end-exclusive array range | `start`, `end: int` or integer expressions |

`alter_rows()` exposes only the effects valid for that selection: `drop_if` on
every selection, `expand` on an array, and `drop_null` on a nullable selection.
Each method returns a selection, so a second effect needs another
`alter_rows()`. Array operations other than `expand` require the present
`ArraySelection` returned by `alter_rows().drop_null()`.

| Name | Purpose | Operations |
| --- | --- | --- |
| `ValueExpression[T]` | Base bindable calculation | `to_string()` on every canonical scalar |
| `IntExpression` / `FloatExpression` | Numeric calculation | `add(other)`, `sub(other)` |
| `StrExpression` | Text calculation | `prepend(value)`, `append(value)`, `equals(value)`, `replace(search, replacement)`, `before_separator(separator, occurrence=1, *, include_separator=False)`, `after_separator(...)` |
| `BoolExpression` | Row predicate or Boolean value | `not_()`, `and_(other)`, `or_(other)` |
| `ArrayExpression[T]` | Array calculation used through a selection | `transform_items`, `drop_null_items`, `sort`, `distinct`, `join(separator)` |
| `StructExpression[S]` / `NullableExpression[T, E]` / `CustomDataTypeExpression[C]` | Bindable struct, nullable, and custom scalar | Struct and custom expose no value-specific operations; null policy stays on the selection |
| `value_expression(value, *, logical_type=None)` | Build a typed literal expression | Value, optional logical type |
| `any_of(*predicates)` / `all_of(*predicates)` | Compose Boolean predicates | Empty identities are `False` / `True` |

```python
from kg_build_system import any_of

email = (
    SiteTable.contact.alter_rows().drop_null()
    .extract(lambda contact: contact.email)
    .alter_rows().drop_null()
)
label = email.expression.prepend("mailto:")

priority_sites = SiteTable.row_source().where(
    lambda site: any_of(
        site.name.alter_rows().drop_null().expression.equals("Depot"),
        site.tags.alter_rows().drop_null()
        .alter_rows().expand().expression.equals("priority"),
    )
)
```

Every source field reads as nullable, including scalars and arrays, so keys,
required properties, and array operations start from a narrowed selection.
`where(predicate)` exists on `RelationRowSource`, `DerivedRowSource`, `Table`,
and `Projection` and takes a callable receiving a symbolic shape instance that
returns a `BoolExpression`; a bare expression is refused. `to_string()` renders
canonical unit scalars for keys; arrays, structs and custom scalars are refused.
`default_to` keeps the row
while `alter_rows().drop_null()` removes it; `alter_rows().expand()` produces one
row per item and a null array produces none. See
[Expressions](../concepts/expressions.md).

## Derive a row product

| Name | Purpose | Key arguments |
| --- | --- | --- |
| `Projection` | Named logical row product with one driving plan | Subclass with at least one output; `Projection(source.row_source())` pins a relation, `Projection(derived)` pins a derived plan |
| `computed_field(value, *, name=None, description=None, annotations=())` | Declare one expression-backed output; reading it from the class yields a selection | A selection or expression |
| `Table.row_source()` / `Projection.row_source()` | Relation row source for a table or projection | No arguments |
| `.union(other, all=True)` | Concatenate two same-shape row sources | Another row source; `all=False` deduplicates |
| `.join(other, on=..., how="inner")` | Equality join producing `{on, left, right}` | Key pair or `equals`; `how` is `inner`, `left`, `right`, `full` |
| `.group_by(by=...)` | Group producing `{by, members}` | Key mapping, pair list, or one key input |
| `.distinct()` | Remove duplicate rows | No arguments |
| `.order_by(*keys, ascending=True)` | Order rows | Names, selections, expressions or callables |
| `.projection_base()` | Base carrying a source's plan and inherited outputs | On `Table`, `Projection`, `RelationRowSource`, `DerivedRowSource` |
| `.shape` | The shape class of a row source | On a table, projection, or row source |

`Table.row_source()` and `Projection.row_source()` return a `RelationRowSource`.
`where`, `union`, `join`, `group_by`, `distinct` and `order_by` each return a
`DerivedRowSource`, so the algebra composes; a projection relation accepts the
same operations. `join` accepts a key pair or one text `equals`, and keys share
a base type while their nullability may differ. `group_by` keys are non-null
and uniquely named.

```python
from kg_build_system import Projection, computed_field

class SiteProjection(Projection(SiteTable.row_source())):
    site_id = computed_field(SiteTable.site_id.alter_rows().drop_null())
    label = computed_field(
        SiteTable.name.alter_rows().drop_null().expression.prepend("site::")
    )
```

`Projection(SiteTable.row_source())` pins the projection to the relation and
records that source, with any filters, in its compiled definition. A joined,
grouped, unioned or filtered derived source is passed directly, as
`Projection(joined)`. The pin does not copy fields; declare the outputs with
`computed_field`. A projection is rejected at class creation if it is not pinned
or declares no output. Reading
`SiteProjection.site_id` elsewhere refers to the materialised output, not the
source expression. Use `.projection_base()` to publish a filtered source under a
name and inherit its outputs. A further expansion needs another projection (see
[Projections](../concepts/projections.md)).

## Bind rows to graph records

A binding connects one row source to one concrete component. Every declared
property is bound exactly once; keys are non-null scalar expressions.

| Name | Purpose | Key arguments |
| --- | --- | --- |
| `node_binding(*, target, build_key=None, properties=None, rows=None, bind=None, debug_name=None, options=BindingOptions())` | Bind rows to one concrete node | `target`; either `build_key` + `properties` or `rows` + `bind` |
| `edge_binding(*, target, build_key=None, source_build_key=None, target_build_key=None, properties=None, rows=None, bind=None, debug_name=None, options=BindingOptions(), source_node=None, target_node=None)` | Bind rows to one concrete edge | Three keys and properties, or `rows` + `bind`; endpoint tokens for abstract sides |
| `NodeValues(build_key, properties)` / `EdgeValues(build_key, source_build_key, target_build_key, properties)` | Row-derived values returned by a `bind` callable | Keys and a component instance |
| `BindingOptions(annotations=())` | Annotations carried by a binding | `annotations` |
| `NodeBinding[N]` / `EdgeBinding[E]` | Frozen values returned by the factories | Compose with `compile` |

```python
from kg_build_system import NodeValues, edge_binding, endpoint, node_binding

site_binding = node_binding(
    target=SiteNode,
    rows=SiteTable.row_source(),
    bind=lambda site: NodeValues(
        build_key=site.site_id.alter_rows().drop_null(),
        properties=SiteNode(
            name=site.name.default_to("Unnamed site"),
            summary=site.name.default_to("No summary"),
        ),
    ),
)

link_binding = edge_binding(
    target=LinkedEdge,
    build_key=SiteTable.site_id.alter_rows().drop_null(),
    source_build_key=SiteTable.site_id.alter_rows().drop_null(),
    target_build_key=SiteTable.parent_site.alter_rows().drop_null(),
    properties=LinkedEdge(since=SiteTable.parent_site),
    source_node=endpoint(SiteNode),
    target_node=endpoint(SiteNode),
)
```

A concrete side needs no token; an abstract side needs exactly one.
`rows` accepts a row-source value such as `SiteTable.row_source()`, a
`DerivedRowSource` from `.where(...)`, or a joined/grouped source; a declaration
class is rejected. The callable receives a symbolic shape instance, so
row-derived values live inside `bind`. A non-null value may satisfy a nullable property, never the reverse.
Since every source field reads as nullable, keys narrow and required properties
default or narrow. See [Bindings](../concepts/bindings.md).

## Point declarations at data

| Name | Purpose | Key arguments |
| --- | --- | --- |
| `bind_source(*, target, config, options=SourceBindingOptions())` | Attach a physical configuration to a table or group; carry source annotations | `target`, `config`, `options` |
| `DataSourceConfig(location, format=InputFormat.CSV, layout=None, credentials=None, version=None)` | Physical location and options; `InputFormat` is `CSV`, `JSON`, or `PARQUET` | `location` first; format and layout |
| `BoundTable` / `BoundTableGroup` / `BoundSource` | Values returned by `bind_source`, and their alias | Compose with `compile` |

```python
from kg_build_system import DataSourceConfig, InputFormat, bind_source

sites = bind_source(
    target=SiteTable,
    config=DataSourceConfig(
        "data/sites.json", format=InputFormat.JSON, version="2026-08",
    ),
)
```

A group target adds `layout="{group_path}/{table_name}.json"`; the layout may
use only those two fields. Definitions carry credential references, never
resolved secrets. See [Sources](../concepts/sources.md).

## Annotate declarations

| Name | Purpose | Key arguments |
| --- | --- | --- |
| `Annotation` | Base for portable, frozen metadata values | Declare `namespace`, `annotation_id`, and dataclass fields |
| `NodeLabel(label)` / `EdgeLabel(label)` | The single semantic label of a component | Non-empty string |

```python
from dataclasses import dataclass

from kg_build_system import Annotation, NodeLabel, NodeOptions

@dataclass(frozen=True)
class SourceSystem(Annotation):
    namespace = "example"
    annotation_id = "source_system"
    system: str

site_options = NodeOptions(annotations=(NodeLabel("Site"), SourceSystem("estate-register")))
```

Annotations attach through `field(annotations=...)`,
`property(annotations=...)`, `computed_field(annotations=...)`, declaration
options, `BindingOptions`, and `SourceBindingOptions`. A component carries at
most one node label or one edge label. See [Annotations and
descriptions](../concepts/annotations.md).

## Register modules

Modules are registered from `kg_build_system.modules`. Registration order is
composition order; the mandatory core module is appended after your modules.

| Name | Purpose | Key arguments |
| --- | --- | --- |
| `register_module(module_class, configuration=None)` / `ModuleRegistration` / `Module` | Register one module; the frozen registration value; the module protocol | Configuration is required only when the module defines no default |
| `ModuleRegistrationConfiguration` | Base for serialisable, non-secret module configuration | Subclass with dataclass fields |
| `CollapseExactDuplicatesModule` / `MergeCompatibleFactsModule` / `RejectConflictingNonNullValuesModule` | Deduplicate records; merge same-key facts; report conflicting non-null values | `MergeCompatibleFactsModuleConfiguration(components=None)`; `RejectConflictingNonNullValuesConfiguration(fail_on_error=True)` |
| `FileModule` / `MetaGraphModule` | Write JSON Lines records; write the topology document and HTML page | `FileModuleConfiguration(relative_path)`; `MetaGraphModuleConfiguration(relative_path="meta_graph.json", example_limit=3, include_html=True, html_relative_path="meta_graph.html")` |
| `Neo4jModule` | Write a Neo4j import Parquet bundle | `Neo4jModuleConfiguration(relative_directory="neo4j-import", script_name="import_neo4j.py", default_database="neo4j")` |

```python
from kg_build_system.modules import (
    CollapseExactDuplicatesModule, FileModule, FileModuleConfiguration,
    register_module,
)

modules = (
    register_module(CollapseExactDuplicatesModule),
    register_module(FileModule, FileModuleConfiguration("graph.jsonl")),
)
```

Registration and composition are public; authoring a new `Module` is
framework-internal in this release because its compiler and executor protocols
are not exported. See [Modules](../concepts/modules.md).

## Compile and build

| Name | Purpose | Key arguments |
| --- | --- | --- |
| `create_blueprint(*, modules, namespace_path=None, bindings=None, sources=None)` | Validate reached declarations into an inspectable blueprint; requires at least one component and binding | A namespace, or explicit `bindings` + `sources` |
| `compile(*, modules, namespace_path=None, bindings=None, sources=None, blueprint=None)` | Freeze the blueprint into an executable contract | Same modes, plus a prebuilt `blueprint` |
| `build(contract, runtime=None, *, output_directory=Path("build"), working_directory=Path("_workdir"), temporary_directory=None, monitor=None)` | Execute a contract and write its outputs | Contract and runtime controls; `monitor` also accepts a custom `WorkflowExecutionMonitor` |
| `BuildRuntime(credentials={}, module_configuration={}, output_directory=Path.cwd() / "build", working_directory=Path("_workdir"), temporary_directory=None, duckdb_storage="memory", duckdb_threads=None, duckdb_memory_limit=None, duckdb_compression=True)` | Credentials, module settings, directories, DuckDB controls | Every field is optional; relative working directories resolve beneath the output directory |
| `WorkflowReport` | Result of a completed build | `published_artifacts`, `recovered_failures`, `unresolved_failures`, `provenance`, `succeeded` |

```python
from pathlib import Path

from kg_build_system import build, compile

contract = compile(
    bindings=(site_binding, link_binding),
    sources=(sites,),
    modules=modules,
)

report = build(contract, output_directory=Path("build"))
```

With only `modules`, `compile` and `create_blueprint` discover bindings and
sources in the calling file's namespace. `bindings` and `sources` must be
supplied together; `blueprint` cannot be combined with another mode. Published
artifacts, `workflow_contract.json`, and `build_report.json` land in the output
directory. See [Compile and build](../concepts/build.md) and [Outputs](../concepts/outputs.md).
