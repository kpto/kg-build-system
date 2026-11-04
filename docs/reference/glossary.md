# Glossary

This glossary defines the vocabulary used across the authoring guide and links each term to the page that develops it.

The diagram shows the main path through an authoring project. Each entry below
names the concept page or reference page that owns the detail.

```text
asset contract ──kbs generate──> Table[Asset] / Struct / TableGroup
                                           │
Asset + AssetLayout ───────────────────────┘
                                           │
field access ──selection──> projection ──binding──> WorkflowPlan ──execute──> target
```

## Data declarations

**Annotation**
: A frozen, portable metadata value with a stable `namespace` and
  `annotation_id`. It attaches to a declaration, field, property, projection,
  binding or source, and the build preserves it without interpreting it.
  `NodeLabel` and `EdgeLabel` are annotations. See [Semantics and
  annotations](../concepts/semantics.md).

**Computed field**
: A member declared with `computed_field(expression)`. As a `Projection` output
  it is typed by its expression: non-null when the expression is non-null,
  nullable when it is nullable. As a `ComputedStruct` member it is a type
  witness only, and the value is read from the carrier row. See
  [Projections](../concepts/projections.md).

**Computed struct**
: A value-record declaration built from `computed_field` members. It is usable
  as a field type (`Field[SomeComputedStruct]`) and through `extract`, but it is
  not a table or row source and cannot be bound. Its member expressions are type
  witnesses: they fix member types, are not evaluated, and `extract` reads the
  member from the carrier row. See [Types](types.md#structs-and-computed-structs).

**Field**
: The typed member of a record, written `Field[T]`. `field()` declares a
  source-backed field: a table column or a source struct member. A field
  declaration names the value type and its presence: `Field[T]` reads a present
  selection and `Field[T | None]` reads a nullable one. See [Data
  contracts](../concepts/data-contracts.md).

**Generated package**
: An owned directory of ordinary `Table`, `Struct` and `TableGroup` declarations
  produced beside an author-owned request. It is generated and must not be
  edited; change the request and regenerate. See
  [Generation](generation.md#ownership).

**Struct**
: A nested-record shape. It is only a shape, never a row source, and is used
  inside a `Field[SomeStruct]`. A source member reads its own declaration; a
  nullable carrier makes its members nullable. Its identity is its
  `(module, qualname)` pair. See [Data
  contracts](../concepts/data-contracts.md#nested-records).

**Table**
: A final logical data declaration. It is both a shape and a row source, and it
  names the asset its rows come from with `Table[Asset]`. See [Data
  contracts](../concepts/data-contracts.md).

**Table group**
: A named hierarchy of final tables and nested table groups. Every member has a
  canonical catalog path and names its own asset. A group is a catalog, not a
  shape, a row source or a source declaration. See
  [Assets and ingest](ingest.md#table-groups).

**Template**
: An inert mixin that shares property slots or fields and annotation flow with
  its hosts. `StructTemplate` mixes only into `Table`, `Struct` and
  `ComputedStruct`. `NodeTemplate`, `EdgeTemplate` and `StructTemplate` never
  enter the workflow plan and carry no identity. See
  [Semantics and annotations](../concepts/semantics.md).

## Types and values

**Array**
: The portable ordered-collection marker `Array[T]`. It is not `list[T]`,
  `Sequence[T]` or a storage type. Array presence is declared: `Field[Array[T]]`
  is present and `Field[Array[T] | None]` is nullable. Item nullability stays in
  the declaration as `Array[T | None]`. See [Types](types.md#arrays).

**Canonical type**
: The normalized logical type of a value: one of the eight lowercase scalars,
  a custom scalar, a struct identity, an `Array`, or a nullable wrapper. The
  canonical name is what the workflow plan and every error message use. See
  [Types](types.md#canonical-scalars).

**Custom scalar**
: An application-defined scalar declared as a top-level `CustomDataType`
  subclass. Identity is `(module, qualname)`. It composes as a field, array item,
  key or property type but exposes no value operations, and a target may refuse
  it. See [Types](types.md#custom-scalars).

**Digest gate**
: The generation boundary that maps a physical DuckDB type to a canonical type
  with one of three dispositions: `canonical`, `declared_only` or `refused`. See
  [Assets and ingest](ingest.md#digest-gate) and [the full
  mapping](types.md#duckdb-dispositions).

**Graph property**
: A value on a node or edge, declared as `PropertySlot[T]` and built with
  `property()`. It is a scalar or a flat array of non-null scalars. Every
  declared property, including an inherited one, must be bound exactly once. See
  [Types](types.md#graph-property-shape).

**Guard**
: The build-time check on every non-null binding output: `build_key`, source and
  target keys, and every non-null property. It aborts on the first null where
  that output is read. A nullable output is not guarded. See [Assets and
  ingest](ingest.md#guards).

**Key**
: The build key: the non-null scalar expression that identifies one node or edge
  record. An edge binding also has source and target node keys. A source field
  declared `Field[T | None]` must be narrowed for a key; `Field[T]` is already
  present. See [Types](types.md#keys).

**Nullability**
: Whether a selection may hold an absent value. Source field access follows the
  declaration: `Field[T]` is present and `Field[T | None]` is nullable.
  `default_to(...)` replaces an absence and `alter_rows().drop_null()` removes
  the row; both are no-ops on a present value. A computed field follows its
  expression; a computed-struct member follows its witness. See
  [Types](types.md#nullability).

**Pre-flight**
: The Parquet footer statistics check behind a declared non-null claim. At
  generation it reports violations and continues; at build it marks the source
  step `WARNING` and logs the count. It never enforces the claim. See [Assets
  and ingest](ingest.md#statistics-pre-flight).

**Representative type**
: The capitalised spelling an author writes for a text-canonical scalar:
  `Date`, `Time`, `Timestamp` or `Uuid`. Each is an alias of the stdlib class the
  engine returns, not a subclass. See [Types](types.md#representative-types).

**Trust tier**
: The nullability authority of a source: `ENFORCED` for an enforced catalog
  constraint, `DECLARED` for a Parquet footer, or `DEFAULTED` for a schema-less
  CSV or JSON source. See [Assets and ingest](ingest.md#trust-tiers).

**Widening**
: The build's cast of each declared top-level source column to the canonical SQL
  type of its logical type. Ingest widens and never narrows by itself; a
  declared-only narrowing requires an override and is checked. See [Assets and
  ingest](ingest.md#widening).

## Assets

**Asset**
: One logical unit of source data, like a package. One asset may back many
  tables. It declares semantics, optional layout, governance and annotations,
  and a table names it with `Table[Asset]`. See
  [Assets](../concepts/assets.md).

**`AssetOptions`**
: The options on an asset: `semantics`, `name`, `website`, `version`, `layout`,
  `governance` and `annotations`. It has no content model, adapter or
  code-generation field. See [Assets](assets.md).

**`AssetSemantics`**
: What an asset represents and the limits of that representation: `subject`,
  `coverage`, `authority`, `basis`, `claims`, `limitations` and optional
  title/description. See [Assets](assets.md#assetsemantics).

**`AssetAuthority`**
: How an asset relates to its claims: `PRIMARY`, `DERIVED`, `REFERENCE` or
  `INFERRED`. See [Assets](assets.md#assetauthority).

**`AssetGovernance`**
: The `license`, `owner` and string `metadata` of an asset. See
  [Assets](assets.md#assetgovernance).

**`AssetLicense`**
: The license an asset is distributed under: `identifier`, optional `url` and
  optional `attribution`. See [Assets](assets.md#assetlicense).

**`AssetLayout`**
: Optional descriptive layout metadata: `kind`, `locator`, `format`, `selector`,
  `partition_by`, `members` and `properties`. It is not an access contract and
  is not a Hive, catalog, schema or partition-style model. See
  [Assets](assets.md#assetlayout).

**Asset contract**
: The inert `@asset_contract(AssetContractOptions(...))` class decorator on an
  asset. It states how the asset's table declarations are generated; it is not
  part of `AssetOptions` or the blueprint. See
  [Generation](generation.md#request-model).

**Generic source planner**
: `DuckDbSourcePlanner`, a module planner that resolves `parquet`, `json` and
  `csv` asset layouts into `source.<relation>` steps. It is not an adapter and
  there is no adapter registry. See
  [Assets and ingest](ingest.md#the-generic-source-planner).

## Rows and graph meaning

**Binding**
: The declaration that turns rows into graph records for one concrete
  component. A node binding supplies a build key and every declared property;
  an edge binding also supplies source and target keys. See
  [Bindings](../concepts/bindings.md).

**Category**
: An abstract node or edge declaration. It is a graph-visible parent recorded
  in the topology, it may hold shared properties, and it may be named as an edge
  endpoint. A category is never a binding target; a binding names a concrete
  descendant through `endpoint(...)`. See [Topology](../concepts/topology.md).

**Edge**
: A graph relationship component. It declares a source node side, a target node
  side and its properties. A concrete `Edge[S, D]` is bindable; an
  `AbstractEdge[S, D]` is a category. See [Topology](../concepts/topology.md).

**Endpoint**
: One side of an edge declaration, named by a node category or a concrete node.
  When the declared side is abstract, the binding supplies
  `source_node=endpoint(...)` or `target_node=endpoint(...)` to say which
  concrete node participates. See [Bindings](../concepts/bindings.md).

**Expression**
: A typed calculation over row values. It carries a logical type and only the
  operations valid for that type; it performs no structural navigation and owns
  no null policy. A selection exposes its calculation as `.expression`. See
  [Expressions](../concepts/expressions.md).

**Node**
: A graph entity component with properties. A concrete `Node` is bindable and
  terminal; an `AbstractNode` is a category. See
  [Topology](../concepts/topology.md).

**Projection**
: A named logical row product with exactly one driving row plan. Its outputs are
  declared with `computed_field(...)`. A projection is also a row source, so a
  binding or another projection can consume it. See
  [Projections](../concepts/projections.md).

**Property**
: A named graph value on a node or edge, declared as `PropertySlot[T]` and built
  with `property()`. It is a scalar or a flat array of non-null scalars. See
  [Types](types.md#graph-property-shape).

**Row effect**
: An operation that changes which rows survive or how many there are: `expand`,
  `drop_null`, `drop_if` and the row-source `where` filter. A selection's row
  effects are reached through the one-shot `alter_rows()` handle. See
  [Expressions](../concepts/expressions.md).

**Row source**
: Something that produces rows of a known shape. `Table.row_source()` and
  `Projection.row_source()` return a `RelationRowSource`; `where`, `union`,
  `join`, `group_by`, `distinct` and `order_by` return a `DerivedRowSource`. A
  row source is a value; the algebra requires it. A binding accepts a `Table` or
  `Projection` class as a compatibility shorthand. See [Row sources
  and grain](../concepts/row-sources.md).

**Selection**
: A typed, structural view of a field or value in a row. A source field gives the
  selection its declaration names: present for `Field[T]`, nullable for
  `Field[T | None]`. Narrowing gives a `ValueSelection`, `ArraySelection` or
  `StructSelection`. A selection owns `extract`, `alter_rows`, `default_to` and
  the present-array operations; `.expression` reaches the calculation. See
  [Expressions](../concepts/expressions.md).

**Semantics**
: The descriptions, labels and annotations that state what a component means and
  travel with it into the workflow plan and its outputs. See [Semantics and
  annotations](../concepts/semantics.md).

**Shape**
: A class-level row shape: a class whose fields are typed. `Shape` is the base of
  `Struct`, `Table` and `Projection`. A shape is a class, never a schema
  instance or a dictionary. See [Data contracts](../concepts/data-contracts.md).

**Topology**
: The graph-meaning declarations: nodes, edges, properties, categories and their
  hierarchy, independent of any input file or output target. See
  [Topology](../concepts/topology.md).

## Compile, execute and outputs

**Blueprint**
: The immutable, validated semantic model produced by `create_blueprint`. It
  contains the graph topology, data declarations, assets and bindings that a
  reached binding needs, named by typed references rather than a symbol table.
  See [Compile, build and outputs](../concepts/build-and-outputs.md).

**Build**
: The act of linking declarations into a model with `build`, compiling that
  model with `compile`, and running the plan with `execute`. `execute` writes
  published artifacts, `workflow_plan.json` and `build_report.json`, and returns
  a `WorkflowReport`. See [Compile, execute and
  outputs](../concepts/build-and-outputs.md).

**Compile**
: The call `compile()` that reads a blueprint and produces a `WorkflowPlan`. It
  reads declarations but no data. See [Compile, build and
  outputs](../concepts/build-and-outputs.md).

**Workflow plan**
: The immutable result of `compile()`: the components, steps, connections and
  provenance of one planner composition. The same plan can be stored, inspected
  and executed repeatedly where an executor exists for every instruction kind;
  there is no schema migration path. See [Compile, build and
  outputs](../concepts/build-and-outputs.md).

**Step identity**
: `StepId(component, name)`, a two-segment role type over `Key`. `Step` keeps
  `component` and `name` and derives `.id`; a formatted string is display only.
  See [Compile, build and outputs](../reference/compile.md).

**Opening**
: `OpeningId(step, direction, name)`, the typed identity of one input or output
  port. Direction is part of the key, so an input and an output with the same
  name are distinct. See [Compile, build and outputs](../reference/compile.md).

**Artifact type**
: A concrete `ArtifactType` over a `Key`. An input declares an `ArtifactPattern`;
  `*` matches one segment and a final `**` matches the rest. See
  [Planners and executors](../reference/planners-and-executors.md).

**Instruction kind**
: `InstructionKind(operation, engine)`, the exact two-segment key an executor
  owns. There is no prefix matching. See
  [Planners and executors](../reference/planners-and-executors.md).

**Planner**
: A component that reads the linked model and emits `Step`s. Supplied planners
  deduplicate, merge, validate or produce graph records. The core module
  contributes four planners that share one component; the generic
  `DuckDbSourcePlanner` is a separate planner with `component_id="duckdb"`. See
  [Planners and executors](../concepts/planners-and-executors.md).

**Executor**
: A component that owns one exact instruction kind, declares the resources it
  reads and executes its steps. The DuckDB, Python, file, meta-graph and Neo4j
  executors are supplied. See [Planners and
  executors](../concepts/planners-and-executors.md).

**Resource**
: A live capability with a lifecycle, such as a DuckDB service or output storage.
  A `ResourceProvider` publishes it on `PipelineStarted` and disposes it on
  `PipelineFinished` or `PipelineHalted`; an executor receives only the resource
  types it declares in a `ResourceView`. See [Planners and
  executors](../concepts/planners-and-executors.md).

**Pipeline event**
: One `PipelineStarted`, `StepStarted`, `StepFinished`, `StepLogged`,
  `PipelineFinished` or `PipelineHalted` value emitted by a run. An `EventBus`
  delivers each event to the run's providers and frontend listeners; a monitor
  is a frontend listener.

**Output**
: A value published by an output planner's executor during a build, such as
  `graph.jsonl`, `meta_graph.json` or the Neo4j import directory. The report
  lists each published artifact and any failure. See [Compile, build and
  outputs](../concepts/build-and-outputs.md).

**Target**
: Two related senses. A *target planner* is an output backend such as the file,
  meta-graph or Neo4j planner and its executor. A *binding target* is the
  concrete component named by `target=...` in a binding. See
  [Planners and executors](../concepts/planners-and-executors.md).

## Generation

**Check**
: `kbs generate --check`, the no-write comparison of products with their
  requests and ownership records. It reports `CURRENT` or `STALE` and does not
  observe sources. See [Generation](generation.md#check).

**Generation result**
: The value returned by `generate(...)`: a `GenerationStatus` plus changed,
  created, updated and deleted paths, diagnostics and actions. See
  [Generation](generation.md#python-surface).

**Ownership record**
: The `.kbs-generation.json` file in a generated product. It records the request
  fingerprint, provider identity and version, optional source digest, owned files
  and directories, and file hashes. It proves what the generator owns. See
  [Generation](generation.md#ownership).

**Provider**
: A typed implementation of `Provider[T]` with `ID`, `VERSION`, `CONFIG_TYPE`
  and an async `generate(context)` that returns a `GeneratedPackage`. See
  [Generation](generation.md#provider-contract).

**Regenerate**
: `kbs generate --regenerate`, which forces every provider to observe its source
  again. With `--check` it reports source-schema drift without writing. See
  [Generation](generation.md#regenerate).

**Watch**
: `kbs generate --watch`, which runs one pass and then watches project files for
  declaration changes. Generated products and data sources do not trigger it.
  See [Generation](generation.md#watch).

## Terms that look alike

| Term | Not the same as | Difference |
| --- | --- | --- |
| Field | Property | A field describes a source member or computed output; a property is a graph value bound from an expression. |
| Selection | Expression | A selection navigates structure and owns null policy; an expression calculates a value. |
| Struct | ComputedStruct / Table | A source struct is source-backed and each member reads its declaration; a computed struct supplies member types as witnesses and reads from its carrier; a table is also a bindable row source. |
| Template | Category | A template is inert and never enters the workflow plan; a category is graph-visible and may be an endpoint. |
| Row source | Shape | A shape is a class of fields; a row source is something that yields rows of that shape. |
| Workflow plan | Blueprint | A workflow plan is executable; a blueprint is the validated semantic model used to create one. |
| Binding target | Output target | The binding target is a component; the output target is a planner/executor pair that writes results. |
| Asset | Data contract | An asset says what the source data is and how it is laid out; a data contract says what one row is. |
| Canonical type | Representative type | A canonical type is the lowercase logical type used by the workflow plan; a representative type is the Python alias an author may write. |
| Guard | Pre-flight | A guard aborts at the point a non-null value is read; a pre-flight only reports null counts from Parquet footers. |
| Check | Regenerate | Check compares generated files with their requests; regenerate re-observes the source schema. |
| Asset contract | Generated package | The contract is author-owned and inert; the package is generator-owned output. |

## Authoring names

Use these names in author code. A source member is declared with `field()` and a
computed output with `computed_field(...)`. A struct member is reached with
`extract`. A null is resolved with `default_to(...)` or
`alter_rows().drop_null()`. Row effects are opt-in through `alter_rows()`. On a
present array, use `drop_null_items()`, `sort()`, `unique()`, `concat()`, `at()`,
`slice()` and `transform_items()`.

Generation uses `@asset_contract(AssetContractOptions(...))` on an
author-owned asset and the `kbs generate` command. An asset names its own
`AssetLayout`. Graph records use
`node_binding(...)` and `edge_binding(...)`. A build uses `compile()` and
`execute()`.

## Where to go next

- [Authoring API](index.md) — the surface you write.
- [Types](types.md) — canonical types, nullability and DuckDB dispositions.
- [Assets and ingest](ingest.md) — asset layouts, source steps, trust tiers and guards.
- [Generation](generation.md) — requests, providers and generated packages.
- [Data contracts](../concepts/data-contracts.md) and
  [Bindings](../concepts/bindings.md) — the two halves of a build.
- [Compile, execute and outputs](../concepts/build-and-outputs.md) — the workflow
  plan, execution and artifacts.
- [Install](../get-started/install.md) — the generation workflow end to end.
