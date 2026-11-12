# Source survey: CLI, tests, verification and the reference project

- Source: `/home/paul/Repos/kg-build-system` (read-only for this survey)
- Snapshot: branch `dev`, commit `68b569e` (`2026-11-06 18:58:29 +0000`), one commit ahead of `origin/dev`
- Workspace: `/home/paul/Repos/kg-build-kb`
- Measured on: 2026-11-09
- Counts below are from this checkout, not from the prose in `README.md` or `docs/`.

## 1. CLI

### 1.1 Entry point and call chain

`pyproject.toml` declares:

```toml
[project.scripts]
kbs = "kg_build_system.cli:main"
```

The console script and module execution reach the same function:

| Layer | File | Role |
| --- | --- | --- |
| `kbs` console script | `pyproject.toml` | Calls `kg_build_system.cli:main` |
| Package facade | `kg_build_system/cli/__init__.py` | Re-exports `main` from `service.public` |
| Module runner | `kg_build_system/cli/__main__.py` | `raise SystemExit(main())` |
| Public service facade | `kg_build_system/cli/service/public/main.py` | Thin `main(argv)` wrapper; imports `..internal` |
| Internal wrapper | `kg_build_system/cli/service/internal/main.py` | Thin wrapper; function-local import of `.._private.main` |
| Private implementation | `kg_build_system/cli/service/_private/main.py` | Argparse, logging, dispatch |
| Model zone | `kg_build_system/cli/model/__init__.py` | Empty marker; no CLI DTOs |
| Generation command | `kg_build_system/generation/code_generation/service/_private/command.py` | Registers and implements `generate` |

The CLI is 10 Python files, 132 lines. Its sole command implementation lives under `generation/`, not under `cli/`.

### 1.2 Command surface

There is exactly one subcommand, `kbs generate` (generate/check edit-time declarations); there is no `build`, `compile`, `execute`, `run`, `validate` or `version` command. With no flags it runs one desired-state pass over `--project` (default cwd) and writes changes.

Root help, observed:

```text
usage: kbs [-h] {generate} ...

positional arguments:
  {generate}
    generate  generate edit-time declaration code

options:
  -h, --help  show this help message and exit
```

`generate --help` lists only the five flags in the table below; it has no `--version`, `--verbose`, `--quiet` or output-path option.

### 1.3 Flags

| Flag | Type | Default | Semantics |
| --- | --- | --- | --- |
| `--watch` | `store_true` | `False` | Run one pass, then watch project files; cannot combine with `--check` or `--regenerate` |
| `--check` | `store_true` | `False` | Compare desired state with installed products; no writes |
| `--regenerate` | `store_true` | `False` | Force every provider to re-observe every source and regenerate every product |
| `--project PATH` | `Path` | `Path.cwd()` | Project root to discover; resolved before use |
| `--debounce MS` | `int` | `300` | Debounce in milliseconds; validated only when watch mode opens the watcher |
| `-h`, `--help` | argparse | n/a | Prints help and exits 0 |

Notes:

- `--watch` + `--check` and `--watch` + `--regenerate` are rejected in `run_generate` with `ValueError`; `main` turns that into `parser.error(...)` and exit 2.
- `--check` + `--regenerate` is allowed; it reports source-schema drift as `STALE` without writing.
- `--debounce` is ignored in one-shot mode. A value of zero or less is rejected later by `watch()` with `ValueError`.
- `--project` help says “project directory to watch” even in one-shot mode.

### 1.4 Exit codes

| Situation | Exit code | Mechanism |
| --- | --- | --- |
| Root or subcommand `--help` | 0 | argparse `SystemExit(0)` |
| `generate` result `CURRENT` | 0 | `_execute_pass` returns 0 |
| `generate` result `CHANGED` | 0 | `_execute_pass` returns 0 |
| `--check` result `STALE` | 1 | `_execute_pass` returns 1 |
| `GenerationError` or `OSError` during a pass | 1 | `_execute_pass` logs `Generation failed: ...` and returns 1 |
| Invalid `--watch`/`--check` or `--watch`/`--regenerate` combination | 2 | `ValueError` → `parser.error` → `SystemExit(2)` |
| Project path is not a directory (one-shot) | 2 | `discover` raises `ValueError`; `main` calls `parser.error` |
| Non-positive debounce in watch mode | 2 | `watch` raises `ValueError`; `main` calls `parser.error` |
| Unknown command, unknown flag, non-integer debounce | 2 | argparse error |
| Keyboard interrupt | 0 | `main` catches `KeyboardInterrupt`, logs `Stopped.` |
| Unhandled exception | process traceback; normally 1 | no catch-all |

Observed checks run against an empty temporary directory:

```text
kbs generate --project /tmp/empty              -> 0, no output
kbs generate --check --project /tmp/empty      -> 0, no output
kbs generate --check --regenerate --project /tmp/empty -> 0, no output
kbs generate --watch --check --project /tmp/empty -> 2, usage + error
kbs generate --project /tmp/missing            -> 2, usage + error
kbs nope                                       -> 2, usage + error
```

### 1.5 Output and logging

`_configure_logging` installs one handler on the `kg_build_system` logger:

- Stream: `sys.stdout`
- Level: `INFO`
- Format: `%(asctime)s %(levelname)s %(message)s`
- Date format: `%Y-%m-%dT%H:%M:%S%z`
- `propagate = False`

Consequences:

- Generation progress and errors are written to **stdout**, not stderr.
- Argparse usage and argument errors are written to stderr.
- There is no JSON output, no progress bar and no final status line.
- A `CURRENT` one-shot pass and a `CURRENT --check` pass print nothing.
- A `CHANGED` pass prints one line per created, updated or deleted path.
- A `STALE --check` pass prints one diagnostic per path at `ERROR` level and exits 1.

Message forms in `command.py`:

```text
Created/Updated/Deleted generated output <path>.
Generation failed: <message>
<path> is missing, stale, altered, or orphaned
```

Watch-mode messages: `Running initial generation pass for <root>...`, `Initial generation pass complete. Watching <root>...`, `Generation declaration {added,changed,deleted}: <id>. Processing...`.

An initial watch pass that fails does not terminate the process; it logs the failure and continues watching. Per-change failures are logged and the watcher continues. The watch command returns 0 on interrupt, even if the initial pass failed.

### 1.6 Mapping to `api.compile` / `api.execute`

There is **no** mapping from `kbs` to `compile()` or `execute()`. The CLI never imports `kg_build_system.api` and never calls the build pipeline. A grep for `compile`, `execute` or `api` in `kg_build_system/cli/**/*.py` returns no matches.

| Layer | What it calls |
| --- | --- |
| `kbs generate` | `generate(root, check=..., regenerate=...)` or `GenerationSession` |
| Build entry point | Python code calls `create_blueprint` → `compile` → `execute` |
| Reference project | `reference_project/build.py` calls the public API directly |
| Docs position | `docs/get-started/install.md`: “`kbs` is for generated contracts. Use `compile()` and `execute()` in Python for a build.” |

So `kbs` is an edit-time code-generation frontend; it is not a build CLI. Generation writes ordinary `Table[Asset]`, `Struct` and `TableGroup` declarations that a Python build later imports.

## 2. Test suite layout

### 2.1 Size and counts

- 60 Python files under `tests/`, 10,526 lines.
- 49 pytest-collected test modules (`test_*.py`).
- 350 collected tests.
- 1,957 unittest subtests.
- 6.78 s for the full suite on this checkout.
- Every collected test module uses `unittest`; none imports `pytest`.
- No `conftest.py`, no `@pytest.fixture`, no `pytest.mark` decorators, no skips or xfails in collected tests.

Counts by area, from `pytest --collect-only -q`:

| Area | Test modules | Tests | Main guard |
| --- | ---: | ---: | --- |
| `tests/kernel/` | 6 | 39 | Domain-agnostic kernel flow: languages, linker, toolchain, runtime, resources, events, import isolation |
| `tests/pipeline/` | 1 | 24 | Typed pipeline identity and plan/report codecs |
| `tests/distribution/` top-level | 13 | 145 | Language models, DTOs, semantics, codecs, source round trips, blueprint linker |
| `tests/distribution/planners/` | 7 | 35 | Core, DuckDB source, dedup/merge/conflict, multi-planner components, plan assembly |
| `tests/distribution/executors/` | 5 | 18 | DuckDB executor/resources, Python executor, toolchain execution, import isolation |
| `tests/distribution/executors/targets/` | 6 | 12 | File, meta-graph, Neo4j and conflict-report targets |
| `tests/` root guard tests | 11 | 77 | Architecture, layout, naming, facades, public API, docstrings, authoring, generation, custom operation, reference build |
| **Total** | **49** | **350** | |

`tests/typecheck/` contains 2 files and 299 lines, but is not pytest-collected because the filenames are `authoring.py` and `authoring_negative.py`, not `test_*.py`.

### 2.2 Directory map

```text
tests/
  test_*.py                 11 root guard modules: architecture, layout, naming,
                            facades, public API/docstrings, authoring, generation,
                            custom operation, reference build
  kernel/                   6 modules: kernel, toolchain flow, runtime resources,
                            runtime events, extension bundle, import isolation
  pipeline/                 test_pipeline_identity.py (typed identity contract)
  distribution/
    support.py              shared TestEstate asset fixture
    test_*.py               13 language/DTO/semantics/source/blueprint modules
    planners/               7 planner-contract modules
    executors/              5 executor/resource modules
      targets/              6 output-target modules + _support.py
  typecheck/                authoring.py and authoring_negative.py (pyright only)
```

### 2.3 What each area guards

| Area | Contract asserted |
| --- | --- |
| Kernel | `build` gives languages and a namespace to the linker; a language discovers, keys, transcribes and exposes earlier symbols; `compile` groups planners by `component_id`; duplicate step ids and unknown instruction kinds are refused; `execute` dispatches exact kinds, opens providers, builds per-executor resource views and disposes on finish/halt |
| Pipeline identity | `Key`, `StepId`, `OpeningId`, `ArtifactType`, `ArtifactPattern`, `Connection`, `WorkflowPlan` and `WorkflowReport` have unambiguous identity; dotted names, input/output collisions, wildcard placement, duplicate ids and unknown endpoints are guarded; plan and report codecs round-trip |
| Distribution languages | Declaration discovery, validation, typed references, DTO shapes, semantics preservation, source rendering and source round trips for annotations, assets, data, topology, binding, graph and semantics |
| Blueprint linker | `BlueprintLinker` implements the kernel `Linker`; it indexes declarations, resolves the authoring reference closure, transcribes each reachable declaration once and assembles one blueprint |
| Planners | Each planner receives a `GraphBlueprint`, emits only its component's steps, declares `component_id`/`version`/`runtime_fields`, and produces known artifact types; multi-planner groups must agree on version and runtime fields |
| Executors | An executor claims exact instruction kinds, declares resources, reads only its payload and returns a `StepOutcome`; a disrupted context becomes a skipped outcome |
| Targets | `FileExecutor` writes JSONL; `MetaGraphExecutor` writes JSON and optional HTML; `Neo4jExecutor` writes Parquet plus a standalone import script; `ConflictReportExecutor` reports or fails findings |
| Architecture/layout | Every leaf has a facade; zones are non-empty or absent; model public/internal never import service/private; service public never imports private; cross-package imports never enter a private zone; foreign protocols have explicit adapters |
| Naming | No `IR` suffix, no `lower` verb, DTOs live in DTO modules, plans are not DTOs, no cross-package underscore imports, removed names stay removed |
| Public API | Every `kg_build_system.__all__` name resolves; `compile` is a function, not a module; removed `kg_build_system.types` and `build` names do not import; canonical entry points are distinct |
| Public docstrings | Public functions and class methods have `Example` blocks; facade functions come from public surfaces; internal functions have developer docs. Known missing examples are allowlisted as framework defects |
| Authoring API | `Selection[T]` is the single authoring type; source reads are nullable; computed reads follow their selection; `field`/`computed_field`, pinned projections, one-shot row effects, lookup, zip and unnest behave as typed |
| Generation request | `@asset_contract` is inert, stores options on the asset, is exported from both frontends, and rejects non-assets, mismatched configs and invalid packages |
| Code generation | Discovery parses source with LibCST without importing the project; generated packages, nested structs, array/nullability rendering and overrides are covered |
| Custom operation | A custom expression operation reaches the emitter without editing a dispatcher; an unregistered operation is refused; a supplied emitter is used for core SQL |
| Reference build | The reference blueprint is a `GraphBlueprint`; compile + execute publishes `write_result`, `meta_graph_document` and `import_bundle`, writes all expected files and publishes no `core` intermediates |

### 2.4 Fixtures and harness

- No pytest fixtures. Shared values are ordinary modules:
  - `tests/distribution/support.py`: `TestEstate(Asset)` with fixed `AssetOptions`.
  - `tests/distribution/executors/targets/_support.py`: `node()`, `bound_blueprint()`, `record_type()`, `opening()`, `resolve_inputs()`, `connection()`, `component()`.
  - Local `_fixture()` helpers in `test_blueprint_source.py` and `test_source_roundtrip.py`.
- Tests use `unittest.TestCase` and `subTest` heavily, which is why 350 test items produce 1,957 subtests. Pytest 9.1.1 supports this natively; there is no `pytest-subtests` dependency.
- Temporary files use `tempfile.TemporaryDirectory`; no test requires a live database or network. The Neo4j target test writes and inspects the import bundle only.
- Import-isolation tests spawn `sys.executable -c ...` subprocesses and assert that `kg_build_system.distribution`, `duckdb` or the removed `kg_build_system.pipeline` package did not enter `sys.modules`.
- `pytest.ini_options` sets `testpaths = ["tests"]` and `pythonpath = ["."]`; the latter makes `import reference_project` and `import tests.distribution.support` work without installation.
- There are no skip/xfail decorators; the words “skip”/“skipped” appear only in test names and docstrings.

### 2.5 Contract tests

`docs/developer/testing.md` states the doctrine: “The contract tests guard interfaces, not implementation. Each test names a boundary and fails when the boundary changes shape. A test that only proves one function returns the expected value is not a contract test.”

The same document names five groups: kernel flow, planner, executor, distribution, and reference build. The actual tree has additional groups: `tests/pipeline/` (typed identity) and the root architecture/public-API guards. Treat the directory layout as the authoritative grouping.

The explicitly named contract suite is `tests/pipeline/test_pipeline_identity.py` (“Contract tests for the typed pipeline identity model”, 24 tests). It guards:

- dotted step names as one key segment; input/output name collisions; connection direction; step ids rejecting `/`;
- expanded openings without a delimiter parser; concrete types and patterns, including `**` only at the end;
- exact two-segment instruction kinds; duplicate step ids and component ids; duplicate artifact names;
- unresolved openings and unknown connection endpoints;
- plan/report documents using arrays for every identity role; codec round trips for every identity role;
- publication preserving its opening; failure and outcome carrying the same step id.

The broader boundary tests are equally contract-shaped: import isolation, source/DTO round trips, architecture matrices, public-facade checks and the reference build.

### 2.6 Authoring typecheck fixture

`tests/typecheck/authoring.py` (234 lines, positive) constructs a complete authoring surface and uses `typing.assert_type` to pin inferred types:

- `FixtureAsset(Asset)` with `@asset_contract`.
- `FixtureGraph(Graph)` with claims, purpose, frames and limitations.
- `Address`/`Detail` structs; `Site`/`Region` tables; `Summary` computed struct; `SiteProjection`; `SiteNode`; a node binding.
- `Site.site_id` is `Selection[Nullable[str]]` and `NullableSelection[str]`.
- source reads are nullable; computed projections follow their selection.
- one-shot row effects: `alter_rows().drop_null()`, `.expand()`, chained effects; `extract`, `at`, `unique`, `sort`, `concat`, `transform_items`, `drop_null_items`.
- `lookup`, `zip`, `RowSource.unnest`.
- `NodeValues` / `node_binding` result typing.

`tests/typecheck/authoring_negative.py` (65 lines, negative) expects failures:

- removed `.expression`, `.value`, `.model`, `.require_expression`;
- `concat`/`prepend` on a scalar, `expand` on a scalar;
- a second `alter_rows()`;
- removed `distinct`, `join`, `where_present`, `where_if`;
- `rows=Site` instead of a row source in `node_binding`;
- `Field[str | None]`;
- removed `projection_field`.

Negative expectations are encoded as `# pyright: ignore[report...]` comments. The file also begins with `# pyright: basic, reportUnusedImport=false, ...`, while `pyproject.toml` lists it under `strict`. File-level pyright directives take precedence for that file, so the strict entry appears to be overridden; whether that is intentional is **unclear**.

The fixtures are typechecked by pyright, not run by pytest.

## 3. How to run verification

### 3.1 Standard commands

```console
cd /home/paul/Repos/kg-build-system
uv run pytest -q
uv run pyright
uv run mkdocs build --strict
```

| Command | What it proves | Current observed result |
| --- | --- | --- |
| `uv run pytest -q` | All 350 collected tests, including import isolation and the reference build in a temporary directory | `350 passed, 1957 subtests passed in 6.78s` |
| `uv run pyright` | Static types for `kg_build_system` plus the two authoring fixtures | 0 errors, 0 warnings, 0 informations when the virtual environment is visible |
| `uv run mkdocs build --strict` | Documentation links, navigation membership and strict MkDocs warnings | Passes; docs built in 1.36 s |
| `uv run pytest -q tests/test_reference_build.py` | Runs the reference compile + execute into a temporary directory (same functions as `reference_project/build.py`) | Passes; 21 nodes and 21 edges published |
| `cd ~/Repos/opentargets-kg && uv run pytest -q` | External Open Targets compatibility check | Documented as 7 tests; not run or verified in this checkout |

### 3.2 Pyright environment caveat

`pyproject.toml` has `include = ["kg_build_system", "tests/typecheck/authoring.py", "tests/typecheck/authoring_negative.py"]`, `typeCheckingMode = "basic"`, and no `venvPath` or `venv` setting.

Direct invocation without an activated environment:

```console
.venv/bin/pyright
# 63 errors, mostly reportMissingImports for libcst, watchfiles and other deps
```

With the environment exported:

```console
VIRTUAL_ENV="$PWD/.venv" PATH="$PWD/.venv/bin:$PATH" .venv/bin/pyright
# 0 errors, 0 warnings, 0 informations
```

The documented `uv run pyright` is expected to export the project environment and therefore produce 0 errors. The direct invocation is a trap for anyone who calls the binary directly.

Pyright does **not** analyze the rest of `tests/`, `reference_project/`, `legacy/`, `build/` or `site/`. A type error in a test file other than the two fixtures is not caught by pyright.

### 3.3 Documentation build caveat

`uv run mkdocs build --strict` writes `site/` in the repository root. `site/` is gitignored. For a read-only check, point the output elsewhere:

```console
uv run mkdocs build --strict --site-dir /tmp/kg-build-site
```

The build emits a Material-for-MkDocs end-of-life notice, but it is not treated as an error; the strict build still exits 0.

### 3.4 Expected state vs. documented state

The suite currently reports **350 tests / 1,957 subtests**. Several documents still state **259 tests / 1,858 subtests**: `README.md:103`, `FRAMEWORK_STATE.md:8`, `docs/developer/testing.md:210`, `docs/developer/index.md:58`, `docs/developer/system-design.md:891`, `docs/developer/philosophy.md:261`.

The reference build passes; the documented “Open Targets: 7 tests” is external and **unverified**.

## 4. `reference_project`

### 4.1 What it is

`reference_project/` is a checked-in, executable example of the public authoring API. It is not part of the `kg_build_system` wheel and is not imported by the framework.

- 39 Python files outside `build/`.
- 5 source JSON documents.
- One logical asset, `Estate`, with `AssetLayout` over the five files.
- 6 concrete node types and 6 concrete edge types.
- 4 composed planners: deduplication, file, meta-graph and Neo4j.
- 48 git-tracked files in `reference_project/`; `reference_project/build/` is untracked and gitignored.

### 4.2 Entry points

`reference_project/build.py` is the composition entry point:

| Function | Role |
| --- | --- |
| `create_reference_blueprint()` | `create_blueprint(namespace_path=PROJECT_ROOT)` |
| `compile_reference_build()` | `compile(blueprint=..., planners=...)` |
| `run_reference_build()` | `execute(plan, output_directory=PROJECT_ROOT / "build")` |
| `__main__` block | Calls `run_reference_build()` |

Invocation: `uv run python -m reference_project.build` or `uv run python reference_project/build.py`. Both work because the editable install adds the repository root to `sys.path`. The VSCode launch configuration “Python Debugger: Reference Project” runs `reference_project/build.py` with `cwd = reference_project`.

`tests/test_reference_build.py` imports `create_reference_blueprint` and `compile_reference_build` and executes the plan into a temporary directory, so the example is exercised on every test run.

### 4.3 End-to-end flow

1. `Estate` declares one asset with `AssetLayout` members: `sites.json`, `equipment.json`, `surveys.json`, `readings/temperature.json`, `readings/mechanical/vibration.json`; `@asset_contract(...)` points at `InferDataContractProvider` with `mode="table_group"`, `layout="files"` and timestamp overrides for three date columns.
2. Generated declarations are checked in under `reference_project/table/`: `SitesTable`, `EquipmentTable`, `SurveysTable`, `TemperatureTable`, `VibrationTable`, nested `Struct`s and `TableGroup`s.
3. `table/projections/defects.py` flattens `surveys.areas[].elements[].defects[]` into one row per defect; `table/projections/observations.py` flattens observations from that grain.
4. `topology/` declares 6 concrete nodes, 6 concrete edges, 2 abstract categories and reusable templates for provenance, documented summaries and relation stamps.
5. `bindings/` binds each node and edge from a table or projection, with explicit null policy (`drop_null`, `default_to`) and provenance stamps.
6. `compile()` adds the default `DuckDbSourcePlanner` and core planners, then appends `DeduplicationPlanner`, `FilePlanner("graph.jsonl")`, `MetaGraphPlanner` and `Neo4jPlanner`; `execute()` writes the plan, graph, meta-graph, Neo4j bundle and report.

Source data sizes: 3 sites, 4 equipment records, 3 surveys, 3 temperature readings, 2 vibration readings.

### 4.4 What the build produces

Observed `reference_project/build/` contents:

| Artifact | Size / count | Contents |
| --- | --- | --- |
| `workflow_plan.json` | 157,475 bytes | 6 components, 60 steps, 90 connections |
| `build_report.json` | 2,148 bytes | 3 published artifacts, 0 recovered failures, 0 unresolved failures |
| `graph.jsonl` | 9,819 bytes | 42 lines = 21 nodes + 21 edges |
| `meta_graph.json` | 30,540 bytes | 7 node components, 7 edge components, 2 abstract components |
| `meta_graph.html` | 341,680 bytes | Self-contained diagram |
| `neo4j-import/import_neo4j.py` | 5,733 bytes | Standalone import script |
| `neo4j-import/nodes/*.parquet` | 6 files | One per concrete node type |
| `neo4j-import/relationships/*.parquet` | 6 files | One per concrete edge type |

Plan components: `duckdb@1`, `core@4`, `deduplication@2`, `file@2`, `meta_graph@2`, `neo4j@2`.

Step kinds: 16 SQL, 13 Neo4j, 12 aggregate, 12 deduplication, 5 source-relation, 1 file, 1 meta-graph.

Graph record counts: site 3, unit 4, defect 3, observation 3, reading 5, survey_visit 3; has_unit 4, has_defect 3, has_observation 3, measures 5, observed_during 3, surveyed_at 3.

Meta-graph components include abstract `documented` and `monitored_relation`; that is why 7 node/edge components cover 6 concrete node/edge types.

The checked-in generated table packages have `.kbs-generation.json` ownership records:

- `format_version: "6"`
- `provider_qualname: "InferDataContractProvider"`
- `provider_version: "7"`
- one `request_fingerprint` and optional `source_digest` per request
- owned files and SHA-256 hashes, including nested `mechanical/` files for the readings product

There are four manifests: `equipment`, `sites`, `surveys`, `readings`.

### 4.5 Relationship to the docs

- `docs/concepts/assets.md` uses the same monitored-estate scenario but its `Estate` snippet shows `semantics=Semantics(...)` and no `@asset_contract`. The real `reference_project/assets.py` has `@asset_contract(...)` and no `semantics` on `AssetOptions`.
- `docs/reference/assets.md` shows the `@asset_contract` fragment and generated-table rules.
- `docs/developer/testing.md` names the reference build as the end-to-end check.
- `docs/concepts/index.md` uses a different illustrative package name (`from estate.assets import Estate`), not `reference_project`.
- There is no MkDocs snippet-inclusion or doctest mechanism. The docs build checks links and navigation, not Python examples. The reference build test is the only executable proof that the documented composition works.

### 4.6 Reference-project limits

- There is **no `Graph` declaration** in `reference_project/`: no `GraphOptions`, no `GraphSemantics`, no purpose or claims at the graph level. The blueprint is assembled from topology/bindings/assets alone.
- Generated tables are checked in and treated as source. `reference_project/table/__init__.py` states that the checked-in per-table directories predate the single-asset request; a current generation pass would write one package at `table/estate`, a multi-table layout limit. Running `kbs generate` on this project is not part of its build and is not exercised; whether it would create a parallel `table/estate` product is **unclear**.
- `reference_project/build/` is gitignored, so a fresh clone has no artifacts until the build is run. The files present in this checkout are dated 2026-11-05, one day before the current HEAD commit.
- The docs example and the checked-in asset are not identical; do not treat docs snippets as generated from this project.

## 5. `legacy/`

`legacy/` is a complete prior implementation snapshot, not a live package.

| Fact | Detail |
| --- | --- |
| Size | 161 Python files, 21,163 lines |
| Location | `legacy/kg_build_system/` |
| Packaging | No `pyproject.toml`; not included in the wheel (`packages = ["kg_build_system"]`) |
| Git | Not tracked; excluded by `.git/info/exclude` (`legacy/`) |
| Imports | No current package or test imports `legacy` |
| Architecture | Old `api.py`, `authoring.py`, `compile/`, `workflow/`, `engines/`, `modules/`, `relational/`, `table/`, `topology/`, `types/`, `binding/`, `annotations/`, `code_generation/` |
| Old API names | `BuildBlueprint`, `WorkflowContractIR`, `compile_workflow`, `configure_blueprint_modules`, `CoreModule`, `register_module` |
| Old CLI | `legacy/kg_build_system/cli/main.py` has the same `argparse` skeleton (`kbs`, `generate`) but imports the old `code_generation.interfaces.add_generate_command` |

Evidence it is dead:

- No `legacy` import in `kg_build_system`, `tests`, `reference_project`, `pyproject.toml`, `mkdocs.yml` or `docs/`.
- `git ls-files legacy` returns 0.
- The current tests check removal of the old `kg_build_system.pipeline` module path, not the `legacy/` directory.
- `__pycache__` exists, so it was imported at some point, but that is not runtime wiring.

Conclusion: `legacy/` is a local, untracked archive of the pre-refactor implementation. It is not installed, not imported and not live. Do not treat it as supported API or as part of the package.

## 6. `pyproject.toml`

### 6.1 Packaging

| Field | Value |
| --- | --- |
| Name | `kg-build-system` |
| Version | `0.1.0` |
| Description | “Declarative knowledge graph build system” |
| Readme | `README.md` |
| License | `{ text = "Apache-2.0" }` |
| Requires Python | `>=3.12` |
| Build backend | `hatchling` |
| Wheel target | `packages = ["kg_build_system"]` |
| Console script | `kbs = "kg_build_system.cli:main"` |
| Dev group | `mkdocs-material>=9.8.0`, `pyright>=1.1.400`, `pytest>=9.1.1` |

There is no `[project.optional-dependencies]`, no extras, no classifiers, no project URLs and no sdist-specific configuration. `kg_build_system/py.typed` exists; there is no explicit package-data table.

### 6.2 Runtime dependencies

| Dependency | Lower bound | Role / observation |
| --- | --- | --- |
| `duckdb` | `>=1.4` | Default SQL engine and DuckDB executor |
| `fsspec` | `>=2025.7` | Filesystem abstraction; imported in DuckDB readers and dataset generation |
| `libcst` | `>=1.8` | Static `@asset_contract` discovery and package rendering |
| `pydantic` | `>=2.10` | Frozen/strict configuration and DTO validation |
| `rich` | `>=14.1` | Console monitor; imported lazily, but declared as a required runtime dependency |
| `sqlglot` | `>=30.14.0` | SQL expression construction/emission |
| `s3fs` | `>=2025.7` | No direct import found in `kg_build_system`; likely an fsspec S3 backend convenience |
| `watchfiles` | `>=1.1` | `kbs generate --watch` |
| `pytz` | `>=2026.3.post1` | No direct import found in `kg_build_system`; purpose unclear |

All dependencies are lower-bounded, none upper-bounded. `uv.lock` (361 KB) pins the resolved graph. `.python-version` is `3.12`; the checked-in `.venv` runs Python 3.12.14.

### 6.3 Tool configuration

```toml
[tool.pyright]
include = [
    "kg_build_system",
    "tests/typecheck/authoring.py",
    "tests/typecheck/authoring_negative.py",
]
typeCheckingMode = "basic"
strict = ["tests/typecheck/authoring.py", "tests/typecheck/authoring_negative.py"]
reportMissingTypeStubs = false

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

There is:

- no `[tool.ruff]` section and no `ruff` dependency, although generated files carry `# ruff: noqa: F401` headers;
- no `mypy`, `coverage`, `tox`, `nox`, `pre-commit`, `Makefile` or `justfile`;
- no pytest markers, `addopts`, `filterwarnings` or timeout configuration;
- no pyright `venvPath`/`venv`, which is why direct binary invocation can fail.

`mkdocs` itself is not a direct dev dependency; it comes transitively through `mkdocs-material`.

## 7. `build/`

### 7.1 Repository-root `build/`

Current contents:

```text
build/
  _workdir/     (empty)
```

- `build/` is gitignored (`/build/` in `.gitignore`).
- There is no `workflow_plan.json`, `build_report.json`, graph file or target output.
- The only child is an empty `_workdir`, which is the runtime working storage directory.
- This is consistent with kernel tests that call `toolchain.execute(..., output_directory=Path("build"))` or configure `working_directory=Path("build/_workdir")`; those tests use the runtime directly, not `api.execute`, so no plan/report is written.
- Do not read this directory as the reference build output; the reference output is under `reference_project/build/`.

### 7.2 How build artifacts are produced

`api.execute(plan, output_directory=...)` is the producer:

1. Creates the output directory.
2. Writes `workflow_plan.json` **before** execution, so it exists even if the run fails.
3. Creates `RuntimeConfiguration` from `BuildRuntime` and replaces `output_directory`.
4. Runs the toolchain, which opens providers and writes resources under `output_directory/_workdir`.
5. Writes `build_report.json` **after** execution completes.
6. Planners/executors write their own publications:
   - `FileExecutor` → the configured JSONL path, e.g. `graph.jsonl`;
   - `MetaGraphExecutor` → `meta_graph.json` and optional `meta_graph.html`;
   - `Neo4jExecutor` → `neo4j-import/` with Parquet files and `import_neo4j.py`;
   - `ConflictReportExecutor` → findings report / failure, depending on configuration.

Only composed output planners publish. There is no implicit graph file; a composition without a reader of core graph records fails assembly.

### 7.3 `reference_project/build/`

The real artifact set, produced by `reference_project/build.py`:

- `workflow_plan.json` — the executed plan (60 steps, 90 connections).
- `build_report.json` — 3 published artifacts, no failures.
- `graph.jsonl` — 42 records: 21 nodes + 21 edges.
- `meta_graph.json` / `meta_graph.html` — effective topology and diagram.
- `neo4j-import/` — 6 node Parquet files, 6 relationship Parquet files, standalone importer.
- No `_workdir` remains after the run in this checkout (working storage is normally empty after a build).

`reference_project/build/` is gitignored; the generated table packages under `reference_project/table/` are tracked and have `.kbs-generation.json` manifests.

## 8. CI configuration

There is **no CI configuration** in the source repository.

Checked and absent:

- `.github/workflows/`
- `.gitlab-ci.yml`
- `.circleci/`
- `azure-pipelines.yml`
- `Jenkinsfile`
- `.pre-commit-config.yaml`
- `tox.ini`, `noxfile.py`, `Makefile`, `justfile`

The only automation is local:

- `uv run pytest -q`
- `uv run pyright`
- `uv run mkdocs build --strict`
- the VSCode launch configurations
- the local `.opencode` plugins (agent reminders, not project CI)

What is missing for CI:

- a pytest job on a supported Python matrix (at least 3.12, likely 3.13);
- a pyright job with the virtual environment correctly exported;
- a strict MkDocs build job and link checking;
- a wheel build and install smoke test;
- a reference-build job (or a test job that includes it);
- a lockfile consistency check (`uv lock --check` or equivalent);
- the external Open Targets job, caching, artifact upload and branch protection;
- ruff/format/lint checks if wanted; no ruff config exists today.

## 9. Surprising or ambiguous points

1. **`kbs` is not a build command.** It only runs code generation. `compile()` and `execute()` are Python API calls. This is intentional per the install docs, but surprising for a package whose main console script is named after the framework.
2. **Verification counts are stale.** Current run: 350 tests / 1,957 subtests. Six docs files still say 259 / 1,858. Do not quote the docs numbers without checking the checkout.
3. **Direct pyright is environment-sensitive.** `.venv/bin/pyright` gave 63 errors because it could not see `libcst`, `watchfiles`, etc. With `VIRTUAL_ENV` exported it gave 0. `uv run pyright` is the safe documented form, but the config has no `venvPath`.
4. **Pyright scope is narrow.** It analyzes `kg_build_system` plus two typecheck fixtures only. Tests other than the fixtures, `reference_project`, `legacy` and `build` are not typechecked.
5. **The negative typecheck fixture may not be strict.** `pyproject.toml` lists `authoring_negative.py` under `strict`, but the file starts with `# pyright: basic`, which appears to override it. The negative cases rely on `# pyright: ignore[...]`; unused-ignore enforcement is not configured. Whether the strict listing is effective is **unclear**.
6. **The reference project has no `Graph` declaration.** No `GraphOptions`/`GraphSemantics` appears anywhere under `reference_project/`; graph-level purpose/claims are absent. The blueprint is still valid because the graph language permits zero declarations.
7. **Reference generated tables are historical.** `reference_project/table/__init__.py` says the checked-in per-table packages predate the single-asset request and that a current generation pass would write one package at `table/estate`. Running `kbs generate` there is not part of the build and is not tested; the resulting tree is **unclear**.
8. **The docs example is not the checked-in asset.** `docs/concepts/assets.md` shows `semantics=` on `Estate` and no `@asset_contract`; the real `assets.py` has `@asset_contract` and no semantics. Docs snippets are illustrative, not generated.
9. **Root `build/` is not reference output.** It contains only an empty `_workdir`, is gitignored, and is consistent with tests that use `Path("build")` directly. The real artifacts are in `reference_project/build/`.
10. **Reference artifacts are untracked.** `reference_project/build/` is gitignored; a fresh clone has no plan/report/graph/Neo4j bundle until the build runs.
11. **No CI at all.** All checks are manual. The repository has a lockfile and a full test suite but no workflow file to run them.
12. **No ruff.** Generated files carry `# ruff: noqa: F401` headers, but `ruff` is neither a dependency nor configured. The headers are inert in this checkout.
13. **`legacy/` is untracked.** `git ls-files legacy` is empty; `.git/info/exclude` hides it. The same applies to `.opencode/plugins/design-notes/` and `.opencode/plugins/rule-promotion/`. These exist only in local snapshots, so a KB built from a clean clone may not see them.
14. **`.vscode` “Generate” launch has no `cwd`.** It runs module `kg_build_system.cli` with arg `generate`; `--project` defaults to the process cwd, which is the workspace root. That scans the whole repository, including `reference_project` contracts, rather than a project subdirectory. Likely unintended.
15. **`--debounce` is parsed but not validated at parse time.** One-shot mode ignores it; watch mode rejects `<= 0` only when `watch()` runs, which surfaces as an argparse-style exit 2 via `ValueError`.
16. **`--check` success is silent.** A `CURRENT` check prints nothing. CI or scripts must rely on the exit code, not output.
17. **Watch-mode failure exit semantics are weak.** An initial pass can fail, the watcher continues, and Ctrl+C returns 0. Only one-shot passes return 1 for generation failure/STALE.
18. **`pytz` and `s3fs` have no direct import.** Both are declared runtime dependencies; `pytz` in particular appears unused. `rich` is described as optional in `frontend/monitor.py`, but it is an unconditional dependency in `pyproject.toml`. Reasons are **unclear**.
19. **Pytest subtests are native.** `pytest 9.1.1` provides the `subtests` fixture; no `pytest-subtests` package is installed. Older pytest versions would not reproduce the documented subtest count.
