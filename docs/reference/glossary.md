# Glossary

The terms below are the ones an author meets while declaring a build. Each
entry says what the thing is and where it lives in the authoring surface.

```
Table / Projection ──> selection / expression ──> binding ──> contract ──> build ──> target
   (row source)            (row values)          (meaning)   (frozen)     (execute)  (output)
```

## Declarations

**Annotation**
: A frozen, portable metadata value with a stable `namespace` and
  `annotation_id`. It attaches to a declaration, field, property, projection,
  binding, or source, and the build preserves it without interpreting it.
  `NodeLabel` and `EdgeLabel` are annotations. See [Annotations and
  descriptions](../concepts/annotations.md).

**Binding**
: The declaration that turns rows into graph records for one concrete
  component. A node binding supplies a build key and every declared property;
  an edge binding also supplies source and target keys. A binding owns its
  complete row context, so its filters and expansions never affect another
  binding. See [Bindings](../concepts/bindings.md).

**Category**
: An abstract node or edge declaration. It is a graph-visible parent recorded
  in the topology, it may hold shared properties, and it may be named as an
  edge endpoint. A category is never a binding target; a binding names a
  concrete descendant through `endpoint(...)`. See
  [Topology](../concepts/topology.md).

**Computed field**
: An expression-backed member declared with `computed_field(expression)`. It
  appears as a `Projection` output or a `ComputedStruct` member and is typed by
  its expression: non-null when the expression is non-null, nullable when the
  expression is nullable.

**Computed struct**
: A value-record declaration built from `computed_field` members. It is usable
  as a field type (`Field[SomeComputedStruct]`) and through `extract`, but it is
  not a table or row source and cannot be bound. See
  [Projections](../concepts/projections.md#computed-structs).

**Contract**
: The immutable result of `compile()`: the complete, portable description of
  one build, including the workflow fingerprint. The same contract can be
  stored, inspected, and built repeatedly. See [Compile and
  build](../concepts/build.md).

**Edge**
: A graph relationship component. It declares a source node side, a target
  node side, and its properties. A concrete `Edge[S, D]` is bindable; an
  `AbstractEdge[S, D]` is a category.

**Endpoint**
: One side of an edge declaration, named by a node category or a concrete
  node. When the declared side is abstract, the binding supplies
  `source_node=endpoint(...)` or `target_node=endpoint(...)` to say which
  concrete node actually participates. See [Bindings](../concepts/bindings.md).

**Expression**
: A typed calculation over row values. It carries a logical type and only the
  operations valid for that type; it performs no structural navigation and
  owns no null policy. A selection exposes its calculation as `.expression`,
  and bindings accept expressions directly. See
  [Expressions](../concepts/expressions.md).

**Field**
: The typed member of a record, written `Field[T]`. `field()` declares a
  source-backed field: a table column or a source struct member. A field
  declaration names the value type, never a presence guarantee; every source
  field access returns `NullableSelection[T]`. See [Data
  contracts](../concepts/data-contracts.md).

**Key**
: The build key: the non-null scalar expression that identifies one node or
  edge record. An edge binding also has source and target node keys. Every
  source field reads as nullable, so a key starts from
  `alter_rows().drop_null()` (or a deliberate `default_to`); an array of
  strings becomes key text through `concat()` after narrowing, `sort()`, and
  `unique()`.

**Module**
: A composable build stage registered with `register_module(...)`. Supplied
  modules deduplicate, merge, validate, or write output. The core module is
  always appended. See [Modules](../concepts/modules.md).

**Node**
: A graph entity component with properties. A concrete `Node` is bindable and
  terminal; an `AbstractNode` is a category.

**Nullability**
: Whether a selection may hold an absent value. Source field access is always
  nullable; `default_to(...)` replaces an absence and `alter_rows().drop_null()`
  removes the row. A computed field follows its expression. See [Types and
  nullability](../concepts/types.md).

**Projection**
: A named logical row product with exactly one driving row plan. Its outputs
  are declared with `computed_field(...)`. A projection is also a row source, so
  a binding or another projection can consume it; `Projection(source.row_source())`
  pins it to a relation and records that source in its definition. See
  [Projections](../concepts/projections.md).

**Property**
: A named value on a node or edge, declared as `PropertySlot[T]` and built with
  `property()`. It is a scalar or a flat array of non-null scalars. Every
  declared property, including an inherited one, must be bound exactly once.
  See [Topology](../concepts/topology.md).

**Row effect**
: An operation that changes which rows survive or how many there are:
  `expand`, `drop_null`, `drop_if`, and the row-source `where` filter. A
  selection's row effects are reached through the one-shot `alter_rows()`
  handle; `default_to` and array calculations preserve the row.

**Row source**
: Something that produces rows of a known shape. `Table.row_source()` and
  `Projection.row_source()` return a `RelationRowSource`; `.where(...)` returns
  a `DerivedRowSource`. A row source is a value; a declaration class is not
  accepted. A `Struct` or `ComputedStruct` is not a row source.

**Selection**
: A typed, structural view of a field or value in a row. A source field gives a
  `NullableSelection`; narrowing gives a `ValueSelection`, `ArraySelection`, or
  `StructSelection`. A selection owns `extract`, `alter_rows` (for `expand`,
  `drop_null`, and `drop_if`), `default_to`, and the array operations on a
  present array; `.expression` reaches the calculation.

**Shape**
: A class-level row shape: a class whose fields are typed. `Shape` is the base
  of `Struct`, `Table`, and `Projection`. A shape is a class, never a schema
  instance or a dictionary.

**Struct**
: A nested-record shape. It is only a shape — never a row source — and is used
  inside a `Field[SomeStruct]`. Every source member is nullable at every source
  step. Its identity is its `(module, qualname)` pair. See [Data
  contracts](../concepts/data-contracts.md).

**Table**
: A final logical data declaration. It is both a shape and a row source based
  on a physical input, and it is bound to that input with `bind_source(...)`.
  A `TableGroup` gives tables a named nested catalog structure.

**Table group**
: A named hierarchy of final tables and nested table groups. Every member has a
  canonical catalog path, and a group source uses one layout to resolve each
  member's physical location.

**Template**
: An inert mixin that shares property slots or fields and annotation flow with
  its hosts. `NodeTemplate`, `EdgeTemplate`, and `StructTemplate` never enter
  the contract and carry no identity. Their options are annotations-only:
  `NodeOptionsTemplate`, `EdgeOptionsTemplate`, `StructOptionsTemplate`.

**Topology**
: The graph-meaning declarations — nodes, edges, properties, categories, and
  their hierarchy — independent of any input file or output target. See
  [Topology](../concepts/topology.md).

## Process and output

**Build**
: The act of executing a compiled contract with a `BuildRuntime`. It writes
  published artifacts, `workflow_contract.json`, and `build_report.json`, and
  returns a `WorkflowReport`. See [Compile and build](../concepts/build.md).

**Target**
: Two related senses. A *target module* is an output backend such as the file,
  meta-graph, or Neo4j module. A *binding target* is the concrete component
  named by `target=...` in a binding. The context makes the sense clear; when
  it does not, say "output target" or "binding target".

## Terms that look alike

| Term | Not the same as | Difference |
| --- | --- | --- |
| Field | Property | A field describes a source member or computed output; a property is a graph value bound from an expression. |
| Selection | Expression | A selection navigates structure and owns null policy; an expression calculates a value. |
| Struct | ComputedStruct / Table | A source struct is source-backed; a computed struct is expression-backed; a table is also a bindable row source. |
| Template | Category | A template is inert and never enters the contract; a category is graph-visible and may be an endpoint. |
| Row source | Shape | A shape is a class of fields; a row source is something that yields rows of that shape. |
| Contract | Blueprint | A contract is executable; a blueprint is the validated declaration snapshot used to create one. |
| Binding target | Output target | The binding target is a component; the output target is a module that writes results. |

## Authoring names

Use these names in author code. A source member is declared with `field()` and a
computed output with `computed_field(...)`. A struct member is reached with
`extract`. A null is resolved with `default_to(...)` or `alter_rows().drop_null()`.
Row effects are opt-in through `alter_rows()`. On a present array, use
`drop_null_items()`, `sort()`, `unique()`, `concat()`, `at()`, `slice()`, and
`transform_items()`.

## Where to go next

- [Public API](api.md) — names, arguments, and examples.
- [Type vocabulary](types.md) — canonical types and their restrictions.
- [Data contracts](../concepts/data-contracts.md) and
  [Bindings](../concepts/bindings.md) — the two halves of a build.
- [Your first graph](../start/first-graph.md) — the terms used end to end.
