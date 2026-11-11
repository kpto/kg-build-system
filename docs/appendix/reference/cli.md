---
title: CLI
summary: The sole console command, its flags and exit codes, and the Python calls that replace a build command.
section: reference
order: 20
status: normative
verified: 2026-11-11
sources:
  - pyproject.toml
  - kg_build_system/cli/service/_private/main.py
  - kg_build_system/generation/code_generation/service/_private/command.py
  - kg_build_system/generation/code_generation/model/public/results.py
  - kg_build_system/generation/code_generation/service/_private/watcher.py
subject: generation
perspective: reference
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Source generation and CLI</span><a href="/appendix/subjects/generation">Overview</a><a href="/book/part-2/07-generation">Guide</a><a href="/appendix/spec/generation">Spec</a><a href="/appendix/reference/api">API</a><a href="/appendix/philosophy/explainability-is-authored">Philosophy</a><a href="/appendix/review/limits">Review</a></div>
<!-- END GENERATED:views -->

`kbs` is a console script for edit-time declaration generation. Its only command is `kbs generate`. There is no build, run, validate or version command.

## Surface

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
| `0` | `CURRENT` or `CHANGED`; also a watch session stopped with Ctrl+C. |
| `1` | `STALE` or a generation failure. |
| `2` | Usage error, including a refused flag combination. |

`compile` and `execute` are Python calls, not console commands. Use `compile` to turn a blueprint into a plan and `execute` to run it; the calls are listed on [API surface](/appendix/reference/api) and walked through on [Generation](/book/part-2/07-generation).

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

The absence of a build command is deliberate: a build is a composition of public Python calls, not a CLI mode. For the command that produces records, read [Execute](/book/part-3/03-execution-and-outputs); for the command that writes declarations, read [Generation](/book/part-2/07-generation).
