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

- A source relation MUST own one file and MUST state `contract=...` or
  `contract=Omitted`.
- A source relation MUST be declared as
  `class Sites(SourceRelation[AssetT])` with `SourceRelationOptions(...)`.
- Fields MUST use `field(...)` and MUST state `meaning=...` or `meaning=Omitted`;
  a nested record MUST be a `Struct` beside it.
- A field's definition MUST state the value, its unit and its null meaning; name,
  type and provenance MUST be derived, never restated.
- A source relation read by a binding SHOULD declare a contract. The identity MUST
  name the source's key fields.
- A nested `Struct` MAY live beside the source relation it serves.
- A source relation MUST NOT expand an array or join another relation; that
  belongs in `../derived/`.
- The contract MUST be inline at the declaration; a one-use field expression MUST
  be inlined. The declaration MUST NOT have a docstring.

## Support

Imports `asset/` and the framework. Read `../derived/README.md` next.

## Gate

`tests/test_philosophy.py` and `kbs check`. A source relation with a derivation
fails the model check, not the wording.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY follow RFC 2119.
