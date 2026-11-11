---
title: Asset specification
summary: An asset MUST name one logical source unit; its profile states meaning and its layout only describes a possible location.
section: spec
perspective: spec
subject: asset
spec: SPEC-001
order: 10
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/distribution/languages/asset/model/public/options.py
  - kg_build_system/distribution/languages/asset/model/public/declarations.py
  - kg_build_system/distribution/languages/asset/service/_private/declarations.py
  - kg_build_system/distribution/modules/duckdb/service/public/planner.py
  - docs/author/assets.md
evidence:
  - tests/distribution/test_asset_language.py
  - tests/distribution/planners/test_duckdb_source_planner.py
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Assets and source data</span><a href="/subjects/asset">Overview</a><a href="/author/assets">Guide</a><a href="/spec/asset" class="active">Spec</a><a href="/reference/api">API</a><a href="/philosophy/meaning-first">Philosophy</a><a href="/review/limits">Review</a></div>
<!-- END GENERATED:views -->

## Requirement

- **R1.** An asset MUST be a subclass of `Asset` with exactly one `options = AssetOptions(...)` assignment; a subclass whose `options` is missing or is not an `AssetOptions` MUST be refused.
- **R2.** `AssetOptions.profile` MUST be an `AssetProfile`; `subject`, `coverage` and `basis` MUST be non-empty strings, and `authority` MUST be an `AssetAuthority`.
- **R3.** `AssetOptions.name` MUST default to the snake-case class name and MUST be unique within a build; a duplicate asset key MUST be refused.
- **R4.** `AssetOptions.layout`, `semantics`, `governance`, `website`, `version` and `name` MUST be optional; an asset that supplies only a profile MUST be legal.
- **R5.** `AssetLayout` MUST be descriptive metadata: `kind`, `locator`, `format`, `selector`, `partition_by`, `members` and `properties` MUST NOT prove that a relation exists or that a resource is readable.
- **R6.** A table that reads an asset MUST be declared `Table[AssetT]`; its relation MUST carry an `AssetRef`, one asset MAY back many tables, and a relation without a logical asset MUST be refused.
- **R7.** `DuckDbSourcePlanner` MUST resolve a relation in the order `members[relation]`, then `selector`, then `locator`; a relative member MUST be joined to `locator` and an absolute member MUST be used unchanged.
- **R8.** `DuckDbSourcePlanner` MUST support `parquet`, `json` and `csv` by default, reading `AssetLayout.format` before `AssetLayout.kind`; a format outside that set MUST produce no source step from that planner.
- **R9.** The distribution MUST NOT provide a source-adapter type or source-adapter registry; a further format MUST be an ordinary planner with its own instruction kind.
- **R10.** `@asset_contract` MUST be an inert generation decorator: it MUST NOT be an `AssetOptions` field, and it MUST NOT add generation instructions to a blueprint.

## Evidence

| Evidence | Proves |
| --- | --- |
| `tests/distribution/test_asset_language.py` | `AssetOptions` validation, name default, `AssetRef` identity and asset-part transcription. |
| `tests/distribution/planners/test_duckdb_source_planner.py` | member, selector and locator resolution; absolute members; supported-format filtering and no step for another format. |

## API

| Name | Meaning |
| --- | --- |
| `Asset` | Base class for one logical unit of source data. |
| `AssetOptions` | One asset's profile plus optional layout, semantics, governance and identity metadata. |
| `AssetProfile` | Required statement of subject, coverage, authority and basis. |
| `AssetAuthority` | `primary`, `derived`, `reference` or `inferred` relation to the claims. |
| `AssetLayout` | Descriptive locator metadata; not an access contract. |
| `AssetGovernance` | Optional license, owner and string metadata. |
| `AssetLicense` | License identifier with optional URL and attribution. |
| `AssetRef` | Typed reference a relation uses to name its asset. |
| `DuckDbSourcePlanner` | Planner for asset-backed parquet, json and csv relations. |

The facade groups and defining modules are listed in [API surface](/reference/api).

## Limits

- `AssetLayout` opens no file and proves no relation; `partition_by` is descriptive and is not used by `DuckDbSourcePlanner`.
- There is no source-adapter registry, no source-adapter type and no per-format field on `AssetOptions`.
- `AssetOptions.website` is a human-facing page; a machine location belongs in `layout.locator`.
- `AssetOptions.version` is a label, not a pin; the build does not fetch, resolve or check it.
- Governance is published data; a license or owner is not enforced at execution time.
- An asset is terminal and is not itself a row source; a table names it, and a graph reads tables.
- `@asset_contract` is upstream of the build; the build never invokes generation.

## Rationale

An asset separates the durable meaning of a source from the deployment fact of where one copy sits, so a table can survive a release move without changing its row shape. Keeping `AssetProfile` mandatory and `AssetLayout` descriptive makes the trust claim explicit and the location replaceable. This is the contract layer of [meaning before mechanism](/philosophy/meaning-first): declare what the source is, then let a planner decide where to read it.

## Next

[Asset subject](/subjects/asset) — the hub for this subject.
