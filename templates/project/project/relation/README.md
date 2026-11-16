# Relation

**BLUF:** This directory is the relation axis. A relation is a contract, not a
pipeline step.

## Situation

A relation states what rows exist in the domain and what one row means. It is not
defined by the graph's use of it; the binding is what makes it relevant to a
record.

## Mission

Own source relations and derived relations. Do not own records or bindings.

## Execution

- A source relation is asset-backed; a derived relation is computed and published.
- A published relation MUST be a `Contract`: Definition(grain, identity) + Meaning.
- The relation MUST be stateable in one sentence with no graph nouns and no
  operator verbs.
- If the sentence needs a join, filter or expansion, that operation is a row
  source or a private stage, not the relation's name.
- A published relation MUST NOT name a record's key, properties or endpoints.
- The contract MUST be inline at the declaration. The declaration MUST NOT have a
  docstring; the contract is its documentation.

## Support

Imports `asset/`, `relation/` and the framework. Never `graph/` or `binding/`.
Read `source/README.md` or `derived/README.md` next.

## Gate

`tests/test_philosophy.py` and `kbs check`. A relation read by a binding should
declare a contract; a derived relation must.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY follow RFC 2119.
