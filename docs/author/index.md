---
title: Author
summary: "The nine declarations that turn a source asset into records: asset, rows, values, grain, projection, topology, binding, meaning and generation."
section: author
order: 0
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/distribution/languages/
  - docs/author/
---

<div class="kb-section-head">
  <p class="kb-kicker">02 · Author</p>
  <p class="kb-lede">A graph is declared in one direction: source, row shape, value, grain, graph meaning, mapping. Each page owns one object and one decision. Read them in order the first time.</p>
</div>

<figure class="kb-plate">
  <img src="/_assets/authoring.svg" alt="Asset feeds Table, Field and Selection; row sources feed projections; topology and bindings meet at the graph; semantics attaches to every declaration.">
  <figcaption>The authoring chain. An arrow means “is read by” or “is named by”, not an import.</figcaption>
</figure>

## In this section

| # | Page | One decision |
| --- | --- | --- |
| 01 | [Declare an asset](/author/assets) | What one logical source is, and what its layout does not promise. |
| 02 | [Declare data](/author/data) | Which row shape and value types the source offers. |
| 03 | [Select values](/author/values) | How one value is read, computed and narrowed. |
| 04 | [Set the grain](/author/grain) | What one row means after filter, join, group, union and unnest. |
| 05 | [Project rows](/author/projections) | Which grain gets a name and typed outputs. |
| 06 | [Declare topology](/author/topology) | What a node or edge means, carries and points at. |
| 07 | [Bind records](/author/bindings) | Which row produces which record, and what identifies it. |
| 08 | [Declare meaning](/author/meaning) | Which claims, frames and purpose travel with the graph. |
| 09 | [Generate declarations](/author/generation) | How an inert contract produces owned source. |

## Pages

Before the first declaration, read [Philosophy](/philosophy/index); it states the order these pages assume. The [subject map](/subjects/index) shows the same ideas from guide, spec, API, philosophy and review views. Start at [Declare an asset](/author/assets) and follow the numbers. Each page opens with the object it owns, then its rules, one valid example, its limits and the next decision.

## Next

[Declare an asset](/author/assets) — the logical source every table names.
