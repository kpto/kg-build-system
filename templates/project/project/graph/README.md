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

- `graph.py` MUST hold the one `Graph` declaration and its root `Meaning`.
- A concrete node MUST own one directory: `node.py` and one file per edge from
  that node, named `<predicate>__<target>.py`.
- A concrete node or edge MUST state its own purpose, claims and limitations
  inline. A one-use expression MUST be inlined at the property or declaration.
- The declaration MUST NOT have a docstring; the meaning is its documentation.
- A property MUST be a value on a record; it MUST NOT be a column and MUST NOT be
  a foreign key.
- `__init__.py` MUST be a facade; it declares nothing.

## Support

Imports the framework and `graph/`. Never import `relation/` or `binding/`.
Read `relation/README.md` next.

## Gate

`tests/test_philosophy.py` and `kbs check`. A record that names a source column
is a binding decision in the wrong layer.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY follow RFC 2119.
