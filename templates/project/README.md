# A kg-build-system project

**BLUF:** This is a project skeleton with a neutral conformance fixture. It builds
and its philosophy gate passes; replace the fixture with your domain before you
write your first real declaration.

## Run it

```console
uv sync
uv run pytest
uv run kbs check --project project       # print the authored model for review
uv run kbs blueprint --project project   # build and print the blueprint
uv run kbs workflow --project project    # compile and print the plan
uv run kbs run --project project         # compile and execute
```

The fixture writes `build/graph.jsonl`, `build/meta_graph.json`,
`build/workflow_plan.json` and `build/build_report.json`.

## What is here

```text
project/                 the package; the declaration tree
  asset/                 one logical source unit
  graph/                 the graph declaration, records and properties
  relation/source/       asset-backed relations
  relation/derived/      published computed relations and private stages
  binding/               the fulfilment between a relation and a record
  expression/            project-local value operations: spec and typed handle
  modules/               project-local planners, executors, emitters, relation operations and resources
  data/                  the fixture source
  manifest.py            the blueprint and workflow declarations
tests/                   the philosophy gate, the smoke test and the example tests
```

Each directory has a `README.md` directive. Read it before adding a file there.
The key words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY in those directives are
used as defined in RFC 2119.

## Replace the fixture

The fixture is a conformance fixture, not a domain model. Its graph, nodes,
relations and bindings all say “replace it”. The order is meaning first:

1. Answer `START-HERE.md` and **keep the answers**. This file is the design
   record a cold reader reads before the code; it is not a one-off interview.
2. Replace the graph declaration and record meanings: purpose, records, uses,
   non-goals and what a consumer may not infer.
3. Replace the relation contracts: what one row means, its grain, identity and
   coverage, independent of the graph.
4. Replace the bindings: which record use each relation fulfils, at what grain,
   identity and coverage, and where it falls short.
5. Implement the declarations. Add a derived relation only when a record needs a
   computation the source rows do not supply; a project with no derived
   relation or stage is valid.
6. Delete `data/items.json` and add your source. If the project does not use the
   fixture's `hello` example, also delete `expression/hello.py`,
   `modules/hello_emitter.py`, the `HELLO`/`HelloEmitter` import and
   composition in `manifest.py`, and the hello tests. If the format is not
   parquet, json or csv, add a source adapter in `modules/` (see below).
7. Add a value or relation operation only when a domain calculation is missing;
   do not add one to satisfy a template example.
8. Run `uv run pytest` and `uv run pyright`.

The release files are inputs, not fixtures. An adapter that reads one may be a
planner and executor; a source relation may keep a nested structure and let a
derived relation expand it.

Copy this template into a new project (or use `kbs init` when the installed
version provides it). The fixture is optional; a project may start from an
empty package when you prefer to write the first slice directly.

## Adapt an input

The shipped source planner reads `parquet`, `json` and `csv`. For another input,
add a project-local module under `project/modules/`: a planner with no-input
steps and an executor that decodes the input and registers the relation.
`hello_world.py` is the minimal pair and `tests/test_input_adapter.py` runs it.
Read `project/modules/README.md` for the rule and the composition.

The adapter preserves the source model. It is a decoder, not a transformer: it
decodes and casts to the types the declarations already state; it does not join,
filter, translate identifiers, deduplicate, aggregate, expand an array or change
the grain. If the bytes do not match the declared relation, it fails rather than
repairing the schema. A rule that changes what a row means belongs in a derived
relation, a stage, a binding or a later planner. Keep the adapter as thin as the
format allows: one step and one relation.

## Extend an expression

A value operation is one row in, one value out; it does not change the row count
or the grain. Add it in `project/expression/` as an `OperationSpec` plus a typed
`Operation` handle. Add its engine emitter in `project/modules/`, and compose the
language and engine in `manifest.py`.

Both authoring forms use the same handle:

```python
from project.expression.hello import hello

first = hello(row.item_label.default_to("Untitled item"))
second = row.item_label.default_to("Untitled item").custom_op(hello)
```

The fixture's `hello` operation is wired into the item binding, so
`tests/test_hello_expression.py` proves both forms and the build. Read
`project/expression/README.md` for the rule. There is no `register_operation`
and no registry; the operation set is part of the expressions language
composition.

A row effect, a grain change or a relation aggregate is not an expression
operation. Use a `DerivedRelation`, a `Stage`, or a relation operation.

## Extend a relation

A calculation that changes the row count or shape is a **relation operation**.
It takes one input row source, declares an output shape and a grain, and supplies
an engine `RowSourceEmitter`:

```python
class CountRow(Shape):
    count: Selection[int]

COUNT_ROWS = RelationOperationSpec(
    name="count_rows", output=CountRow, grain="one_total",
)
count_rows = RelationOperation(COUNT_ROWS)
```

`project/modules/count_rows.py` is the minimal global count. Compose its
emitter into the engine and the engine into the toolchain:

```python
engine = DuckDbSqlEmitter(
    instruction_emitter=(
        DuckDbInstructionEmitter().with_row_sources(CountRowsEmitter())
    ),
)
toolchain = default_toolchain(engine=engine)
```

The output is plan-local until a `DerivedRelation` or `Stage` publishes it with a
matching grain. `tests/test_relation_operation.py` proves the count executes.
The relation operation is not wired into the conformance fixture workflow; it is
an extension example.

## The gate

`tests/test_philosophy.py` reads the declarations and the blueprint. It fails when
a facade declares, the axes import each other, a stage leaks, a derived relation
has no contract, a binding has no purpose or states a row recipe, or the graph has
no purpose. `tests/test_project.py` proves the fixture compiles and executes.

A failure is a model change, not a wording change.
