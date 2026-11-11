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
| `docs/philosophy/index.md` | /philosophy/index | Rewrite |
| `docs/start/install.md` | /start/install | Rewrite |
| `docs/start/first-graph.md` | /start/walkthrough | Rewrite |
| `docs/start/project-layout.md` | /start/project | Rewrite |
| `docs/author/index.md` | /pipeline/index | Rewrite |
| `docs/author/data-contracts.md` | /author/data | Rewrite |
| `docs/author/data.md` | /reference/types | Rewrite |
| `docs/author/assets.md` | /author/assets | Rewrite |
| `docs/author/expressions.md` | /author/values | Rewrite |
| `docs/author/grain.md` | /author/grain | Rewrite |
| `docs/author/projections.md` | /author/projections | Rewrite |
| `docs/author/topology.md` | /author/topology | Rewrite |
| `docs/author/bindings.md` | /author/bindings | Rewrite |
| `docs/author/meaning.md` | /author/meaning | Rewrite |
| `docs/author/meaning.md` | /author/meaning | Redirect |
| `docs/author/planners-and-executors.md` | /operate/outputs | Rewrite |
| `docs/pipeline/execute.md` | /pipeline/execute | Rewrite |
| `docs/operate/relations.md` | /author/grain | Redirect |
| `docs/operate/custom-extensions.md` | /operate/extend | Rewrite |
| `docs/operate/debug.md` | /operate/debug | Rewrite |
| `docs/operate/patterns.md` | /philosophy/anti-patterns | Rewrite |
| `docs/developer/index.md` | /developer/index | Rewrite |
| `docs/developer/philosophy.md` | /developer/philosophy | Rewrite |
| `docs/developer/system-design.md` | /developer/system-design | Rewrite |
| `docs/developer/data-and-expressions.md` | /developer/data-and-expressions | Rewrite |
| `docs/developer/testing.md` | /developer/testing | Rewrite |
| `docs/reference/index.md` | /reference/index | Rewrite |
| `docs/reference/types.md` | /reference/types | Rewrite |
| `docs/reference/declarations.md` | /reference/declarations | Rewrite |
| `docs/reference/assets.md` | /reference/assets | Rewrite |
| `docs/reference/expressions.md` | /reference/expressions | Rewrite |
| `docs/reference/row-sources.md` | /reference/row-sources | Rewrite |
| `docs/reference/projections.md` | /reference/projections | Rewrite |
| `docs/reference/topology.md` | /reference/topology | Rewrite |
| `docs/reference/bindings.md` | /reference/bindings | Rewrite |
| `docs/reference/semantics.md` | /reference/semantics | Rewrite |
| `docs/reference/compile.md` | /reference/compile | Rewrite |
| `docs/reference/planners-and-executors.md` | /reference/planners-and-executors | Rewrite |
| `docs/reference/ingest.md` | /reference/ingest | Rewrite |
| `docs/reference/generation.md` | /reference/generation | Rewrite |
| `docs/reference/glossary.md` | /reference/glossary | Rewrite |
| `README.md` | / | Keep; repository entry |
| `AGENTS.md` | /developer/index | Keep; governance |
| `ARCHITECTURE.md` | /developer/system-design | Merge |
| `FRAMEWORK_STATE.md` | /review/verification | Merge |
| `DESIGN_ISSUES.md` | /review/limits | Merge |
| `specs/README.md` | /developer/index | Merge |
| `specs/semantics-and-graph.md` | /spec/meaning | Merge; exact reference at /reference/semantics |

## Details

### The replacement rule

- The KB is the source of knowledge. `docs/` becomes redirects or is deleted after parity.
- `README.md` stays as the repository entry point and links to the KB.
- `AGENTS.md` stays because it governs agents, not user knowledge.
- Public docstrings stay because `tests/test_public_docstrings.py` enforces them; the KB links to the API surface and reference.
- `ARCHITECTURE.md`, `FRAMEWORK_STATE.md`, `DESIGN_ISSUES.md` and `specs/` are merged into the KB pages above; do not keep a second copy.

### Move checklist

1. Move `kg-build-kb/content/` into `kg-build-system/docs/` (or `docs/guide/`) and keep one content root.
2. Move `scripts/kb.py`, `scripts/diagrams.py`, `quartz.config.yaml`, `package.json` and `quartz/` into the framework repository, or build the KB as a pinned release artifact with a CI drift gate.
3. Add the build gate: `uv run pytest -q`, `uv run pyright`, `python3 scripts/kb.py check`, `npx quartz build -d ../kg-build-system/docs`.
4. Install redirects for every row above. A redirect may be a static HTML page or a host rule; a bare 404 is not a replacement.
5. `README.md`, `AGENTS.md`, `STYLE.md` and the verification section are updated; the review surface is `/spec/` and `/developer/`.
6. `docs/` is the KB content and `mkdocs.yml` is removed. Keep redirects for old URLs.
7. Run `python3 scripts/kb.py check`, `npx quartz build`, `uv run pytest -q` and `uv run pyright`; record the source commit in the status block.

### What is still not automated

- Examples in guide pages are checked by hand; the source tests remain the executable truth.
- `content/spec-map.yml` names the owning spec for each source area. A changed-files CI check is the remaining automation: it should fail when a mapped source changes and its spec page does not.
- The KB is still a separate repository in this checkout. A spec that is the source of truth must move into the framework repository or be pinned by CI.

