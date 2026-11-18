# A kg-build-system project

**BLUF:** This project starts from an empty graph and an unanswered design
record. `uv run pytest` is red on purpose: two tests name the answers you owe
before the first declaration. The declarations are the product; the build is
replaceable.

## The first run

```console
uv sync
uv run pytest
```

Two tests fail until you do the first task:

- `test_the_start_here_design_record_is_answered` — `START-HERE.md` still has
  placeholder answers;
- `test_the_graph_declaration_has_a_purpose` — `project/graph/graph.py` still has
  the placeholder purpose.

That is the gate, not a broken template. Do not delete the tests to get a green
run; answer them.

## Start

1. Answer `START-HERE.md` and **keep the answers**. It is the model a cold
   reader reads before the code: purpose, records, relations, fulfilments,
   assumptions and the first slice.
2. Replace the placeholder purpose in `project/graph/graph.py` with the decision
   the graph supports, for whom, and what it is not for.
3. Add the first slice in meaning order: a record in `project/graph/`, its
   source relation in `project/relation/source/`, and the binding in
   `project/binding/`. Read the `README.md` in each directory first.
4. Run `uv run pytest` and `uv run pyright`. Then read the model as a stranger:

   ```console
   uv run kbs check --project project       # print the authored argument
   uv run kbs blueprint --project project   # build the semantic model
   uv run kbs workflow --project project    # compile the plan
   uv run kbs run --project project         # compile and execute
   ```

A project with no derived relation, stage, adapter or operation is valid when
the domain does not need one. Add one only when a record needs a computation the
source rows do not supply.

## What is here

```text
project/                 the package; the declaration tree
  graph/                 the one graph declaration and the record kinds
  asset/                 one logical source unit
  relation/source/       asset-backed relations
  relation/derived/      published computed relations and private stages
  binding/               the fulfilment between a relation and a record
  expression/            project-local value operations
  modules/               project-local planners, executors, adapters and emitters
  manifest.py            the blueprint and workflow declarations
tests/                   the philosophy gate and the build smoke test
notebook/                   the project notebook and console config
```

Each directory has a `README.md` directive. The key words MUST, MUST NOT, SHOULD,
SHOULD NOT and MAY in those directives are used as defined in RFC 2119.

## A worked example

`kbs init --fixture <dir>` writes the conformance example: a complete small
project with records, relations, bindings, an adapter, a value operation and a
relation operation. Use it to see a worked shape:

```console
kbs init --fixture ../example
cd ../example && uv run pytest
```

Read it, run it, then write this project's own argument. Do not copy its domain
into this project and rename the records: the example exists to show the shape,
not to supply an answer.

## The notebook

`notebook/` is the project notebook created by `kbs init`. Record findings and
proposals there, capture revisions, and serve the project console:

```console
kbs notebook status --project .
kbs console --project .
```

The console is a separate page that embeds the design viewer by URL; it is not
another viewer.
