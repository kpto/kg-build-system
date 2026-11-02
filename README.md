# kg-build-system

Declarative, typed, reproducible knowledge-graph builds.

The framework is split into a domain-agnostic `kernel`, a set of languages
(`types`, `expressions`, `table`, `topology`, `binding`), an engine
(`engines`), modules (`modules`) and a workflow runtime (`workflow`).

- The authoring surface is `from kg_build_system import ...`.
- The current architecture is `ARCHITECTURE.md`.
- Reviewer state and open design issues are `FRAMEWORK_STATE.md` and
  `DESIGN_ISSUES.md`.
- Author-facing documentation starts at `docs/index.md`; `STYLE.md` is the
  writing brief.

```console
uv run pytest -q
uv run pyright
uv run mkdocs build --strict
```

The framework is experimental; the guide describes the current model, not a
compatibility promise.
