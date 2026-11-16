---
title: "2. A first build"
summary: "Run the monitored-estate reference build, read its artifacts and fix a first refusal."
section: book
perspective: book
part: I
chapter: 2
order: 12
status: normative
verified: 2026-11-11
sources:
  - reference_project/manifest.py
  - reference_project/asset/estate.py
  - tests/test_reference_build.py
  - pyproject.toml
  - docs/content/appendix/reference/compile.md
---

The previous chapter described a chain: declarations become a blueprint, the blueprint becomes a plan, the plan produces a report and records. This chapter runs that chain on the reference project and reads what it leaves behind. The project is small by declaration count and complete by artifact count. It is the shortest proof that the public path composes.

## Start from a checkout that passes its own tests

The framework is a Python package plus a `kbs` console script. It requires Python 3.12 or newer. DuckDB, `sqlglot`, `libcst`, `pydantic`, `fsspec`, `watchfiles` and `rich` are runtime dependencies. The documented development path uses `uv`; any PEP 517 installer works.

```console
cd kg-build-system
uv sync
```

Before running the reference build, run the checks that tell you whether the checkout is usable at all.

```console
uv run pytest -q
uv run pyright
```

The suite reports 393 tests and 1,972 subtests passing in roughly seven seconds. Those numbers describe this checkout, not a promise about another revision. A failure here is an environment or checkout problem, not a graph problem, and chasing it through a build error is wasted work.

Pyright reports no errors in this checkout. The measured count is the honest number to quote; do not treat a clean run as a design approval. Pyright analyzes the package and two authoring fixtures, not the whole of `tests/`, `reference_project/` or `legacy/`.

Node is needed to build this knowledge base, not to run the framework. The docs build is a separate concern and does not belong in a first build.

## A small estate still exercises every layer

The project declares one logical asset, `Estate`, over five JSON members: sites, equipment, surveys, a temperature feed and a vibration feed. The asset states a subject, a coverage statement, an authority and a basis. Its layout states the format, the directory and the member map. The layout is descriptive metadata, not an access contract; the DuckDB source planner resolves the JSON members that the source relations name.

Five source relations sit over the asset. `SitesSourceRelation` exposes a site identifier, a site name, a nested premises structure and a priority array. `EquipmentSourceRelation` exposes a unit reference, a site identifier, a unit name, an in-service flag and a survey period. `SurveysSourceRelation` carries the survey identity, the site it belongs to, the survey timestamp and nested areas. The temperature and vibration source relations carry a reading identity, a unit reference, a value and a timestamp. Every field declares a value type. Source access is nullable because a JSON member may be absent; the field type states what the value is when it is present.

Two derived relations sit beside the source relations. `Defects` unnests the defects inside each survey's areas, and `Observations` unnests the observations inside each defect. They change the grain: one survey row can produce several defect rows, and one defect row can produce several observation rows. Each is a contract: a definition with a grain and identity, and a meaning with its own purpose. Its outputs are computed fields, so downstream bindings can read them exactly like source relations.

The source-relation packages are generated and checked in. `kbs generate` is not part of the reference build: the build reads declarations, not source schemas. The generated files use the same public authoring surface as handwritten source relations, so the build cannot tell which were generated and which were typed by hand. Chapter 3 covers the generation step and its ownership record.

The graph declares six concrete node types: `SiteNode`, `UnitNode`, `SurveyVisitNode`, `DefectNode`, `ObservationNode` and `ReadingNode`. It also declares one abstract node category, `DocumentedAbstractNode`, which carries a summary property and gives the concrete nodes a shared parent. Six concrete edge types connect them: `HasUnitEdge` runs from site to unit, `SurveyedAtEdge` from survey visit to site, `HasDefectEdge` from unit to defect, `MeasuresEdge` from unit to reading, `HasObservationEdge` from defect to observation and `ObservedDuringEdge` from defect to survey visit. One abstract edge category, `MonitoredRelationAbstractEdge`, gives every relation a shared parent, and the recorded-relation and timestamped-relation templates supply the `as_at` and `stage` properties they share.

Fourteen bindings map rows to records: seven node bindings and seven edge bindings. The site and unit bindings are the shortest full chain, because the equipment register already carries both endpoint identifiers. The survey, defect, observation and reading bindings exercise derived-relation grain, nested access, defaults and provenance stamps. A shared `source_version` stamp records the feed release that produced each node; a shared `stage` stamp records that each relation was derived.

The build composes four planners: a deduplication planner, a file planner writing `graph.jsonl`, a meta-graph planner and a Neo4j import planner. The default toolchain adds the generic DuckDB source planner and the four core planners. The resulting plan has six components: `duckdb`, `core`, `deduplication`, `file`, `meta_graph` and `neo4j`.

The project declares one `Graph` in `graph/graph.py`. Its meaning states the root purpose: the estate graph exists to answer which equipment is monitored, at which sites, and which defects and observations the surveys reported. Every node, edge, relation and binding meaning is read under that purpose. A project may declare zero graphs, but then it carries no stated reason for the graph it builds.

| Layer | Reference declarations | What the layer exercises |
| --- | --- | --- |
| Asset | One `Estate` over five JSON members | A logical source unit with a descriptive layout |
| Relations | Five source relations, two derived relations | Nested structs, nullable source access, grain changes, contracts |
| Graph | Six nodes, six edges, two categories, one graph declaration | Direction, categories, shared properties and the root purpose |
| Binding | Seven node bindings, seven edge bindings | Identity, defaults, endpoints and provenance stamps |
| Plan | Four explicit planners plus defaults | Components, steps, connections and publications |

## One command creates, compiles and runs

The entry point is a module with a guarded main block. Its essential calls are these.

```python
from pathlib import Path

from kg_build_system import compile, create_blueprint, execute
from kg_build_system.distribution import (
    DeduplicationPlanner, FileConfiguration, FilePlanner,
    MetaGraphPlanner, Neo4jPlanner,
)

PROJECT_ROOT = Path(__file__).parent


def _planners():
    return (
        DeduplicationPlanner(),
        FilePlanner(FileConfiguration("graph.jsonl")),
        MetaGraphPlanner(),
        Neo4jPlanner(),
    )


def run_reference_build() -> None:
    output_dir = PROJECT_ROOT / "build"
    output_dir.mkdir(exist_ok=True)
    plan = compile(
        blueprint=create_blueprint(namespace_path=PROJECT_ROOT),
        planners=_planners(),
    )
    execute(plan, output_directory=output_dir)


if __name__ == "__main__":
    run_reference_build()
```

The checked-in file also exposes `create_reference_blueprint` and `compile_reference_build` as separate functions, so the test suite can inspect the blueprint and the plan without executing.

Run it from the repository root.

```console
uv run python -m reference_project.build
```

The command performs three calls in order. `create_blueprint(namespace_path=PROJECT_ROOT)` imports the project's modules, collects the declarations, links the reachable closure and validates the semantic model. It reads no data. `compile(blueprint=..., planners=...)` turns that model into components, steps and connections. It also reads no data. `execute(plan, output_directory=...)` opens the runtime, runs the steps and writes the outputs. It is the only call that touches the JSON files.

`PROJECT_ROOT` is derived from the module file rather than the process working directory, so the output path is stable when the module is run from the repository root. The `__main__` guard matters because discovery imports `build.py` as part of the project; without the guard, importing the project would start a build. The guard is not a style preference.

The script discards the returned report. The durable form is `build_report.json`, which `execute` writes before returning. A caller that wants to inspect the report in memory can call `execute` directly and read `report.succeeded` and `report.published_artifacts`; the reference script chooses the file.

## The run writes six things

The output directory is `reference_project/build/`. A successful run leaves six entries.

| Entry | Content |
| --- | --- |
| `workflow_plan.json` | The plan: components, steps, connections and provenance |
| `graph.jsonl` | The published records, one JSON object per line |
| `meta_graph.json` | The component model with labels, descriptions, properties and counts |
| `meta_graph.html` | A rendered view of the same model |
| `neo4j-import/` | Node and relationship parquet files plus `import_neo4j.py` |
| `build_report.json` | The outcome: publications, failures, provenance and success |

The order matters. The plan is written before execution starts; the report is written after the run finishes. A run that raises leaves the plan and no report. That makes the plan the explanation of what was attempted and the report the explanation of what completed.

`graph.jsonl` is the record file. Each line has a `kind` of `node` or `edge`, a `type`, a `build_key`, the declared properties and a `_kg_binding_symbol` naming the binding that produced the record. A node line carries its property values; an edge line carries `source_build_key` and `target_build_key` in addition to its own key. The file is JSON Lines rather than one JSON array, so a consumer can stream it.

`meta_graph.json` is the graph of the graph. It describes seven node components and seven edge components: for each kind, six concrete types and one abstract category. Each component carries its label, description, annotations, properties, parent, endpoints and record count. It also carries examples of property values. The HTML file renders that model for a reader. This artifact is not a copy of the source data; it is the declared model plus the counts observed during the run.

`neo4j-import/` is an import bundle, not a live database. It contains one parquet file per concrete node type and one per concrete relationship type, plus a script that invokes a locally installed Neo4j admin tool. The bundle is produced by the Neo4j executor; the run does not start a database.

The DuckDB engine is in memory by default, so no database file appears. There is no compiled Python artifact and no copy of the source JSON. The output directory contains records, the model that describes them, the plan that produced them and the report that judged the run.

Open the directory in this order: the report for the outcome, the records for the result, the meta graph for the meaning of each record type and the plan when a result needs explaining. The report says whether the run published. The records say what it published. The meta graph says what those records are. The plan says which steps and connections produced them. Starting from the plan is the slowest route, because it describes work rather than results.

A second run rewrites the same entries. The build is whole-plan, not incremental; there is no record-level change detection and no attempt to preserve a previous output.

## The report is the outcome, not the log

A successful reference run reports `succeeded: true` and three publications.

| Publication | Type | Value |
| --- | --- | --- |
| File write | `file.write_result` | 21 nodes, 21 edges |
| Meta graph | `meta_graph.meta_graph_document` | 7 node components, 7 edge components, 2 abstract components |
| Neo4j bundle | `neo4j.import_bundle` | 21 nodes, 21 edges |

`recovered_failures` and `unresolved_failures` are both empty. The `published_artifacts` list has exactly those three entries. The test suite enforces that no intermediate artifact with the `core` namespace is published: the records exchanged between the source, derived-relation and binding steps are internal to the run, and only the file, meta-graph and Neo4j publications leave it.

The report fields answer different questions. `published_artifacts` says what left the run. `recovered_failures` says what went wrong and was handled downstream. `unresolved_failures` says what blocked a publication. `provenance` carries the plan provenance, including the blueprint document. `succeeded` is true exactly when `unresolved_failures` is empty. It does not mean every step succeeded; a recovered failure can sit in a successful report.

The provenance is what makes the directory self-describing. `workflow_plan.json` carries the source blueprint document under `provenance.blueprint`, and `build_report.json` carries the plan provenance. A consumer can read the plan without a second artifact and can connect the report back to the model that produced it. The estate's three publications name their own locations in their values, so the report also points at the files it wrote.

When a run fails, the report is still the first surface to read. Each unresolved failure names a step identifier and an exception type. The report does not replace a traceback for a coding error, but it tells you which step in the planned work failed and whether any publication was blocked.

## A first failure is about identity

The most useful first failure is a deliberate one. Open the site binding and remove the row effect from the build key.

```python
build_key=row.site_id,
```

Importing the project raises:

```text
TypeError: build_key must be non-nullable
```

The message is exact, and it is raised while the binding is constructed, before a blueprint exists. The source read for `site_id` is nullable because a JSON member can be missing. `Field[str]` declares the value type when the field is present; it does not promise presence. A build key must be a present scalar, because a record with no identity cannot be named, connected or deduplicated.

A display value has a different rule. `default_to("Unnamed site")` states that a missing name is acceptable and supplies one. An identity has no meaningful default: inventing a key would create a record that no source row supports. That is why the fix is a row effect, not a default.

```python
build_key=row.site_id.alter_rows().drop_null(),
```

`alter_rows()` returns a one-shot row-effect handle. `drop_null()` filters the rows whose selected value is null before the binding sees them. The effect is one-shot: another row effect needs another call to `alter_rows()`. The drop changes the grain of the binding, because the excluded rows produce no record. That is a design decision, and the declaration states it rather than hiding it in a query.

A second common first failure is passing the source-relation class instead of its row source.

```python
rows=SitesSourceRelation,
```

That raises:

```text
TypeError: rows must be a row source value; use SourceRelation.row_source() or DerivedRelation.row_source()
```

A binding consumes a row-source value, not a class. `SitesSourceRelation.row_source()` states the grain and the fields the binding reads. The class is the declaration; the row source is the value the binding reads. A `Stage` has no bindable row source at all, so a private intermediate cannot be bound by accident.

Both failures occur before data is read. The first happens while the module is imported during discovery; the second happens at the same point. No plan is written and no partial output appears. This is the practical benefit of separating authoring and execution: a nullable identity is caught as a declaration error, not discovered halfway through a run with a null key in the output.

Fix the binding and run the command again. The counts return to 21 nodes and 21 edges when the source contains no null site identifiers. The fix does not repair missing identities; it excludes the rows that lack them. If the source genuinely has unidentified sites, the next question is a design question: should those rows be dropped, or should the source be corrected before the build?

## What the first build proves

The reference run proves that the public path composes: declarations become a blueprint, the blueprint becomes a sixty-step plan with ninety connections, the plan executes, and the report accounts for three publications and 21 nodes and 21 edges. The record count is small. The artifact chain is complete.

It also shows where the next questions live. The run found the declarations because they are module-level values in an importable package. It ignored the `build/` directory because discovery prunes it. It imported `build.py` and relied on the guard. The next chapter explains that boundary: where declarations live, how discovery finds them, and how generated declarations enter the same namespace.

## Next

[3. A project](/book/part-1/03-a-project) — where declarations live and what a build can see.
