---
title: "17. Shipping a build"
summary: "What a shipworthy build contains, what to pin, and what the measured checkout does not promise."
section: book
perspective: book
part: III
chapter: 17
order: 35
status: normative
verified: 2026-11-11
sources:
  - docs/content/book/part-3/05-shipping.md
  - docs/content/appendix/review/verification.md
  - docs/content/appendix/review/limits.md
  - tests/test_reference_build.py
  - reference_project/build.py
---

A build that exists on one machine is an experiment. A build that ships is a bundle another person can inspect, re-run and judge: the declarations at a known revision, the dependency lock, the plan, the artifacts, the report that lists them, the commands that were run, and a statement of what the build does not guarantee.

The graph file alone is not that bundle. `graph.jsonl` carries records, but it does not carry the declarations that named their components, the plan that produced them, the source data they were read from, or the reason a merge chose one value. It is an output. Shipping the output without the procedure makes every later question unanswerable.

## A build moves as a bundle, not as a file

Six parts make a build reviewable.

- **Source.** The declaration namespace at a known revision, with its Python version and dependency lock.
- **A plan.** The compiled steps, connections, components and provenance that turn the declarations into work.
- **Published artifacts.** The files and in-memory publications the run produced, named by the report.
- **A report.** The run's published artifacts, recovered and unresolved failures, and provenance.
- **Tests and commands.** The checks that were run, and the result each one reported.
- **Known limits.** The boundaries the build does not cross, stated where a consumer meets them.

The rest of this chapter takes those six in turn, then states what to pin and what to re-run when one of them changes.

## Source is reproducible only when the inputs are pinned

Declarations are Python values discovered from a namespace. `create_blueprint(namespace_path=...)` imports the project, indexes its declarations and links the reference closure. The blueprint therefore depends on the project source at a revision, the framework checkout that interprets it, the Python version and the resolved dependencies.

Pin all four. The repository declares Python 3.12 or later and commits `uv.lock`; `uv sync` installs the locked set, and `uv run` executes inside it. Pin the framework at a commit rather than a branch. The package version `0.1.0` is not a compatibility promise: the API is experimental and breaking changes are expected.

Project composition is one namespace. `create_blueprint` accepts either a namespace path or explicit binding values, never both, and the linker refuses more than one reached graph declaration. Shared declarations are imported into that namespace; there is no merge command and no combined report for two projects. A shipped build names one namespace and at most one graph declaration.

Source data is the part the framework does not pin. The toolchain has no download or ingest step, and the blueprint records an asset's declared identity, version and layout but does not verify that the files it resolves match that declaration. There is no content hash. Two runs of the same plan against a moved or updated source produce different records and the same plan. Pinning the source release, the storage location and, where possible, the file content is the shipper's job. The build can describe its provenance only as far as the declarations and the plan go.

Execution is not incremental. Every run executes the whole plan and rewrites its outputs; there is no cache or partial publish. That makes a run simple to reason about and expensive to repeat, and it means a stale artifact is never silently reused.

## The plan states the work; the report states the run

A `WorkflowPlan` holds components, steps, connections and provenance. A component publishes a planner group's id, version and runtime fields. A step has a component and name, typed input and output openings, and one instruction with an exact kind. A connection resolves one output opening to one input opening. Assembly has already checked that every input is fed and every ordinary output is read.

`compile` also records the source blueprint document at `plan.provenance["blueprint"]`. A serialized plan therefore carries the semantic model that produced it. That is the strongest provenance the framework offers: a reader can see the graph declaration, topology, data, assets and bindings behind the wiring.

The plan does not carry runtime values, credentials, provider settings or source data. `execute` writes `workflow_plan.json` before the run starts, so the plan document exists even when the run fails. Runtime configuration is an execution input keyed by plan component and provider: an unknown component key is refused before the first step, and a component's declared fields are validated before that component's step runs. None of it is part of the plan.

This split gives the shipping rule its shape. A declaration or planner change makes the plan stale, so compile again. A runtime or source-data change leaves the plan intact but makes the report stale, so execute again. A report and its artifacts belong to one plan and one output directory; copying an artifact into another run's directory breaks that pairing.

A plan is executable only where an executor claims every exact instruction kind it names. Shipping a plan to another checkout means shipping a checkout with the same executors, or recompiling there. There is no plan compatibility negotiation and no migration path.

## Artifacts are publications, not proof

The report lists publications, not every intermediate artifact. `published_artifacts` holds the values a run handed to the build itself: the file write summary, the meta-graph document, the Neo4j import bundle and, when conflict validation found something, the conflict report. Ordinary graph-record outputs stay inside the run.

The file target writes one JSON object per line for every graph record it receives. A node record carries `build_key`, `type`, `kind` and the declared properties. An edge also carries `source_build_key` and `target_build_key`. A record that has not passed through a merging step also carries `_kg_binding_symbol`; a merged record does not, because the merge select omits it. Property keys are sorted. The whole file is rewritten on every run.

The meta-graph target writes a JSON description of the effective topology, with per-component counts and approximate property examples, and optionally a self-contained HTML page. Its counts are exact for the records that reached its executor and say nothing about records that were filtered out earlier. The examples are approximate by construction and the document names the method.

Neo4j is export only. The executor writes Parquet files under `nodes/` and `relationships/`, a standalone `import_neo4j.py` and a summary. The script invokes `neo4j-admin database import` and needs neither the framework nor a network at run time. No driver, Cypher session or live database is opened.

None of these targets validates. The file target writes what it receives, the meta-graph describes what reached it, and Neo4j exports what it was given. An edge whose endpoints match no node is exported and fails later at import. Quality is an upstream decision, made by the planners composed before the targets and by the checks a project adds itself.

Artifact presence is therefore evidence of publication, not of correctness. The shipping question is not "did the target write a file?" but "which planner composed the stream that the target wrote, and what does that planner guarantee?" Chapter 16 states those guarantees; the bundle repeats them as limits.

## The test suite guards interfaces, not the graph

The checkout measures itself. A run of `uv run pytest -q` on 2026-11-15 reports 393 tests and 1,972 subtests passing in about 7 seconds. `uv run pyright` reports no errors. The repository has no CI configuration; every check is a command someone runs.

Those numbers are properties of the checkout, not promises about the next one. A test count, subtest count or duration varies with the machine and dependency versions. The stable claims are the pass or fail result and the measured type state. Quoting 363 and 1,957 is honest only with the date and the command; quoting them as a guarantee is not.

What the suite guards is worth stating precisely, because a green run is often asked to prove more than it can.

| Group | Guards |
| --- | --- |
| Kernel flow | Build, link, compile and execute with fake languages, planners, executors and runtime |
| Pipeline identity | Step ids, openings, artifact types, instruction kinds and duplicate identities |
| Planner and executor contracts | Component ownership, exact kinds, declared resources and step outcomes |
| Distribution and DTOs | Typed refs, linker order, codecs and blueprint source round trips |
| Reference build | The public path composes and writes real artifacts |
| Guards | Import isolation, package architecture, facades and public docstrings |
| Typecheck | The authoring surface and its refusals in two fixtures |

The reference build is the integration proof: it creates a blueprint, compiles it, executes it into a temporary directory and asserts the report, the three publication types and the files. The kernel flow tests use fakes and never import the distribution, which is how the domain-agnostic boundary is proved rather than asserted.

A project's own tests follow the same two levels. For the plan, declare a module, call `create_blueprint`, compile with the project's planner tuple and assert the components, step ids and connections the project depends on. For the data layer, execute into a temporary directory and assert `report.succeeded`, the publication types and the files. Keep declaration and wiring tests independent of source files: `create_blueprint` and `compile` read no data, so a test that needs a source file belongs to the execution level. There is no fixture kit, and the assertions are ordinary Python.

The suite does not measure line or branch coverage. It does not prove grain, duplicate keys, dangling edges or the correctness of a merge. Pyright analyses `kg_build_system` and two authoring fixtures, not `tests/`, `reference_project/` or `legacy/`. The public docstring test requires an `Example` section but does not execute it.

The Open Targets suite is external evidence. It runs in another checkout and is not a check on this repository. The seven tests there say something about that project, not about this one.

The practical consequence is that the shipping gate is a sequence of commands, not a badge:

```console
uv sync
uv run pytest -q
uv run pyright
uv run python -m reference_project.build
```

The only console command is `kbs generate`; it writes declaration source and does not build. `compile` and `execute` are Python calls, so the script that sequences a build is part of the project source and belongs in the bundle.

The reference build writes `graph.jsonl`, `meta_graph.json`, `meta_graph.html`, `neo4j-import/`, `workflow_plan.json` and `build_report.json` under `reference_project/build` and publishes no intermediate core records. Wrapping those commands in CI is a reasonable delivery choice, but the repository does not supply that configuration and the documentation must not claim it does.

## Known limits travel with the build

A shipped build should say what it does not promise. Four limits matter to a consumer more than the rest.

There is no schema version and no compatibility negotiation. Blueprint and plan documents have no version envelope, codecs refuse unknown fields, and a changed document shape is read by the matching checkout rather than migrated. There is no migration path from an older plan, blueprint or report. Recompile and re-execute when the framework changes.

The API is experimental. Breaking changes are expected. A consumer that imports internal modules, rather than the public names in the composition root, has no boundary to rely on.

There is no incremental build and no cache. A run is all or nothing over the whole plan, and its outputs are rewritten. A build that must preserve an earlier result keeps its own copy of the output directory.

Scale is unmeasured. A graph of 5.9 million annotations is unproven at that size; the reference build is a wiring proof, not a benchmark. A consumer planning a large run should measure on its own data rather than infer a capacity from the reference counts.

Add the boundaries that apply to the project: no built-in licence filter, no network acquisition step, no Python execution isolation or per-step timeout. Each is a real limit with a named extension point. Stating them in the bundle is cheaper than discovering them after a consumer relies on the opposite.

## What to pin and what to re-run

Pinning is the act of naming the inputs a result depends on. Re-running is the act of regenerating the result after one of them changes. The two belong together; a pinned input with a stale output is as misleading as an unpinned one.

| Change | What becomes stale | What to run |
| --- | --- | --- |
| A declaration, binding or derived relation | Blueprint and plan | `compile`, `execute`, the full test suite |
| A planner or executor | The plan for a planner change; the execution set for an executor change | `compile` for a planner, `execute` for an executor, the matching contract tests |
| Runtime configuration | The run and its report | `execute` into a fresh output directory |
| Source data | The records and the report | `execute`; re-check counts and keys |
| Framework checkout | Everything | `uv sync`, pytest, pyright, the reference build |
| A stored document consumer | Document compatibility | The codec round trip for that document |

Two rules keep the table honest. First, never patch an artifact or a report by hand; regenerate it from the plan and the source. A hand-edited report no longer describes a run. Second, keep one output directory per run and do not mix artifacts from two runs. The report's provenance and the files beside it are a single pairing.

A ship record can then be short and checkable:

| Part | Evidence | What it does not prove |
| --- | --- | --- |
| Source | Project revision, Python version, `uv.lock` | That the source data is unchanged |
| Plan | `workflow_plan.json`, blueprint provenance | That the plan is correct for the data |
| Artifacts | `published_artifacts` and the files they name | That the records are true |
| Report | `succeeded`, failure tuples, provenance | That every step succeeded |
| Tests | The commands and their measured result | Grain, keys or dangling edges |
| Limits | The stated boundaries and their refusals | That a limit is harmless |

The record does not claim a guarantee the checkout does not make. It claims that the procedure is reproducible, that the evidence is present, and that the boundaries are named.

## Shipping is a procedure, not a verdict

A build is shipworthy when another person can take the source revision, the lock, the plan and the commands, reproduce the run, and compare the result with the report. Correctness is a separate question, answered by the declarations, the quality planners, the tests a project writes and the checks a consumer runs.

That separation is the point. The framework can prove that the plan assembled, that every step found an executor, that the run returned and that the published artifacts were recorded. It cannot prove that the graph says what the author meant. Shipping well means refusing to blur the two: state what was measured, state what was not, and hand over the artifacts that let the next person measure again.

## Next

[Part IV — Extending and reviewing](/book/part-4/index) — move from running the default distribution to judging its kernel, its extensions and its evidence.
