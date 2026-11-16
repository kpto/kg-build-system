# Source relations

**BLUF:** A source relation is the rows one asset supplies, typed and named. It
does not derive, join or reshape them.

## Situation

This is the first published relation on the relation axis. It names the asset and
turns its members into typed fields.

## Mission

Own asset-backed relations: `field(...)` members, a `Contract`, and the field
definitions.

## Execution

- A source relation MUST own one file.
- `class Sites(SourceRelation[AssetT])` with `SourceRelationOptions(...)`.
- Fields use `field(...)`; a nested record is a `Struct` beside it.
- A field's definition states the value, its unit and its null meaning; name,
  type and provenance are derived.
- A source relation read by a binding SHOULD declare a contract. The identity
  names the source's key fields.
- A nested `Struct` MAY live beside the source relation it serves.
- A source relation MUST NOT expand an array or join another relation; that
  belongs in `../derived/`.
- The contract MUST be inline at the declaration. The declaration MUST NOT have a
  docstring; the contract is its documentation.

## Support

Imports `asset/` and the framework. Read `../derived/README.md` next.

## Gate

`tests/test_philosophy.py` and `kbs check`. A source relation with a derivation
fails the model check, not the wording.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY follow RFC 2119.
