---
title: Extension reference
summary: Project-local and kernel extension surfaces, the object to add, and the current limits.
section: reference
perspective: reference
order: 180
status: normative
verified: 2026-11-17
sources:
  - kg_build_system/api.py
  - kg_build_system/distribution/languages/expressions/service/public/operations.py
  - kg_build_system/distribution/languages/data/model/public/row_operations.py
  - kg_build_system/distribution/languages/expressions/model/internal/dto/operation_dto.py
  - templates/project/README.md
---

> [!lede]
> Extension is a primary feature of the framework, not a last resort. The default distribution is one composition of the kernel; a project is expected to add value operations, relation operations, source adapters and planner/executor modules, and to compose them explicitly.

## Surface

### The two layers

| Layer | What it extends | Composed by | Examples |
| --- | --- | --- | --- |
| Project-local | The project's vocabulary and workflow | `manifest.py` | value operation, relation operation, source adapter, planner/executor module |
| Kernel | A different toolchain or distribution | `Toolchain(...)` and a runtime | language, linker, planner, executor, resource provider, runtime |

Project-local extension comes first. A project adds an ordinary object and composes it; it changes the kernel only when the six protocols cannot carry the concept.

## Details

### Project-local lanes

| Need | Object | Where it lives | Composed by |
| --- | --- | --- | --- |
| One value per row | `OperationSpec` + typed `Operation` handle | `expression/` | `ExpressionsLanguage((*DEFAULT_OPERATIONS, SPEC))`; engine `ExpressionEmitter` |
| A different row count or shape | `RelationOperationSpec` + `RelationOperation` + `RowSourceEmitter` | `modules/` | `DuckDbInstructionEmitter.with_row_sources(...)`; `default_toolchain(engine=...)` |
| Decode a physical input | source planner + executor (a module) | `modules/` | `default_toolchain(planners=..., executors=...)` |
| A pass over records or a new artifact | planner + executor (a module) | `modules/` | `default_toolchain(planners=..., executors=...)` |

The template has a minimal example of each of the first three: `project/expression/hello.py`, `project/modules/hello_world.py` and `project/modules/count_rows.py`.

### Value operation

A value operation is one row in, one value out. It is a `Selection` extension, not a relation operation:

```python
from kg_build_system import INT, STR, ArgumentSpec, Operation, OperationSpec, Selection

SEVERITY_RANK = OperationSpec(
    name="severity_rank",
    arity=1,
    arguments=(ArgumentSpec(expected=STR),),
    result_type=INT,
)
severity_rank: Operation[
    [Selection[str]], int,
] = Operation(SEVERITY_RANK)
```

Both authoring forms are the same expression:

```python
severity_rank(row.condition.alter_rows().drop_null())
row.condition.alter_rows().drop_null().custom_op(severity_rank)
```

Compose the operation set into the expressions language and supply the engine emitter:

```python
expressions = ExpressionsLanguage((*DEFAULT_OPERATIONS, SEVERITY_RANK))
languages = default_languages(expressions=expressions)
engine = DuckDbSqlEmitter(
    instruction_emitter=(
        DuckDbInstructionEmitter().with_operators(SeverityRankEmitter())
    ),
)
toolchain = default_toolchain(languages=languages, engine=engine)
```

There is no operation registry and no `register_operation`. The operation set is a composition value. A value operation must not carry a row effect, a grain change or an aggregate; use `alter_rows()` for a row effect and a relation operation or a `Stage`/`DerivedRelation` for a grain change.

### Relation operation

A relation operation consumes one input row source and produces one row source with a declared output shape and grain. It is the surface for a global count, a window or another grain-changing rule:

```python
class CountRow(Shape):
    count: Selection[int]

COUNT_ROWS = RelationOperationSpec(
    name="count_rows",
    output=CountRow,
    grain="one_total",
)
count_rows = RelationOperation(COUNT_ROWS)
counts = Items.row_source().custom_op(count_rows)
```

The plan carries a `RowOperationDTO`; the project supplies a `RowSourceEmitter`:

```python
class CountRowsEmitter:
    node_type = RowOperationDTO

    def emit(self, plan, context):
        return (
            "SELECT COUNT(*) AS count FROM "
            f"{context.relation_for(plan.input)}"
        )

engine = DuckDbSqlEmitter(
    instruction_emitter=(
        DuckDbInstructionEmitter().with_row_sources(CountRowsEmitter())
    ),
)
```

A relation operation is plan-local. Its output is published only when a `Stage` or `DerivedRelation` pins it and states a matching grain in its `Definition`. Chaining is sequential: a parent `RowOperationDTO` reads its child as a named `kg_rowsource_N`; the core planner materialises children first, so the parent emitter uses `context.relation_for(plan.input)` rather than the child's SQL text. The `str` return is the relational boundary; an expression emitter returns an `exp` operand, while a row-source emitter returns a complete relation.

### Source adapter

A source adapter is a planner and executor that decodes one physical input into the relation the declarations already describe. It is not an adapter registry entry and it carries no domain transformation:

- preserve the source schema, column meanings, null assumptions, grain and identity;
- decode and cast to the declared types only;
- do not join, filter for a domain reason, translate identifiers, deduplicate, aggregate, expand an array or change the grain;
- if the bytes do not match the declaration, fail rather than repair the schema.

The template's `project/modules/hello_world.py` is the minimal adapter; `kbs` composition and the input-adapter rule are in the template's `modules/README.md`.

## Kernel extension

The six kernel protocols are the extension surface for a different composition:

| Protocol | Job |
| --- | --- |
| `Language` | One declaration syntax: discover, key, transcribe and render |
| `Linker` | Roots, language order, reference closure and model assembly |
| `Planner` | Linked model to workflow steps |
| `StepExecutor` | One exact instruction kind and its declared resources |
| `ResourceProvider` | Resource lifecycle over the pipeline events |
| `Runtime` | Scheduling, dispatch and the report |

A language, linker, planner or executor is a value passed to `Toolchain`; a provider is passed to the runtime. See [Kernel protocols](/appendix/kernel/protocols) and [The kernel and the extension surface](/book/part-4/01-the-kernel-and-extension).

## Blueprint operation declarations

The blueprint publishes the expressions language's operation declarations in its top-level `operations` part. Each `OperationDTO` states the operation name, arity, argument declarations, parameter declarations, static result type and row effect. The expression node carries the actual `logical_type`; the declaration supplies the signature a viewer can show.

`expected` and `result_type` are `null` when the spec resolves them from the call. Callable validators, result resolvers, `expand` scope and predicate index are live-only details; they are not serialised. A document without `operations` decodes to an empty part. See [Documents](/appendix/reference/documents).

## Decision table

| Question | Extend |
| --- | --- |
| One value per row | Value operation |
| Changes row count or shape | Relation operation, `Stage`/`DerivedRelation`, or planner/executor module |
| New physical input format | Source planner + executor |
| New pass over records or a new artifact | Planner + executor |
| New declaration syntax | Kernel `Language` and a linker |
| New storage engine | `SqlEmitter` + executor + provider |
| New lifecycle resource | `ResourceProvider` |
| Different scheduling or assembly | `Linker` or `Runtime` |
| Changes what a graph means | Model change, proposed before implementation |

## Limits

- A relation operation v1 takes one input row source and JSON parameters. Multi-input and arbitrary expression arguments are a larger plan-model change.
- A value operation is row-preserving. A row effect, grain change or aggregate is not a value operation.
- Operation declarations serialise static expected and result types only. Callable resolvers, validators, dynamic row effects and custom `expand` scope remain live-only; generated source may raise a clear error rather than emit an incomplete declaration.
- The source round trip for a project operation depends on the same `ExpressionsLanguage(operations=...)` composition. The blueprint document carries the declaration; generated source normalises to the operation name.
- A relation operation's output is plan-local. A published relation still needs a `Stage` or `DerivedRelation` contract with a matching grain.
- Binding source synthesis uses generated shape class names for group/unnest shapes; the blueprint round trip is at the document level.

## Next

- [Expressions](/appendix/reference/expressions) — the value-operation surface.
- [Row sources](/appendix/reference/row-sources) — relation operations and the row algebra.
- [Ingest](/appendix/reference/ingest) — source adapters.
- [Project structure](/appendix/developer/project-structure) — `expression/` and `modules/`.
- [The kernel and the extension surface](/book/part-4/01-the-kernel-and-extension) — the kernel composition.
