---
title: CLI
summary: The console commands for checking, building, compiling, running, generating and viewing a project, and their flags and exit codes.
section: reference
order: 20
status: normative
verified: 2026-11-18
sources:
  - pyproject.toml
  - kg_build_system/cli/service/_private/main.py
  - kg_build_system/cli/service/_private/init.py
  - kg_build_system/cli/service/_private/manifest_command.py
  - kg_build_system/cli/service/_private/view.py
subject: generation
perspective: reference
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Source generation and CLI</span><a href="/appendix/subjects/generation">Overview</a><a href="/book/part-2/09-generation">Guide</a><a href="/appendix/spec/generation">Spec</a><a href="/appendix/reference/api">API</a><a href="/appendix/philosophy/explainability-is-authored">Philosophy</a><a href="/appendix/review/limits">Review</a></div>
<!-- END GENERATED:views -->

## Surface

`kbs` is the console entry point for a project. It finds the manifest's
`Blueprint` and `Workflow` values by type; importing the manifest builds nothing.
`compile` and `execute` remain available as Python calls.

| Command | Job |
| --- | --- |
| `kbs init [PATH] [--fixture]` | Write an empty project (or the conformance example with `--fixture`) into an empty directory, point its `pyproject.toml` at the framework, and create the notebook. Refuses a non-empty directory unless `--force` is passed. |
| `kbs check --project PATH` | Read the blueprint and print the authored semantic argument: graph purpose, records, relations, bindings and review notes. It is a reading report, not a proof; the project's tests remain the gate. |
| `kbs blueprint --project PATH [--output PATH]` | Build and print, or write, the blueprint document. |
| `kbs workflow --project PATH [--output PATH]` | Compile and print, or write, the workflow-plan document. |
| `kbs run --project PATH [--output-directory PATH]` | Compile and execute; exit `0` when the report succeeds and `1` otherwise. |
| `kbs generate ...` | Generate or check edit-time declaration products. |
| `kbs view ...` | Serve the bundled design viewer for a plan, blueprint or snapshot. |

The project notebook and console are a separate surface: [Project notebook and console](/appendix/reference/notebook).

## `kbs generate`

```console
kbs generate --project .
kbs generate --project . --check
kbs generate --project . --regenerate
kbs generate --project . --check --regenerate
kbs generate --project . --watch --debounce 500
```

| Flag | Effect |
| --- | --- |
| `--project PATH` | Project directory to scan or watch; defaults to the current directory. |
| `--check` | Compare products with requests and ownership records without writing. Does not re-observe sources. |
| `--regenerate` | Re-observe every source and regenerate every product, including products that are current. |
| `--watch` | Run one pass, then watch project files and regenerate on declaration changes. |
| `--debounce MS` | Watch debounce in milliseconds; defaults to `300` and must be greater than zero when watching. |

| Exit code | Meaning |
| --- | --- |
| `0` | `CURRENT` or `CHANGED`; also a watch or view session stopped with Ctrl+C. |
| `1` | `STALE` or a generation failure. |
| `2` | Usage error, including a refused flag combination. |

## `kbs view`

`kbs view` serves the bundled design viewer for one project artifact. A wheel
ships the static viewer build under `kg_build_system/viewer_dist`; a source
checkout serves `viewer/design/out`. The command starts one local HTTP server:
the viewer at `/`, the snapshot at `/snapshot`, and opens the viewer. Node is not
required at runtime.

| Flag | Effect |
| --- | --- |
| `--snapshot PATH` | Workflow plan, blueprint, viewer snapshot or gzip of one. Defaults to `build/workflow_plan.json`. |
| `--title TEXT` | Display title for a bare workflow plan or blueprint. |
| `--host ADDRESS` | Bind address; defaults to `127.0.0.1`. |
| `--port PORT` | Port to serve on; defaults to `8001`, or `8000` in dev mode. |
| `--no-open` | Do not open a browser. |
| `--dev` | Run the viewer command from the framework `.env` and reverse-proxy it; the default port is 8000. |

`kbs view` serves the snapshot at `/snapshot`. It never falls back to a bundled
sample: with no `--snapshot` and no `build/workflow_plan.json`, it exits with an
error and asks for a plan.

The command does not start Next and knows nothing about the viewer source.
`--dev` is the framework-maintainer path: the untracked `.env` at the framework
repo root supplies `KBS_DEV_VIEWER` and `KBS_DEV_CONSOLE`, each command prints
its port on the first line, and `kbs` proxies the dev UI while serving the
snapshot itself.

The wheel build compiles the viewer with `npm ci` and `npm run build:static`.
`KBS_SKIP_VIEWER_BUILD=1` uses an existing `viewer/design/out`, `KBS_SKIP_VIEWER_INSTALL=1`
reuses `viewer/node_modules`, and `KBS_NPM` selects an npm executable.

`compile` and `execute` are Python calls, not console commands. Use `compile` to turn a blueprint into a plan and `execute` to run it; the calls are listed on [API surface](/appendix/reference/api) and walked through on [Generation](/book/part-2/09-generation).

## Details

`kbs generate` runs one desired-state pass over every discovered request. It writes declaration source; it does not read graph data, compile a plan or execute a build. The project layout it scans is described on [Project](/book/part-1/03-a-project).

`--check` performs the full comparison without mutation. It exits `0` for `CURRENT` and `CHANGED`, and `1` for `STALE` or a generation failure. `--check` alone does not observe sources, so a changed source schema is not visible to it.

`--regenerate` forces every provider to observe its source again before the pass. Alone, it rewrites products. Combined with `--check`, it reports source-schema drift as `STALE` without writing.

`--watch` runs one complete pass, then watches project files and regenerates on declaration changes. It cannot be combined with `--check` or `--regenerate`; the source refuses both combinations:

```text
--watch and --check cannot be combined
--regenerate is a single re-observation pass and cannot be combined with --watch
```

The command writes log lines to standard output with a timestamp, level and message. A failed single pass logs the generation error and returns `1`; a failed initial watch pass is logged before the watcher starts. A watch session catches Ctrl+C and returns `0`; an invalid edit during a watched pass is logged without stopping the watcher.

The absence of a build command is deliberate: a build is a composition of public Python calls, not a CLI mode. For the command that produces records, read [Execute](/book/part-3/03-execution-and-outputs); for the command that writes declarations, read [Generation](/book/part-2/09-generation).
