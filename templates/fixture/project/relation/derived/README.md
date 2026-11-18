# Derived relations

**BLUF:** A derived relation is a published contract; a stage is private.

## Situation

The relation axis supplies rows. This directory is where a relation is computed,
named and offered to a consumer. It sits between source access and the binding.

## Mission

Own published derived relations: their Definition (grain, identity), their
Meaning, and their private stages. Do not own source access, records, or the map
to a record.

## Execution

- One package MUST own one relation: `relation.py` MUST publish, `_<stage>.py`
  MUST compose.
- A derived relation MUST pin a named row source and read every output through
  its shape; each `computed_field` MUST state `meaning=...` or `meaning=Omitted`:

  ```python
  rows = <source>.row_source()

  class Name(DerivedRelation(rows)):
      options = DerivedRelationOptions(...)
      field = computed_field(rows.shape.<field>)
  ```

  A `Stage` MUST follow the same pattern with `Stage(rows)`. The named row source
  is the one non-declaration value the style keeps.
- The identity MUST name declared outputs and MUST be true of the plan; add a key
  output or `distinct()` rather than declare a false identity.
- A published relation MUST NOT name a record's property, key or endpoint.
- A step with no consumer MUST be a `Stage`, not a relation.
- Each output expression MUST be inlined at its `computed_field`; a one-use
  selection MUST NOT become a module-level helper. The pinned row source is the
  exception: it is named, and every output reads `rows.shape.<field>`. The contract MUST be inline at
  the declaration. The declaration MUST NOT have a docstring.

## Support

Imports `relation/source`, `asset/` and the framework. Never `graph/` or
`binding/`. Read `../../../binding/README.md` next.

## Gate

`tests/test_philosophy.py`, `uv run pytest` and `uv run pyright`. A failure changes the design, not the
wording.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY follow RFC 2119.
