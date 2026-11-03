# Data and expressions

This page states where row data, expressions and projections live, how they
cross the blueprint and planning boundaries, and what source regeneration must
prove.

## Ownership

| Concept | Owner | What it is |
| --- | --- | --- |
| Canonical types | `kernel/model/public/types` | the one type ontology every layer uses |
| Annotations | `distribution/languages/annotations` | annotation values and DTOs |
| Selections | `distribution/languages/expressions/model/public` | typed reads over a row shape |
| Operation specifications | `distribution/languages/expressions/service/internal/operations` | one specification per operation |
| Row sources | `distribution/languages/table` | the row value a projection or binding reads |
| Joins, unions, filters, groups, distinct, order | `distribution/languages/table` | row-source operations and their plan DTOs |
| Projections | `distribution/languages/table` | a named relation with output expressions and a row source |
| Data DTO | `distribution/languages/table/model/internal/dto/blueprint_dto.py` | the frozen data part of the blueprint |
| Blueprint | `distribution/interpreter` | assembles the layer DTOs into `GraphBlueprint` |
| Relational plan | `distribution/planners/core/service/_private` | engine-neutral relation plans and step planning |
| Instruction emission | `distribution/planners/core` and `distribution/executors/duckdb` | turns a plan into a `("sql", "duckdb")` instruction |
| SQL emitter | `distribution/executors/duckdb/service/_private` | emits DuckDB SQL for an instruction |
| Engine boundary | `distribution/executors/duckdb` | opens and runs the engine through `DuckDbResourceProvider` |

`table` is the `data` language. `expressions` contributes operations and
expression DTOs; it is not a graph language and does not own a build part.

## Table, expression, blueprint and planning

The four boundaries have different jobs:

| Boundary | Input | Output | Must not know |
| --- | --- | --- | --- |
| Table language | `Table`, `Struct`, `Projection`, row-source values | `DataPartDTO` | the blueprint, the engine, the workflow plan |
| Expressions | selections, literals, field references, operations | expression DTOs and operation specifications | the blueprint, the engine runtime |
| Blueprint | layer DTOs | `GraphBlueprint` | declaration classes, symbol IDs |
| Planning | `GraphBlueprint` | `WorkflowPlan` | authoring classes; it reads DTOs only |

A row source is a value. A row shape is the type of one row, not a schema
instance or a dictionary. Reading a member produces a typed selection. A
projection is a named relation with output expressions and a row source; it is
not a raw SQL string and not a second kind of table declaration.

The table language transcribes declarations to its DTO. Planning never sees the
declaration classes, the field descriptors or the row-source wrapper. It sees
the DTO and the plans derived from it.

## Where a change belongs

A join is a row-source operation. Its semantics, its generated row shape and its
plan DTO belong to the row-source package.

!!! warning "Join changes belong to the row-source package"
    A join-semantics change lives in the row-source algebra and its DTO. It does
    not require editing table declarations, the core planner and the authoring
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

A plan is frozen and content-addressed. Two equal plans denote one relation, and
a decoded blueprint computes the same plan key without the authoring object.

## DTO shapes

Only the blueprint and the workflow plan are serialisable artifacts. The
blueprint's data layer uses these DTOs:

```text
distribution/languages/annotations/model/internal/dto/blueprint_dto.py
    AnnotationDTO(namespace, id, arguments)

distribution/languages/expressions/model/internal/dto/blueprint_dto.py
    LiteralExpressionDTO, FieldReferenceDTO, OperationExpressionDTO

distribution/languages/table/model/internal/dto/blueprint_dto.py
    DataPartDTO
    StructDTO, RelationDTO, ColumnDTO
    ProjectionDTO, SourceDTO
    RowScanDTO, RowFilterDTO, RowUnionDTO, RowJoinDTO,
    RowGroupByDTO, RowDistinctDTO, RowOrderByDTO

distribution/languages/topology/model/internal/dto/blueprint_dto.py
    GraphPartDTO, NodeDTO, EdgeDTO, PropertyDTO

distribution/languages/binding/model/internal/dto/blueprint_dto.py
    NodeBindingDTO, EdgeBindingDTO

distribution/interpreter/model/public/graph_blueprint.py
    GraphBlueprint(graph, data, bindings, sources)
```

The graph DTO has these rules:

- no `symbol_id`, Python module path or declaration expression appears in a
  graph node or edge identity;
- a Python binding carries only a stable `PythonRefDTO(module, qualname,
  signature)`;
- endpoints and parents are graph names, not declaration identities;
- an annotation payload is `(namespace, id, arguments)`;
- a layer DTO knows only the DTOs of the layers it depends on, never the
  blueprint;
- the blueprint codec composes the layer codecs;
- a DTO codec lives beside the DTO and uses `to_document` / `from_document`.

`DataPartDTO` contains the data declarations. `GraphPartDTO` contains the graph
declarations. `NodeBindingDTO` and `EdgeBindingDTO` connect one data row context
to one graph record. `GraphBlueprint` is the assembled semantic model.

## Planning boundary

Planning reads a `GraphBlueprint` and runs each planner. The core planner
decomposes the blueprint into sources, row sources, projections, bindings and
aggregates, emits instructions through the DuckDB SQL emitter, and returns
`Step`s. The kernel assembles those steps into a `WorkflowPlan`. Planning does
not read authoring declarations and does not call the blueprint package.

```text
GraphBlueprint
    -> CorePlanner
    -> relational plans and SQL text
    -> Step(instruction=("sql", "duckdb"), ...)
    -> WorkflowPlan
```

The relational plan is engine-neutral. It describes scans, row effects, filters
and outputs. The emitter turns that plan and the expression DTOs into SQL. The
plan stores the instruction, not the engine's live objects.

A planner other than core receives the same linked `GraphBlueprint` and returns
its own steps. A target planner such as `FilePlanner` consumes
`ArtifactType("core", "graph.*")` and emits its own instruction kind. It does not
rewrite the core steps.

## Source-rendering round trip

A language has two directions:

- `service/_private/transcription.py`: declarations -> layer DTO;
- `service/_private/source.py`: layer DTO -> `SourceFragment`.

A layer renders its own DTO using its dependency layers' renderers. The blueprint
source service delegates to each layer and assembles the fragments; it does not
render table, topology or binding source itself.

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
- no layer depends on the declaration objects that produced the DTO;
- rendering is a language responsibility, not a blueprint special case.

## Current state and limits

The data model is implemented:

- `distribution/languages/table/model/internal/dto/blueprint_dto.py` defines
  `DataPartDTO`, `StructDTO`, `RelationDTO`, `ColumnDTO`, `ProjectionDTO`,
  `SourceDTO` and the `Row*DTO` plans. They carry graph names and no
  `symbol_id`.
- `distribution/languages/table`, `topology` and `binding` each provide a
  transcription service and a source service. Their languages implement
  `collect`, `transcribe`, `validate` and `render`.
- `distribution/languages/expressions/model/internal/dto/blueprint_dto.py`
  defines `LiteralExpressionDTO`, `FieldReferenceDTO`, `VariableExpressionDTO`
  and `OperationExpressionDTO`.
- `distribution/interpreter` defines `GraphBlueprint(graph, data, bindings,
  sources)`, a composing codec and a source service. The source service
  delegates to the table, topology and binding renderers and assembles their
  fragments.
- `distribution/planners/core` owns the engine-neutral relation plans and the
  `("sql", "duckdb")` steps. `distribution/executors/duckdb` owns the emitter
  and the engine.
- The kernel scheduler dispatches on `step.instruction.kind`; SQL is one
  instruction kind.

The canonical type DTOs live in `kernel/model/internal/types`; the package root
re-exports the authoring type vocabulary.

The remaining limits in this area are:

- a Python instruction is a reference (`("python", "cpython")` carries module
  and qualname), not the callable body;
- public `GraphBlueprint` fields reference internal layer DTOs;
- the core planner depends on the DuckDB SQL emitter;
- a language may publish only its layer value instead of per-declaration
  definitions.

## What to remember

- Row sources, joins and projections belong to the table language.
- Expressions contribute operation specifications and expression DTOs.
- The blueprint assembles DTOs; planning reads the blueprint and never the
  declarations.
- A join change belongs to the row-source package.
- The blueprint must round-trip through rendered authoring source.

Next: [Testing](testing.md).
