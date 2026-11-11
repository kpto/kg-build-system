---
title: Install and verify
summary: Create one Python environment, run the test suite and prove the reference build publishes records.
section: start
order: 10
status: normative
verified: 2026-11-10
sources:
  - pyproject.toml
  - tests/test_reference_build.py
  - reference_project/build.py
---

> [!lede]
> Install the framework into one Python 3.12+ environment, run the suite, then run the reference build. If those three commands pass, the checkout is usable and the rest of this guide has a working example behind it.

## What it is

`kg-build-system` is a Python package plus a `kbs` console script. It is developed with `uv`; any PEP 517 installer works. DuckDB, `sqlglot`, `libcst`, `pydantic`, `fsspec`, `watchfiles` and `rich` are runtime dependencies.

```console
cd kg-build-system
uv sync
```

The package requires Python `>=3.12`. Node 22 is only needed to build this knowledge base, not to run the framework.

## Rules

| Check | Command | Passes when |
| --- | --- | --- |
| Test suite | `uv run pytest -q` | Every collected test passes; subtests are reported separately. |
| Static types | `uv run pyright` | The reported error count is understood before you change a public type. |
| Reference build | `uv run python -m reference_project.build` | `graph.jsonl`, `meta_graph.json`, `workflow_plan.json` and `build_report.json` exist under `reference_project/build/`. |

> [!warning] The checkout is not a release
> Counts are a property of this checkout. Run the commands before quoting them. The repository has no CI configuration, so every check is manual.

<!-- BEGIN GENERATED:status -->
| Measure | Value |
| --- | --- |
| Test suite | 354 tests, 1957 subtests, 6.83s — passes |
| Static types | 1 error |
| Source | `77f008e` (2026-11-10) |
| Docs build | `npx quartz build` runs separately in this repository |
<!-- END GENERATED:status -->

## Example

```console
uv run pytest -q
uv run pyright
uv run python -m reference_project.build
```

The reference run is the smallest proof that the public path composes: it creates a blueprint, compiles a plan, executes it and writes the selected targets.

## Limits

- `uv run pyright` reports one error in `kg_build_system/api.py`; the guide reports the measured count rather than claiming zero.
- Pyright analyses `kg_build_system` plus two authoring fixtures, not the rest of `tests/`, `reference_project/` or `legacy/`.
- The Open Targets project cited by the framework docs is external and is not run in this checkout.
- There is no incremental build, no schema migration and no plan compatibility promise.

## Next

[Run the estate build](/start/walkthrough) — the same path, declaration by declaration.
