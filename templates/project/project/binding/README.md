# Binding

**BLUF:** A binding is the fulfilment: the one place a relation meets a record.

## Situation

The two axes meet here. A binding states whether a relation's grain, identity and
coverage satisfy a record's purpose, and where they fall short.

## Mission

Own the mapping from a published relation's rows to one record. Do not own the
record's meaning, the relation's meaning, or the row plan.

## Execution

- A binding MUST own one file, grouped by the target node:
  `binding/<node>/binding.py` for the node and `<predicate>__<target>.py` for an
  edge.
- The meaning MUST be present and inline; a binding MUST NOT opt out. Its
  purpose MUST answer the four questions: grain, identity, coverage, meaning.
- The binding's `name` is a display handle: it MUST be excluded from the
  identity digest, so a rename does not change what the binding declares.
- A binding MUST NOT have a docstring; its meaning is its documentation.
- The purpose MUST name the record's use in a clause, then state how the relation
  answers it. It MUST NOT be a row recipe ("Supply X from each row's y").

  The shape is the point; the example is from the conformance project.

  ```python
  # recipe: says what the expression does, not what record use it serves
  Purpose("Supply HAS_PART edges from each row's part_id.")

  # fulfilment: names the use, relation, grain, identity, coverage and shortfall
  Purpose(
      "The item_parts relation fulfils the HAS_PART use as the link a consumer "
      "follows from an item to one of its parts: each item-part row supplies one "
      "edge, keyed by the item and part ids, covering every nested part; an item "
      "with no part supplies no edge."
  )
  ```
- A binding MUST read a published relation, never a stage.
- A missing key MUST be a row to drop or a data failure; it MUST NOT be a silent
  default.
- The row mapping MUST be inline in the binding; a one-use mapping helper MUST NOT
  become a module-level name.

## Support

Imports `relation/`, `graph/` and the framework. This is the only layer that
imports both axes.

## Gate

`tests/test_philosophy.py`, `uv run pytest` and `uv run pyright`. A purpose that copies the record's
meaning or describes the expression fails the gate.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY follow RFC 2119.
