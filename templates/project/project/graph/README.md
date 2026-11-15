# Graph

**BLUF:** This directory is the record axis: the graph declaration, concrete
nodes and edges, categories and templates.

## Situation

A graph record states what the graph asserts and what it is for. It never reads a
source relation; the binding is the only place the axes meet.

## Mission

Own the one graph declaration and the concrete record kinds. Do not own source
access, derived relations, or the mapping from rows to records.

## Execution

- `graph.py` holds the one `Graph` declaration and its root `Meaning`.
- One directory per node kind: `node.py` and one file per edge from that node,
  named `<predicate>__<target>.py`.
- A concrete node or edge states its own purpose, claims and limitations.
- A property is a value on a record, not a column and not a foreign key.
- `__init__.py` re-exports; it declares nothing.

## Support

Imports the framework and `graph/`. Never import `relation/` or `binding/`.
Read `relation/README.md` next.

## Gate

`tests/test_philosophy.py` and `kbs check`. A record that names a source column
is a binding decision in the wrong layer.
