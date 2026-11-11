---
title: Guard quality
summary: Remove exact duplicates, collapse keys with min() and find conflicting non-null values before merging.
section: operate
order: 20
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/distribution/modules/deduplication/service/_private/planner.py
  - kg_build_system/distribution/modules/merging/service/_private/planner.py
  - kg_build_system/distribution/modules/merging/model/public/configuration.py
  - kg_build_system/distribution/modules/conflict_validation/service/_private/planner.py
  - kg_build_system/distribution/modules/conflict_validation/service/_private/executor.py
subject: modules
perspective: guide
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Modules, outputs and quality</span><a href="/subjects/modules">Overview</a><a href="/operate/quality" class="active">Guide</a><a href="/spec/modules">Spec</a><a href="/reference/api">API</a><a href="/philosophy/anti-patterns">Philosophy</a><a href="/review/limits">Review</a></div>
<!-- END GENERATED:views -->

> [!lede]
> Three planners sit between bound records and an output target. Two rewrite records; one reports disagreement and otherwise forwards records unchanged. None of them guesses a semantic winner beyond SQL min().

## What it is

| Planner | Job | Exact rule | Effect on records |
| --- | --- | --- | --- |
| `DeduplicationPlanner()` | Remove exact repeats | One `SELECT DISTINCT *` per bound component over the whole row | Duplicates removed |
| `MergingPlanner(...)` | One row per build key in scope | Group by `build_key`, take `min()` of every property and edge endpoint key | Same-key rows collapse |
| `ConflictValidationPlanner(...)` | Find disagreement | Count distinct non-null values per component, property and build key; flag counts above one | Records forwarded when it passes |

Merging drops `_kg_binding_symbol`, because that column is not in its field list. A target then writes the survivors; see [Publish outputs](/operate/outputs).

## Rules

- Deduplication is exact full-row only, including `_kg_binding_symbol`. It is not key-based: there is no survivor policy, no fuzzy match and no cross-component pass.
- Two rows that differ in one column both survive. A duplicate must match in build key, every property, both endpoint keys and the binding symbol.
- Merging groups by `build_key` and takes `min()` for every property. For an edge it also minimizes `source_build_key` and `target_build_key`. Two non-null values do not raise; the minimum wins.
- Scope merging explicitly with `MergingConfiguration(components=(...))`. The default, all bound components, is unsafe for edge families that deliberately keep parallel facts. An unbound component in the scope emits no step.
- Conflict validation runs per bound component and property. It counts distinct non-null values per `build_key` and flags a count above one. Run it before merging; after a merge it usually finds nothing.
- `ConflictValidationPlanner(ConflictValidationConfiguration(fail_on_error=True))` fails the run on a finding. The report artifact is still returned and can appear in a failed run. With `False`, it publishes, forwards and continues.
- Rewriting planners produce ordinary outputs. A later step must read them, or assembly refuses the unread output.

**Blind spots of conflict validation:**

| Blind spot | Why |
| --- | --- |
| Null versus value | Nulls are filtered out of the distinct count. |
| Endpoint conflicts | Endpoints are binding outputs, not declared properties. |
| `_kg_binding_symbol` | The column is not checked. |
| Unbound components | They emit no steps. |
| Extra columns | Columns outside the declaration are invisible. |
| Cross-component or cross-key | No such pass exists. |

## Example

```python
from kg_build_system import compile
from kg_build_system.distribution import (
    ConflictValidationConfiguration,
    ConflictValidationPlanner,
    DeduplicationPlanner,
    FileConfiguration,
    FilePlanner,
    MergingConfiguration,
    MergingPlanner,
)

from my_project.topology import SiteNode, UnitNode

planners = (
    ConflictValidationPlanner(ConflictValidationConfiguration()),  # first
    DeduplicationPlanner(),
    MergingPlanner(MergingConfiguration(components=(SiteNode, UnitNode))),
    FilePlanner(FileConfiguration("graph.jsonl")),
)
plan = compile(planners=planners)
```

The order matters. Validation sees parallel values; deduplication removes whole-row repeats; the scoped merge collapses site and unit keys; the file target writes the survivors. The scope is a tuple of concrete `Node` or `Edge` classes, not component-name strings. A merge before validation would hide the disagreement it is meant to find.

## Limits

- Deduplication removes only exact duplicates. It does not resolve two different rows for one key.
- Merge is not a conflict check. `min()` is arbitrary for text and chooses the earliest temporal value; two real values silently become one.
- Merge assigns each build key one record per component. It cannot preserve deliberately parallel edge facts in the same component.
- Validation cannot repair, list the competing values or attribute them. A finding names the count only.
- Nulls, endpoints, binding symbols, unbound components and undeclared columns are outside validation.
- Nothing here checks that an edge endpoint matches a node key. That failure appears at import, not at build time.
- The accepted quality boundary is in [Review limits](/review/limits); the long failure table is in [Failures](/reference/failures).

## Next

[Debug a build](/operate/debug) — read the report when a quality step fails.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-033 | Let the merge planner take an explicit component scope. | 2026-10-28 | accepted | `tests/distribution/planners/test_dedup_merge_conflict_planners.py`; `docs/reference/planners-and-executors.md#mergingplanner` |
