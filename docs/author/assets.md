---
title: Declare an asset
summary: An asset is one logical unit of source data; its profile states what it is and its layout only describes where a planner may look.
section: author
order: 10
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/distribution/languages/asset/model/public/options.py
  - kg_build_system/distribution/languages/asset/service/_private/declarations.py
  - docs/author/assets.md
subject: asset
perspective: guide
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Assets and source data</span><a href="/subjects/asset">Overview</a><a href="/author/assets" class="active">Guide</a><a href="/spec/asset">Spec</a><a href="/reference/api">API</a><a href="/philosophy/meaning-first">Philosophy</a><a href="/review/limits">Review</a></div>
<!-- END GENERATED:views -->

> [!lede]
> A table describes a row shape. An asset describes the source that row shape comes from. Keeping them apart lets a feed move, a table be reused and a graph stay unchanged when the storage changes.

## What it is

An `Asset` is one logical unit of source data, like a package. One asset may back many tables. A table names its asset with `Table[Asset]`; the relation carries that identity as an `AssetRef`.

`AssetOptions` has five jobs:

| Member | Meaning |
| --- | --- |
| `profile` | Required source metadata: subject, coverage, authority, basis. |
| `layout` | Optional descriptive locator: kind, locator, format, selector, members, properties. |
| `semantics` | Optional declaration-level claims and frames. |
| `governance` | Optional licence, owner and frozen metadata. |
| `name`, `website`, `version` | Identity and release metadata. |

`AssetAuthority` is `primary`, `derived`, `reference` or `inferred`. The profile answers “what is this source and why should I trust it”; it is not a schema.

## Rules

- A concrete asset declares `options = AssetOptions(...)`. Name defaults to the class name in snake case and must be unique.
- `AssetProfile` is required and its `subject`, `coverage` and `basis` are non-empty.
- A table that reads an asset must be `Table[AssetT]`. A relation without a logical asset is refused.
- `AssetLayout` is descriptive metadata, not an access contract. It opens no file and proves no relation exists.
- A layout member is resolved by a compatible planner: `members[relation]`, then `selector`, then `locator`.
- Governance is data. It does not enforce a licence at execution time.

## Example

```python
from kg_build_system import (
    Asset, AssetAuthority, AssetLayout, AssetOptions, AssetProfile,
)

from pathlib import Path

DATA = Path(__file__).parent / "data"


class Estate(Asset):
    options = AssetOptions(
        name="estate",
        version="2026-08",
        profile=AssetProfile(
            subject="monitored estate records",
            coverage="sites, equipment, surveys and logger readings",
            authority=AssetAuthority.PRIMARY,
            basis="estate registry and telemetry export",
        ),
        layout=AssetLayout(
            kind="json",
            locator=str(DATA),
            format="json",
            members={
                "sites": "sites.json",
                "equipment": "equipment.json",
                "surveys": "surveys.json",
            },
        ),
    )
```

## Limits

- There is no adapter concept and no adapter registry. `DuckDbSourcePlanner` handles `parquet`, `json` and `csv`; another format is another ordinary planner with its own instruction kind.
- `AssetLayout.partition_by` is descriptive. The source planner does not use it as a contract.
- `@asset_contract` is an inert generation decorator. It is not an `AssetOptions` field and does not appear in the blueprint.
- One asset may back many tables, but an asset is terminal: an asset does not inherit another concrete asset.

## Next

[Declare data](/author/data) — the row shape that names this asset.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-021 | Model an asset as one logical source unit and keep layout descriptive, not an access contract. | 2026-11-04 | accepted | `tests/distribution/test_asset_language.py` |
| D-022 | Use a generic source planner for parquet/json/csv and reject an adapter registry. | 2026-11-04 | accepted | `tests/distribution/planners/test_duckdb_source_planner.py` |
