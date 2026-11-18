---
title: Appendix B · Reference
summary: The exact public names, CLI command, document shapes, failure catalogue and vocabulary.
section: reference
order: 0
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/__init__.py
  - kg_build_system/cli/
  - docs/content/appendix/reference/
---

<div class="kb-section-head">
  <p class="kb-kicker">Appendix B · Reference</p>
  <p class="kb-lede">Look things up after the book has given you the model. Signatures are exact; examples are small; the API table is generated from the lazy facade.</p>
</div>

## In this section

| Page | Lookup |
| --- | --- |
| [API surface](/appendix/reference/api) | Every name exported by `kg_build_system`, grouped by import. |
| [CLI](/appendix/reference/cli) | `kbs generate`, its flags and exit codes. |
| [Documents](/appendix/reference/documents) | Blueprint, plan and report shapes; omit versus null; provenance. |
| [Declarations](/appendix/reference/declarations) | SourceRelation, DerivedRelation, Stage, Struct, Field and the constructors. |
| [Assets](/appendix/reference/assets) | Asset options, layout, profile, governance and SourceRelation[Asset]. |
| [Types](/appendix/reference/types) | Canonical types, nullability, property shape and DuckDB dispositions. |
| [Expressions](/appendix/reference/expressions) | The Selection surface, row effects, operations and errors. |
| [Row sources](/appendix/reference/row-sources) | row_source, where, join, group_by, union, distinct, order_by and unnest. |
| [Extension](/appendix/reference/extension) | Project-local value operations, relation operations, source adapters and the kernel protocols. |
| [Project notebook and console](/appendix/reference/kgkit) | The kgkit notebook, revision timeline and separate console that embeds the design viewer. |
| [Derived relations](/appendix/reference/derived-relations) | Contracts, pinned sources, computed fields, stages and outputs. |
| [Topology](/appendix/reference/topology) | Node, Edge, properties, templates, categories and endpoints. |
| [Bindings](/appendix/reference/bindings) | node_binding, edge_binding, fulfilment, keys, properties and endpoints. |
| [Annotations](/appendix/reference/annotations) | Annotation, NodeLabel, EdgeLabel, displayed meaning text and label rules. |
| [Compile and execute](/appendix/reference/compile) | create_blueprint, compile, execute, plan and report. |
| [Planners and executors](/appendix/reference/planners-and-executors) | Supplied planners, executors, configuration and kinds. |
| [Ingest](/appendix/reference/ingest) | AssetLayout, the generic source planner and source checks. |
| [Generation](/appendix/reference/generation) | @asset_generation, providers, discovery and ownership. |
| [Failures](/appendix/reference/failures) | Error messages by stage, with the first place to look. |
| [Glossary](/appendix/reference/glossary) | Terms that look alike and the distinction that matters. |
| [Migration](/appendix/reference/migration) | Old docs page → KB destination, redirects and the replacement plan. |

## Pages

Use [API surface](/appendix/reference/api) for names, [Documents](/appendix/reference/documents) for stored shapes and [Failures](/appendix/reference/failures) for a message. The exact authoring pages start at [Declarations](/appendix/reference/declarations); [Migration](/appendix/reference/migration) maps the old docs to this reference. [Glossary](/appendix/reference/glossary) resolves vocabulary before a review.

## Next

[API surface](/appendix/reference/api) — the public names, grouped as the package groups them.
