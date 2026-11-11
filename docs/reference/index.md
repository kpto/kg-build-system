---
title: Reference
summary: The exact public names, CLI command, document shapes, failure catalogue and vocabulary.
section: reference
order: 0
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/__init__.py
  - kg_build_system/cli/
  - docs/reference/
---

<div class="kb-section-head">
  <p class="kb-kicker">06 · Reference</p>
  <p class="kb-lede">Look things up here after the concept pages have given you the model. Signatures are exact; examples are small; the API table is generated from the lazy facade.</p>
</div>

## In this section

| Page | Lookup |
| --- | --- |
| [API surface](/reference/api) | Every name exported by `kg_build_system`, grouped by import. |
| [CLI](/reference/cli) | `kbs generate`, its flags and exit codes. |
| [Documents](/reference/documents) | Blueprint, plan and report shapes; omit versus null; provenance. |
| [Declarations](/reference/declarations) | Table, Struct, Field and the constructors. |
| [Assets](/reference/assets) | Asset options, layout, profile, governance and Table[Asset]. |
| [Types](/reference/types) | Canonical types, nullability, property shape and DuckDB dispositions. |
| [Expressions](/reference/expressions) | The Selection surface, row effects, operations and errors. |
| [Row sources](/reference/row-sources) | row_source, where, join, group_by, union, distinct, order_by and unnest. |
| [Projections](/reference/projections) | Pinned sources, computed fields and outputs. |
| [Topology](/reference/topology) | Node, Edge, properties, templates, categories and endpoints. |
| [Bindings](/reference/bindings) | node_binding, edge_binding, keys, properties and endpoints. |
| [Semantics](/reference/semantics) | Claim, Frame, Limitation, Purpose, Semantics and GraphSemantics. |
| [Compile and execute](/reference/compile) | create_blueprint, compile, execute, plan and report. |
| [Planners and executors](/reference/planners-and-executors) | Supplied planners, executors, configuration and kinds. |
| [Ingest](/reference/ingest) | AssetLayout, the generic source planner and source checks. |
| [Generation](/reference/generation) | @asset_contract, providers, discovery and ownership. |
| [Failures](/reference/failures) | Error messages by stage, with the first place to look. |
| [Glossary](/reference/glossary) | Terms that look alike and the distinction that matters. |
| [Migration](/reference/migration) | Old docs page → KB destination, redirects and the replacement plan. |

## Pages

Use [API surface](/reference/api) for names, [Documents](/reference/documents) for stored shapes and [Failures](/reference/failures) for a message. The exact authoring pages start at [Declarations](/reference/declarations); [Migration](/reference/migration) maps the old docs to this reference. [Glossary](/reference/glossary) resolves vocabulary before a review.

## Next

[API surface](/reference/api) — the public names, grouped as the package groups them.
