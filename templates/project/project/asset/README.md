# Asset

**BLUF:** One asset is one logical source unit. It describes the source; it does
not read it, join it, or define a record.

## Situation

The relation axis starts here. A source relation names an asset with
`SourceRelation[AssetT]`; the asset carries the source's identity, profile and
layout.

## Mission

Own the asset declaration: its name, version, profile and descriptive layout.
Do not own joins, record shapes, or access logic.

## Execution

- One asset per logical source unit. One asset may back several source relations.
- `AssetOptions(profile=..., layout=..., meaning=...)`.
- `AssetLayout` is descriptive metadata: `kind`, `locator`, `format`, `members`.
  It is not an access contract; an access contract is a source relation.
- The meaning states what the source unit is and what it is not.

## Support

Imports the framework only. Read `relation/source/README.md` next.

## Gate

`tests/test_philosophy.py` and `kbs check`. A layout is not a record; if you are
naming a record's properties here, the decision belongs in `graph/`.
