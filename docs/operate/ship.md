---
title: Ship a build
summary: Test the public calls, run the manual checks, tune runtime configuration and compose one namespace.
section: operate
order: 50
status: normative
verified: 2026-11-11
sources:
  - reference_project/build.py
  - tests/test_reference_build.py
  - pyproject.toml
  - kg_build_system/kernel/model/public/runtime.py
  - kg_build_system/api.py
---

> [!lede]
> A shipped build is a test suite, a repeated command and one configuration. The repository defines no CI job, so every gate is a command you run.

## What it is

| Gate | Command | Proves |
| --- | --- | --- |
| Sync | `uv sync` | Locked runtime and development dependencies |
| Test | `uv run pytest` | Plan shape, report and published artifacts |
| Types | `uv run pyright` | Annotated public surface |
| Reference build | `uv run python -m reference_project.build` | End-to-end wiring and files |
| CI | All of the above | A passing job; no configuration is checked in |

Install first: [Install and verify](/start/install). Execution and report mechanics are in [Execute a plan](/pipeline/execute).

## Rules

- The public path is the test surface. Declare a module, call `create_blueprint` and `compile`, and assert `plan.components`, `plan.steps` and `plan.connections`.
- For the data layer, execute into a temporary directory and assert `report.succeeded`, the artifact types and the files. There is no fixture kit.
- `create_blueprint` and `compile` read no data. Keep declaration and wiring tests independent of source files.
- The CI script is `uv sync`, then `pytest`, then `pyright`, then the reference project build. The repository has no CI configuration; every check is manual.
- Tune with `RuntimeConfiguration`. `component_configuration` is keyed by plan component and validated against that component's `runtime_fields`. `provider_configuration` is keyed by provider; the `duckdb` provider reads `storage` (`memory` or `disk`), `threads`, `memory_limit` and `compression`.
- Compose projects in one namespace. Import shared declarations; there is no merge command. `create_blueprint(bindings=...)` takes explicit binding values and adds the implied tables and assets.
- There is no schema migration or plan compatibility promise. Recompile when declarations or planners change.
- Pin the framework checkout, Python 3.12 or later and `uv.lock`. A report and its artifacts belong to one plan and one output directory.

## Example

```yaml
name: build
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync
      - run: uv run pytest
      - run: uv run pyright
      - run: uv run python -m reference_project.build
```

Tune the same run through runtime configuration:

```python
from pathlib import Path

from kg_build_system.kernel import RuntimeConfiguration

configuration = RuntimeConfiguration(
    output_directory=Path("build"),
    working_directory=Path("build/_workdir"),
    component_configuration={
        "file": {"relative_path": "graph/current.jsonl"},
    },
    provider_configuration={
        "duckdb": {
            "storage": "disk",
            "threads": 4,
            "memory_limit": "8GiB",
            "compression": True,
        },
    },
)
```

The `kg_build_system.execute` shortcut builds this value from `BuildRuntime`; pass `runtime=BuildRuntime(...)` there, or hand `configuration` to `Toolchain.execute`.

## Limits

- There is no CI configuration, build subcommand or release pipeline in the repository. A job is a script you write around the public calls.
- Tests are ordinary Python. The framework supplies no fixtures, snapshots or record assertions.
- There is no incremental build or cache. Every execution runs the whole plan and rewrites its outputs.
- `component_configuration` cannot name a component outside the plan; an unknown key raises. Provider settings are read by the provider, not checked by the kernel.
- One build has one namespace, one plan and one output directory. There is no project merge and no combined report.
- Plans and schemas carry no compatibility promise. A changed declaration or planner requires a new compile.
- The evidence behind these checks is in [Verification](/review/verification); CLI scope is in [CLI](/reference/cli).

## Next

[Verification](/review/verification) — what this checkout measured and where the docs differ.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-036 | Require a rule-promotion check at the end of every change. | 2026-10-29 | accepted | `AGENTS.md#rule-promotion` |
| D-039 | Guard the architecture with a contract test and a reviewer briefing. | 2026-11-02 | accepted | `tests/test_architecture.py` |
