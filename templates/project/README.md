# A kg-build-system project

**BLUF:** This is a project skeleton with a neutral conformance fixture. It builds
and its philosophy gate passes; replace the fixture with your domain before you
write your first real declaration.

## Run it

```console
uv sync
uv run pytest
uv run python -m project.build
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
  data/                  the fixture source
  build.py               the composition root
tests/                   the philosophy gate and the smoke test
```

Each directory has a `README.md` directive. Read it before adding a file there.

## Replace the fixture

The fixture is a conformance fixture, not a domain model. Its graph, nodes,
relations and bindings all say “replace it”. The order is:

1. Answer `START-HERE.md`.
2. Replace the asset in `asset/`.
3. Replace the source relation in `relation/source/`.
4. Replace the derived relation and its stage in `relation/derived/`.
5. Replace the records in `graph/` and the graph declaration.
6. Replace the bindings in `binding/`.
7. Delete `data/items.json` and add your source.
8. Run `uv run pytest`.

`kbs init clinic-kg --empty` starts without the fixture when you prefer to write
the first slice directly.

## The gate

`tests/test_philosophy.py` reads the declarations and the blueprint. It fails when
a facade declares, the axes import each other, a stage leaks, a derived relation
has no contract, a binding has no purpose or states a row recipe, or the graph has
no purpose. `tests/test_project.py` proves the fixture compiles and executes.

A failure is a model change, not a wording change.
