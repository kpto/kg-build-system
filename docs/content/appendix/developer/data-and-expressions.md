---
title: Data and expressions
summary: Where row data, expressions, source relations and derived relations live, and how they cross the blueprint and planning boundaries.
section: developer
perspective: developer
order: 40
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/distribution/languages/data/model/internal/dto/blueprint_dto.py
  - kg_build_system/distribution/languages/expressions/model/internal/dto/blueprint_dto.py
  - kg_build_system/distribution/model/public/refs.py
  - kg_build_system/distribution/service/internal/emission.py
  - kg_build_system/distribution/modules/core/service/_private/planning/emission.py
---

## Interface

The data language owns row sources, source relations, derived relations and the frozen data DTO. The
expressions language owns operation specifications and inline expression
fragments. The blueprint assembles the language DTOs, and planning consumes the
blueprint without the authoring classes. The normative views are
[Data specification](/appendix/spec/data), [Selection specification](/appendix/spec/selection),
[Grain specification](/appendix/spec/grain), [Plan specification](/appendix/spec/plan) and
[Architecture specification](/appendix/spec/architecture).

| Concept | Exact values | Owner |
| --- | --- | --- |
| Authoring selection | `Selection[T]`, `NullableSelection[T]` | `distribution/languages/expressions/model/public/selection.py` |
| Expression fragment | `ExpressionDTO`, `LiteralExpressionDTO`, `VariableExpressionDTO`, `FieldReferenceDTO`, `LookupExpressionDTO`, `OperationExpressionDTO`, `OperationParameterDTO` | `distribution/languages/expressions/model/internal/dto/blueprint_dto.py` |
| Project operation | `OperationSpec`, `ArgumentSpec`, `ParameterSpec`, `Operation`, `DEFAULT_OPERATIONS` | `distribution/languages/expressions/service/public/operations.py` |
| Relation operation | `RelationOperationSpec`, `RelationOperation`, `RowOperationDTO` | `distribution/languages/data/model/public/row_operations.py`, `distribution/languages/data/model/internal/dto/blueprint_dto.py` |
| Operation declaration | `OperationDTO`, `ArgumentDTO`, `ParameterDTO`, `ExpressionsPartDTO` | `distribution/languages/expressions/model/internal/dto/operation_dto.py` |
| Data DTO | `DataPartDTO`, `StructDTO`, `SourceRelationDTO`, `DerivedRelationDTO`, `DefinitionDTO`, `FieldDefinitionDTO`, `ColumnDTO`, `RowSourcePlanDTO` | `distribution/languages/data/model/internal/dto/blueprint_dto.py` |
| Row plan nodes | `RowScanDTO`, `RowFilterDTO`, `RowUnionDTO`, `RowJoinDTO`, `RowGroupByDTO`, `RowDistinctDTO`, `RowOrderByDTO`, `RowUnnestDTO` | `distribution/languages/data/model/internal/dto/blueprint_dto.py` |
| Typed reference | `NodeRef`, `EdgeRef`, `RelationRef`, `FieldRef`, `PropertyRef`, `AssetRef`, `OperationRef` | `distribution/model/public/refs.py` |
| Blueprint | `GraphBlueprint(graph, data, assets, bindings, operations, graph_declaration=None)` | `distribution/interpreter/model/public/graph_blueprint.py` |
| Neutral plan | `RelationPlan`, `Scan`, `Expand`, `Filter`, `RelationSqlEmitter`, `SqlEmitter`, `SqlType`, `ArraySqlType`, `StructSqlType`, `canonical_sql_type` | `distribution/service/internal/emission.py` |
| Core planning | `CorePlan`, `CorePlanning`, `RowSourcePlanner`, `DerivedRelationPlanner`, `BindingPlanner`, `RecordsPlanner` | `distribution/modules/core` |
| DuckDB emission | `DuckDbSourcePlanner`, `DuckDbSqlEmitter`, `DuckDbInstructionEmitter` | `distribution/modules/duckdb` |

`Selection[T]` is the single authoring type. Presence is a type argument:
`NullableSelection[T]` is the alias `Selection[Nullable[T]]`. The compiler tree
stays private; there is no expression-family authoring type and no accessor that
unwraps the tree. A `SourceRelation` or `Struct` read yields
`NullableSelection[T]`; a `DerivedRelation` output or `ComputedStruct` member
follows its `computed_field` selection. Row effects such as `drop_null` and `expand` are
one-shot handles under `selections/effects.py`, and an invalid effect is absent
from the handle type.

An expression is an inline fragment, not a separately keyed symbol.
`FieldReferenceDTO` carries a `FieldRef` and the nested `path` below that field.
`LookupExpressionDTO` carries a target `RelationRef`, a key `ExpressionDTO` and
a `target_field` name. `OperationExpressionDTO` carries an `OperationRef`,
argument expressions and named `OperationParameterDTO` values. The operation
specification lives beside the expressions service; the engine emitter lives
beside the DuckDB executor.

A project operation is one `OperationSpec` plus a typed `Operation` handle. The
language publishes the spec; the engine supplies the emitter; the operation set
is an explicit `ExpressionsLanguage(operations=...)` composition. There is no
operation registry, and an operation not in the language set is an unknown
reference at link time. The authoring forms are `handle(selection)` and
`selection.custom_op(handle)`; both carry the same argument and result types.

A relation operation is a `RelationOperationSpec` over one input row source,
with a declared output shape and grain. `RowSource.custom_op` returns a
`DerivedRowSource[Out]`; the plan carries a `RowOperationDTO` and the engine
supplies a `RowSourceEmitter` registered by the node type. The output is
plan-local until a `Stage` or `DerivedRelation` publishes it with a matching
grain.

The data DTO states the semantic model. `ColumnDTO` carries a `FieldRef`;
`SourceRelationDTO` carries an `AssetRef`; `DerivedRelationDTO` pins a named
derived relation to one `RowSourcePlanDTO` and carries its `Contract`.
`DataPartDTO` contains structs, source relations and derived relations. A stage
is a derived-relation output with no contract; it is plan lineage, not a
consumer relation.
The row plan is a small algebra: each node owns one decision, and the nodes are
frozen values. Their document shape is described in
[Documents](/appendix/reference/documents), the expression vocabulary in
[Expressions](/appendix/reference/expressions), and the row-source algebra in
[Row sources](/appendix/reference/row-sources).

Typed references make the blueprint a semantic model rather than a symbol table.
Each role wraps a kernel `SymbolRef` and exposes `.symbol`, `.key`, `.name` and a
constructor from `(language, Key)` or a `SymbolRef`. A reference serialises as
`[language, role, *key segments]`:

```json
["data", "field", "sites.site_name"]
["expressions", "operation", "default_to"]
```

The role token makes a document decodable without knowing which DTO field
produced it. Field keys join the owner and column name; property keys join the
component and property name.

Planning reads a `GraphBlueprint`, not declarations. `CorePlanning` computes one
`CorePlan` and the four core planners share it. `DuckDbSourcePlanner` turns
compatible asset layouts into `("source_relation", "duckdb")` steps. Core turns
the rest into `RelationPlan` values and emits instructions through an injected
`SqlEmitter`, producing `("sql", "duckdb")` steps and then a `WorkflowPlan`:

```text
GraphBlueprint
    -> DuckDbSourcePlanner() and core_planners(engine=DuckDbSqlEmitter())
    -> RelationPlan and SQL text
    -> Step(instruction=("source_relation" | "sql", "duckdb"), ...)
    -> WorkflowPlan
```

The plan stores scans, expands, filters, outputs and the expression DTOs. It
stores no SQL text and no live engine object. `SqlType`, `ArraySqlType`,
`StructSqlType` and `canonical_sql_type` compose canonical types into SQL
spellings and carry no DuckDB syntax.

A language renders its own DTO through its `service/_private/transcription.py`
and `service/_private/source.py` paths. The blueprint source service delegates
to each language and assembles fragments. The round trip is a contract:

```text
GraphBlueprint
    -> rendered authoring source
    -> create_blueprint(...)
    -> equivalent GraphBlueprint
```

Equivalence means the same semantic model, not the same source text.

## Rules

- A source relation names a logical asset with `AssetRef`; it does not name a
  physical reader binding.
- A row source is a value and a row shape is the type of one row, never a schema
  instance or a dictionary.
- A derived relation is a named relation pinned to one row-source value, not a
  SQL string and not a second kind of source relation.
- A derived relation is a contract: `Definition` states the grain and identity,
  `Meaning` states the purpose, claims and limitations. A source relation may
  state the same contract; a declared contract is always complete. A field states
  its own `FieldDefinition`; name, type and provenance are derived.
- A stage has no contract. It composes inside one published relation, carries a
  definition and no contract meaning, and a binding never reads it.
- Joins, unions, filters, groups, distinct, ordering and unnest are row-source
  operations. Their semantics, generated shapes and plan DTOs belong to the
  row-source package, not to a core planner special case.
- A join produces exactly `{on, left, right}`; only a side that can be unmatched
  becomes nullable. A null join key never matches in any join mode.
- `group_by` drops a row whose key tuple contains a null before grouping. A group
  produces exactly `{by, members}`; member order is unspecified.
- `union` compares shapes structurally by external names and logical types.
  `order_by` carries one direction for all keys.
- A generated record is a struct value, not a row source.
- A plan is frozen. Two equal plans denote one relation, and a decoded blueprint
  computes the same plan without the authoring object.
- A data DTO carries graph names and typed refs, never a `symbol_id`, a symbol
  key, a Python module path or a declaration expression.
- A language DTO imports only the DTOs of the languages it depends on, never the
  blueprint. The blueprint codec composes the language codecs.
- Planning reads DTOs only. It does not import declaration classes, symbol keys
  or the blueprint package.
- Core imports the neutral plan and `SqlEmitter` protocol only. It never imports
  `distribution/modules/duckdb`; `api.default_toolchain` injects
  `DuckDbSqlEmitter()` unless the caller supplies another `SqlEmitter`.
- A non-DuckDB engine supplies an emitter and an executor explicitly.
- The renderer emits one valid authoring form. Two declaration spellings with
  the same meaning produce the same blueprint, and the round trip reproduces it.

## Limits

- A Python instruction is a reference such as `("python", "cpython")` carrying a
  module and qualname, not the callable body.
- Public `GraphBlueprint` fields reference internal language DTOs.
- `Selection[T]` is an authoring value and is not serialised.
- The neutral plan is not a SQL builder; SQL text appears only at the emitter
  boundary.
- `SqlType` carries no nullability.
- `lookup` is an ungated value operation returning a nullable array of target
  records. `zip` pairs arrays by position and refuses unequal lengths.
- `RowUnnestDTO` expands one direct array member and preserves the rest of the
  source row.
- A field declares a value type, never `T | None`; absence belongs to the owner
  and is composed when the row is read.

## Next

[Plan specification](/appendix/spec/plan) — how the neutral plan becomes assembled steps.
