# Data and expressions

This page states where row data, expressions and projections live, how they
cross the blueprint and planning boundaries, and what source regeneration must
prove.

## Ownership

| Concept | Owner | What it is |
| --- | --- | --- |
| Canonical types | `kernel/model/public/types` | the one type ontology every language uses |
| Annotations | `distribution/languages/annotations` | annotation values and DTOs |
| Assets | `distribution/languages/asset` | logical source-data declarations, layout metadata and asset DTOs |
| Selections | `distribution/languages/expressions/model/public` | typed reads over a row shape |
| Operation specifications | `distribution/languages/expressions/service/internal/operations` | one specification per operation |
| Row sources | `distribution/languages/data` | the row value a projection or binding reads |
| Joins, unions, filters, groups, distinct, order | `distribution/languages/data` | row-source operations and their plan DTOs |
| Projections | `distribution/languages/data` | a named relation with output expressions and a row source |
| Data DTO | `distribution/languages/data/model/internal/dto/blueprint_dto.py` | the frozen data part of the blueprint |
| Blueprint | `distribution/interpreter` | assembles the language DTOs into `GraphBlueprint` |
| Relational plan | `distribution/modules/core/service/_private/planning` | engine-neutral relation plans and step planning |
| Instruction emission | `distribution/modules/core` and `distribution/modules/duckdb` | turns a plan into a `("sql", "duckdb")` instruction |
| SQL emitter | `distribution/modules/duckdb/service/_private/emitters` | emits DuckDB SQL for an instruction |
| Engine boundary | `distribution/modules/duckdb` | opens and runs the engine through `DuckDbResourceProvider` |

`data` is the graph language that owns row sources, projections and their
DTOs. `expressions` contributes operations and expression DTOs; it is not a
graph language and does not own a build part.

## Data, expression, blueprint and planning

The four boundaries have different jobs:

| Boundary | Input | Output | Must not know |
| --- | --- | --- | --- |
| Data language | `Table`, `Struct`, `Projection`, row-source values | `DataPartDTO` | the blueprint, the engine, the workflow plan |
| Expressions | selections, literals, field references, operations | expression DTOs and operation specifications | the blueprint, the engine runtime |
| Blueprint | language DTOs | `GraphBlueprint` | declaration classes, symbol keys |
| Planning | `GraphBlueprint` | `WorkflowPlan` | authoring classes; it reads DTOs only |

A row source is a value. A row shape is the type of one row, not a schema
instance or a dictionary. Reading a member produces a typed selection. A
projection is a named relation with output expressions and a row source; it is
not a raw SQL string and not a second kind of table declaration.

The data language transcribes declarations into its DTO. Planning never sees the
declaration classes, the field descriptors or the row-source wrapper. It sees
the DTO and the plans derived from it.

## Where a change belongs

A join is a row-source operation. Its semantics, its generated row shape and its
plan DTO belong to the row-source package.

!!! warning "Join changes belong to the row-source package"
    A join-semantics change lives in the row-source algebra and its DTO. It does
    not require editing table declarations, the core planners and the authoring
    API.

    If a planner needs a generated join shape, the row-source interface exposes
    that shape. The planner does not import a private row-source module to find
    it.

The same rule applies to filters, unions, groups, distinct and ordering: they are
row-source operations, not planner special cases.

An operation is different. An operation specification lives with expressions;
its engine emitter lives with the DuckDB executor. Adding an operation is one
specification plus one emitter. It does not edit a dispatcher.

## Row-source model

The plan DTO is a small algebra. Each node owns one decision.

| DTO | Meaning |
| --- | --- |
| `RowScanDTO` | read one named table or projection relation |
| `RowFilterDTO` | keep the input rows that satisfy one predicate |
| `RowUnionDTO` | stack two same-shaped plans, optionally removing duplicates |
| `RowJoinDTO` | equi-join two plans on one expression from each side |
| `RowGroupByDTO` | one row per distinct non-null key tuple, with members collected |
| `RowDistinctDTO` | remove duplicate rows while preserving shape |
| `RowOrderByDTO` | order rows without changing shape |

The semantics are part of the DTO:

- a null join key never matches in any join mode;
- `group_by` drops a row whose key tuple contains a null before grouping;
- a join produces exactly `{on, left, right}`; only the side that can be
  unmatched becomes nullable;
- a group produces exactly `{by, members}`; keys are non-null and member order is
  unspecified;
- `union` compares shapes structurally, by external names and logical types;
- `order_by` has one direction for all keys;
- a generated record is a struct value, not a row source.

A plan is frozen. Two equal plans denote one relation, and a decoded blueprint
computes the same plan without the authoring object.

## DTO shapes

Only the blueprint and the workflow plan are serialisable artifacts. The
blueprint's data language uses these DTOs:

```text
distribution/languages/annotations/model/internal/dto/blueprint_dto.py
    AnnotationDTO(namespace, id, arguments)

distribution/languages/expressions/model/internal/dto/blueprint_dto.py
    LiteralExpressionDTO, FieldReferenceDTO, OperationExpressionDTO

distribution/languages/asset/model/internal/dto/asset_dto.py
    AssetPartDTO, AssetDTO, AssetLayoutDTO, AssetSemanticsDTO,
    AssetGovernanceDTO, AssetLicenseDTO

distribution/languages/data/model/internal/dto/blueprint_dto.py
    DataPartDTO
    StructDTO, RelationDTO, ColumnDTO
    ProjectionDTO
    RowScanDTO, RowFilterDTO, RowUnionDTO, RowJoinDTO,
    RowGroupByDTO, RowDistinctDTO, RowOrderByDTO

distribution/languages/topology/model/internal/dto/blueprint_dto.py
    GraphPartDTO, NodeDTO, EdgeDTO, PropertyDTO

distribution/languages/binding/model/internal/dto/blueprint_dto.py
    NodeBindingDTO, EdgeBindingDTO

distribution/model/public/refs.py
    NodeRef, EdgeRef, RelationRef, FieldRef, PropertyRef, AssetRef,
    OperationRef

distribution/interpreter/model/public/graph_blueprint.py
    GraphBlueprint(graph, data, assets, bindings)
```

## Typed references

A blueprint is a semantic model, not a symbol table. Every cross-symbol field is
a role type from `distribution/model/public/refs.py`:

| Role | Names | Used by |
| --- | --- | --- |
| `NodeRef` | one topology node | `NodeDTO.parent`, `EdgeDTO.source`/`target`, binding targets and endpoints |
| `EdgeRef` | one topology edge | `EdgeDTO.parent`, edge binding targets |
| `RelationRef` | one relation or projection | `RowScanDTO.relation` |
| `FieldRef` | one declared field | `ColumnDTO.ref`, `FieldReferenceDTO.field` |
| `PropertyRef` | one graph property | `PropertyDTO.ref` |
| `AssetRef` | one logical asset | `RelationDTO.asset` |
| `OperationRef` | one operation specification | `OperationExpressionDTO.operator` |

Each wraps a kernel `SymbolRef` and exposes `.symbol`, `.key`, `.name` and a
constructor from `(language, Key)` or from a `SymbolRef`. Equality and hashing
use the wrapped reference. `.name` is the last key segment.

A reference serialises as `[language, role, *key segments]`:

```json
["data", "field", "sites.site_name"]
["expressions", "operation", "default_to"]
```

The role token makes the document decodable without knowing which DTO field it
came from. A field symbol's key joins its owner and the column name, and a
property symbol's key joins its component and the property name.

The expressions language (`name = "expressions"`) publishes one `operation`
symbol per built-in specification. The linker order is
`expressions, asset, data, topology, binding`: expressions resolve first, then
asset declarations, then data relations that reference assets and expressions,
then topology and bindings.

An expression tree is a value, not a symbol: it references field and operation
symbols through typed refs.

The graph DTO has these rules:

- no `symbol_id`, symbol key, Python module path or declaration expression
  appears in a graph node or edge identity;
- a Python binding carries only a stable `PythonRefDTO(module, qualname,
  signature)`;
- endpoints and parents are graph names, not declaration identities;
- an annotation payload is `(namespace, id, arguments)`;
- a language DTO knows only the DTOs of the languages it depends on, never the
  blueprint;
- the blueprint codec composes the language codecs;
- a DTO codec lives beside the DTO and uses `to_document` / `from_document`.

`DataPartDTO` contains the data declarations. `GraphPartDTO` contains the graph
declarations. `NodeBindingDTO` and `EdgeBindingDTO` connect one data row context
to one graph record. `GraphBlueprint` is the assembled semantic model.

## Planning boundary

Planning reads a `GraphBlueprint` and runs each planner. The generic
`DuckDbSourcePlanner` turns compatible asset layouts into
`("source_relation", "duckdb")` steps. The four core planners decompose the rest
of the blueprint into row sources, projections, bindings and aggregates, emit
instructions through the DuckDB SQL emitter, and return `Step`s. The kernel assembles those steps into a `WorkflowPlan`. Planning does
not read authoring declarations and does not call the blueprint package.

```text
GraphBlueprint
    -> DuckDbSourcePlanner() and core_planners()
    -> relation plans and SQL text
    -> Step(instruction=("source_relation" | "sql", "duckdb"), ...)
    -> WorkflowPlan
```

The relational plan is engine-neutral. It describes scans, row effects, filters
and outputs. The emitter turns that plan and the expression DTOs into SQL. The
plan stores the instruction, not the engine's live objects.

A planner other than core receives the same linked `GraphBlueprint` and returns
its own steps. A target planner such as `FilePlanner` consumes
`ArtifactPattern.of("core", "graph", "**")` and emits its own `InstructionKind`. It does not
rewrite the core steps.

## Source-rendering round trip

A language has two directions:

- `service/_private/transcription.py`: declarations -> symbols and language DTO;
- `service/_private/source.py`: language DTO or symbol value -> `SourceFragment`.

A language renders its own DTO using its dependency languages' renderers. The
blueprint source service delegates to each language and assembles the fragments;
it does not render data, topology or binding source itself.

The round trip is a contract:

```text
GraphBlueprint
    -> rendered authoring source
    -> create_blueprint(...)
    -> equivalent GraphBlueprint
```

"Equivalent" means the same semantic model, not the same original text. The
renderer emits one valid authoring form. Two declaration spellings that mean the
same thing produce the same blueprint, and the round trip reproduces that
blueprint.

The round trip proves three things:

- the blueprint carries enough information to reconstruct the declarations;
- no language depends on the declaration objects that produced the DTO;
- rendering is a language responsibility, not a blueprint special case.

## Current state and limits

The data model is implemented:

- `distribution/languages/data/model/internal/dto/blueprint_dto.py` defines
  `DataPartDTO`, `StructDTO`, `RelationDTO`, `ColumnDTO`, `ProjectionDTO` and the
  `Row*DTO` plans. They carry graph names and typed refs, never a `symbol_id` or
  a symbol key. Every `RelationDTO` carries an `AssetRef`.
- `distribution/languages/asset` defines the asset language, `AssetPartDTO` and
  its codec. A relation names a logical asset, not a physical reader binding.
- `distribution/languages/asset`, `data`, `topology`, `binding` and `expressions`
  each provide a kernel `Language` adapter, a transcription service and a source
  service. Their languages discover declarations, transcribe symbols and
  render those symbol values back to authoring source.
- `distribution/languages/expressions/model/internal/dto/blueprint_dto.py`
  defines `LiteralExpressionDTO`, `FieldReferenceDTO`, `VariableExpressionDTO`
  and `OperationExpressionDTO`. A field read carries a `FieldRef` and a nested
  path; an operation carries an `OperationRef`. An expression is an inline
  fragment, not a separately keyed symbol.
- `distribution/interpreter` defines `GraphBlueprint(graph, data, assets,
  bindings)`, a composing codec and a source service. The source service
  delegates to the asset, data, topology and binding renderers and assembles
  their fragments.
- `distribution/modules/duckdb` owns `DuckDbSourcePlanner`, which reads
  `AssetLayout` and emits `("source_relation", "duckdb")` steps, plus the SQL
  emitter, the executor and the engine resource.
- `distribution/modules/core` owns the four core planners, the engine-neutral
  relation plans and the `("sql", "duckdb")` steps.
- The kernel scheduler dispatches on `step.instruction.kind`; SQL is one
  instruction kind.

The canonical type DTOs live in `kernel/model/internal/types`; the package root
re-exports the authoring type vocabulary.

The remaining limits in this area are:

- a Python instruction is a reference (`("python", "cpython")` carries module
  and qualname), not the callable body;
- public `GraphBlueprint` fields reference internal language DTOs;
- the core planners depend on the DuckDB SQL emitter.

## What to remember

- Assets belong to the asset language; relations name them with `AssetRef`.
- Row sources, joins and projections belong to the data language.
- Expressions contribute operation specifications and expression DTOs.
- The blueprint assembles DTOs; planning reads the blueprint and never the
  declarations.
- A join change belongs to the row-source package.
- The blueprint must round-trip through rendered authoring source.

Next: [Testing](testing.md).
