---
title: Migration
summary: "Old docs page to KB destination, redirects and the replacement checklist."
section: reference
perspective: reference
order: 190
status: normative
verified: 2026-11-10
sources:
  - README.md
  - AGENTS.md
  - STYLE.md
  - docs/
---

## Surface

This page is the redirect and parity map for the docs replacement. `docs/` now contains this knowledge base; every old docs page has a destination, a redirect or an explicit keep decision. The repository keeps `README.md`, `AGENTS.md` and docstrings.

| Old page | Destination | Action |
| --- | --- | --- |
| `docs/index.md` | / | Rewrite |
| `docs/philosophy.md` | /appendix/philosophy/index | Rewrite |
| `docs/get-started/install.md` | /book/part-1/02-a-first-build | Rewrite |
| `docs/get-started/first-graph.md` | /book/part-1/02-a-first-build | Rewrite |
| `docs/get-started/project-layout.md` | /book/part-1/03-a-project | Rewrite |
| `docs/concepts/index.md` | /book/index | Rewrite |
| `docs/concepts/data-contracts.md` | /book/part-2/03-source-and-rows | Rewrite |
| `docs/concepts/types.md` | /appendix/reference/types | Rewrite |
| `docs/concepts/assets.md` | /book/part-2/03-source-and-rows | Rewrite |
| `docs/concepts/expressions.md` | /book/part-2/04-values-and-nullability | Rewrite |
| `docs/concepts/row-sources.md` | /book/part-2/05-grain-and-projections | Rewrite |
| `docs/concepts/projections.md` | /book/part-2/05-grain-and-projections | Rewrite |
| `docs/concepts/topology.md` | /book/part-2/02-topology | Rewrite |
| `docs/concepts/bindings.md` | /book/part-2/06-binding | Rewrite |
| `docs/concepts/semantics.md` | /book/part-2/01-meaning-and-purpose | Rewrite |
| `docs/concepts/semantics-language.md` | /book/part-2/01-meaning-and-purpose | Redirect |
| `docs/concepts/planners-and-executors.md` | /book/part-3/03-execution-and-outputs | Rewrite |
| `docs/concepts/build-and-outputs.md` | /book/part-3/03-execution-and-outputs | Rewrite |
| `docs/how-to/relations.md` | /book/part-2/05-grain-and-projections | Redirect |
| `docs/how-to/custom-extensions.md` | /book/part-4/01-the-kernel-and-extension | Rewrite |
| `docs/how-to/debug.md` | /book/part-3/04-quality-and-failure | Rewrite |
| `docs/how-to/patterns.md` | /appendix/philosophy/anti-patterns | Rewrite |
| `docs/developer/index.md` | /appendix/developer/index | Rewrite |
| `docs/developer/philosophy.md` | /appendix/developer/philosophy | Rewrite |
| `docs/developer/system-design.md` | /appendix/developer/system-design | Rewrite |
| `docs/developer/data-and-expressions.md` | /appendix/developer/data-and-expressions | Rewrite |
| `docs/developer/testing.md` | /appendix/developer/testing | Rewrite |
| `docs/reference/index.md` | /appendix/reference/index | Rewrite |
| `docs/reference/types.md` | /appendix/reference/types | Rewrite |
| `docs/reference/declarations.md` | /appendix/reference/declarations | Rewrite |
| `docs/reference/assets.md` | /appendix/reference/assets | Rewrite |
| `docs/reference/expressions.md` | /appendix/reference/expressions | Rewrite |
| `docs/reference/row-sources.md` | /appendix/reference/row-sources | Rewrite |
| `docs/reference/projections.md` | /appendix/reference/projections | Rewrite |
| `docs/reference/topology.md` | /appendix/reference/topology | Rewrite |
| `docs/reference/bindings.md` | /appendix/reference/bindings | Rewrite |
| `docs/reference/semantics.md` | /appendix/reference/semantics | Rewrite |
| `docs/reference/compile.md` | /appendix/reference/compile | Rewrite |
| `docs/reference/planners-and-executors.md` | /appendix/reference/planners-and-executors | Rewrite |
| `docs/reference/ingest.md` | /appendix/reference/ingest | Rewrite |
| `docs/reference/generation.md` | /appendix/reference/generation | Rewrite |
| `docs/reference/glossary.md` | /appendix/reference/glossary | Rewrite |
| `README.md` | / | Keep; repository entry |
| `AGENTS.md` | /appendix/developer/index | Keep; governance |
| `ARCHITECTURE.md` | /appendix/developer/system-design | Merge |
| `FRAMEWORK_STATE.md` | /appendix/review/verification | Merge |
| `DESIGN_ISSUES.md` | /appendix/review/limits | Merge |
| `specs/README.md` | /appendix/developer/index | Merge |
| `specs/semantics-and-graph.md` | /appendix/spec/meaning | Merge; exact reference at /appendix/reference/semantics |

## Details

### The replacement rule

- `docs/` is the source of knowledge. Old docs URLs become redirects to the KB.
- `README.md` stays as the repository entry point and links to the KB.
- `AGENTS.md` stays because it governs agents, not user knowledge.
- Public docstrings stay because `tests/test_public_docstrings.py` enforces them; the KB links to the API surface and reference.
- `ARCHITECTURE.md`, `FRAMEWORK_STATE.md` and `DESIGN_ISSUES.md` are merged into the KB pages above; `specs/README.md` points to the canonical developer docs and does not duplicate them.

### Replacement status

1. `docs/` is the one content root in `kg-build-system`; the builder reads it directly.
2. `scripts/kb.py`, `scripts/diagrams.py`, `quartz.config.yaml`, `package.json` and `quartz/` remain in `kg-build-kb`; it builds `../kg-build-system/docs`. Pin the builder by commit, or move it into the framework repository.
3. The build gate is `uv run pytest -q`, `uv run pyright`, `python3 scripts/kb.py check` and `npx quartz build -d ../kg-build-system/docs`.
4. Redirects for every row above are the remaining host step. A redirect may be a static HTML page or a host rule; a bare 404 is not a replacement.
5. `README.md`, `AGENTS.md`, `STYLE.md` and the verification section are updated; the review surface is the book and `/appendix/spec/`, `/appendix/developer/` and `/appendix/review/`.
6. `docs/` is the KB content and `mkdocs.yml` is removed.
7. Run `python3 scripts/kb.py check`, `npx quartz build -d ../kg-build-system/docs`, `uv run pytest -q` and `uv run pyright`; record the source commit in the status block.

### What is still not automated

- Examples in the book chapters are checked against the API; the source tests remain the executable truth.
- `docs/spec-map.yml` names the owning spec for each source area. A changed-files CI check is the remaining automation: it should fail when a mapped source changes and its spec page does not.
- The builder is still a separate repository in this checkout. The content is in the framework repository; the builder is pinned by commit or moved as one unit.
