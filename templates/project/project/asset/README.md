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

- One asset MUST back one logical source unit. One asset MAY back several source
  relations.
- An asset MUST declare `AssetOptions(profile=..., layout=..., meaning=...)`.
- `AssetLayout` MUST be descriptive metadata: `kind`, `locator`, `format`,
  `members`. It MUST NOT be an access contract; an access contract is a source
  relation.
- The meaning MUST be inline at the `Asset` subclass. It states what the source
  unit is and what it is not; a declaration with nothing to state MUST pass
  `meaning=Omitted`. A layout path or option used once MUST be inlined; it MUST
  NOT become a module-level helper.
- The declaration MUST NOT have a docstring; the meaning is its documentation.

## Support

Imports the framework only. Read `relation/source/README.md` next.

## Gate

`tests/test_philosophy.py` and `kbs check`. A layout is not a record; if you are
naming a record's properties here, the decision belongs in `graph/`.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY follow RFC 2119.
