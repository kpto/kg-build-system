---
title: Operate
summary: Publish the graph, validate quality, debug a failed run, extend the toolchain and ship a build.
section: operate
order: 0
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/distribution/modules/
  - docs/operate/
---

<div class="kb-section-head">
  <p class="kb-kicker">04 · Operate</p>
  <p class="kb-lede">A compiled plan is not a product until it writes something a consumer can read. This section chooses outputs, guards record quality, finds a failure and adds a capability without editing a dispatcher.</p>
</div>

<figure class="kb-plate">
  <img src="/_assets/modules.svg" alt="Source, rows, projection, binding and records feed quality modules and then file, meta-graph and Neo4j targets.">
  <figcaption>Modules contribute ordinary steps. A planner emits; an executor owns one exact instruction kind.</figcaption>
</figure>

## In this section

| Page | Job | First answer |
| --- | --- | --- |
| [Publish outputs](/operate/outputs) | Write records | JSON Lines, meta-graph, Neo4j bundle, report. |
| [Guard quality](/operate/quality) | Change which records survive | Exact dedup, minimum merge and conflict findings. |
| [Debug a build](/operate/debug) | Find the failed stage | Stage → artifact → first place to look. |
| [Extend the toolchain](/operate/extend) | Add a language, planner, executor or emitter | Implement a protocol and compose a toolchain. |
| [Ship a build](/operate/ship) | Test, tune, compose and run it in CI | Commands, configuration and the checks that gate a job. |

## Pages

Read [Publish outputs](/operate/outputs) for the target matrix, then [Guard quality](/operate/quality) before choosing a merge. [Debug a build](/operate/debug) points at the artifact that records each failure.

## Next

[Publish outputs](/operate/outputs) — turn published openings into files a consumer can open.
