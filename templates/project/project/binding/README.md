# Binding

**BLUF:** A binding is the fulfilment: the one place a relation meets a record.

## Situation

The two axes meet here. A binding states whether a relation's grain, identity and
coverage satisfy a record's purpose, and where they fall short.

## Mission

Own the mapping from a published relation's rows to one record. Do not own the
record's meaning, the relation's meaning, or the row plan.

## Execution

- One file per binding, grouped by the target node: `binding/<node>/binding.py`
  for the node and `<predicate>__<target>.py` for an edge.
- The meaning is required. Its purpose answers the four questions:
  grain, identity, coverage, meaning.
- Name the record's use in a clause, then say how the relation answers it. A row
  recipe ("Supply X from each row's y") is not a fulfilment.
- A binding reads a published relation, never a stage.
- A missing key is a row to drop or a data failure, never a silent default.

## Support

Imports `relation/`, `graph/` and the framework. This is the only layer that
imports both axes.

## Gate

`tests/test_philosophy.py` and `kbs check`. A purpose that copies the record's
meaning or describes the expression fails the gate.
