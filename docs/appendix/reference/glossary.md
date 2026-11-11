---
title: Glossary
summary: Terms that look alike in kg-build-system, and the distinction that changes a decision.
section: reference
order: 50
status: normative
verified: 2026-11-10
sources:
  - docs/appendix/developer/system-design.md
  - docs/appendix/reference/glossary.md
  - kg_build_system/kernel/model/public/workflow.py
  - kg_build_system/distribution/languages/
  - kg_build_system/distribution/modules/
---

Many names in the framework are adjacent, not synonymous. The table gives the one-line distinction; follow the links for the document shape or the stage where the term does its work.

## Surface

| Term | Distinction |
| --- | --- |
| Declaration vs symbol | A declaration is an authoring object a language offers; a symbol is a linked, keyed unit reached from a root. Only reachable declarations become symbols. |
| Key vs symbol ref | A key is a language-owned tuple of string segments; a symbol ref is `(language, key)`. A document reference adds the role token in front. |
| Blueprint vs symbol graph | The blueprint is the delivered semantic model of graph, data, assets and bindings; the symbol graph is the linker's working index of keys, kinds and references. |
| Plan vs instruction | A plan is components, steps, connections and provenance; an instruction is one step's opaque `(kind, payload)` pair. |
| Component vs module | A component is a planner group in a plan, with an id, version and runtime fields; a module is a distribution package that contributes planners, executors and resources. |
| Planner vs executor | A planner reads the blueprint and emits steps; an executor owns one exact instruction kind and runs those steps. |
| Artifact type vs pattern | An artifact type is a concrete key; a pattern is an input key with `*` and `**` matching. |
| Publication vs output | An output is a step port that must be consumed downstream; a publication is an output that is also a final artifact and appears in the workflow report. |
| Asset vs table | An asset is a logical source-data unit; a table is a logical relation with columns and one asset. Several tables may name one asset. |
| Projection vs row source | A projection is a named logical row product with computed fields; a row source is any value that produces rows of a known shape. A projection is also a row source. |
| Selection vs field | A field is a declared typed member; a selection is the authoring value that navigates a row, calculates a value and owns absence. |
| Semantics vs graph semantics | Semantics is a declaration fragment of claims and frames; graph semantics is the project root with claims and exactly one purpose. |
| Annotation vs description | An annotation is portable `(namespace, id, arguments)` metadata preserved without interpretation; a description is a plain human string. |
| Nullable vs optional | Nullable is a value type that may be absent at run time; optional is a document member the codec may omit. The codec writes an absent nullable value as `null` or omits the member, member by member. |
| Dedup vs merge | Dedup removes exact duplicate graph records with `DISTINCT`; merge combines same-key compatible facts into one record. |
| Conflict validation vs merge | Conflict validation reports same-key non-null contradictions; merge reconciles same-key facts and does not diagnose contradictions. |
| Source planner vs module | A source planner emits source-relation steps for asset-backed tables; a module is the package that contributes that planner with related executors and resources. |
| Generation vs build | Generation writes declaration source from asset contracts at edit time; a build links declarations, compiles a plan and executes it to records. |

## Details

The distinction that matters most is **document identity versus runtime identity**. A key, a symbol ref and a document ref all identify a declaration, but only the symbol ref is resolved by the linker; the document ref is a stored pointer. [Documents](/appendix/reference/documents) fixes the stored form, and [Link](/book/part-3/01-linking-and-blueprint) fixes the resolution order.

The second distinction is **value presence versus member presence**. Nullable belongs to a selection or logical type. Optional belongs to a codec: the member may be absent from the JSON object. The blueprint codec is deliberately asymmetric: `graph_declaration` is omitted when absent, binding `rows` is explicit `null`, and topology `parent`, `description` and `semantics` are omitted. Use [Documents](/appendix/reference/documents) for the full table.

The third distinction is **wiring versus execution**. A plan fixes steps and connections; an instruction is opaque until an executor claims its exact kind. A component id names the planner group, while a module is the package that ships it. Use [Plan](/book/part-3/02-planning) for assembly and [Execute](/book/part-3/03-execution-and-outputs) for the run.

For the names exported by the facade, use [API surface](/appendix/reference/api). For the command that writes declarations before a build, use [CLI](/appendix/reference/cli).
