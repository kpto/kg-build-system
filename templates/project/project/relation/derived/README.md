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

- One package MUST own one relation: `relation.py` publishes, `_<stage>.py`
  composes.
- `DerivedRelation(rows)`, `computed_field(...)`,
  `Contract(Definition(...), Meaning(...))`.
- The identity MUST name declared outputs and MUST be true of the plan; add a
  key output or `distinct()` rather than declare a false identity.
- A published relation MUST NOT name a record's property, key or endpoint.
- A step with no consumer MUST be a `Stage`, not a relation.
- The contract MUST be inline at the declaration. The declaration MUST NOT have a
  docstring; the contract is its documentation.

## Support

Imports `relation/source`, `asset/` and the framework. Never `graph/` or
`binding/`. Read `../../../binding/README.md` next.

## Gate

`tests/test_philosophy.py` and `kbs check`. A failure changes the design, not the
wording.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY follow RFC 2119.
