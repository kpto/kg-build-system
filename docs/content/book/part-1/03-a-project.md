---
title: "3. A project"
summary: "Declarations live in an importable package; discovery and generation decide what a build sees."
section: book
perspective: book
part: I
chapter: 3
order: 13
status: normative
verified: 2026-11-11
sources:
  - kg_build_system/distribution/interpreter/service/_private/discovery.py
  - kg_build_system/distribution/interpreter/service/_private/create.py
  - kg_build_system/generation/code_generation/service/_private/command.py
  - reference_project/build.py
  - docs/content/book/part-2/09-generation.md
---

The first build passed `reference_project` to `create_blueprint` as a path. This chapter explains what that path means. A project is not a folder of files that a build happens to read. It is an importable package whose public module-level values are the declarations a build can see. Everything outside the package is outside the build.

## A project is an importable package

The reference project is a package tree.

```text
reference_project/
  __init__.py
  asset/
    __init__.py
    estate.py                   Estate
  graph/
    __init__.py
    graph.py                    EstateGraph and the root Meaning
    common.py                   categories, templates, annotations
    site/
      __init__.py
      node.py                   SiteNode
      has_unit__unit.py         HasUnitEdge
    unit/
      __init__.py
      node.py                   UnitNode
      ...
  relation/
    source/
      __init__.py
      estate/
        __init__.py             facade
        group.py                EstateSourceRelationGroup
        sites.py                SitesSourceRelation and nested Structs
        equipment.py            EquipmentSourceRelation
        surveys.py              SurveysSourceRelation
        readings/
          __init__.py           facade
          group.py
          temperature.py        TemperatureSourceRelation
          mechanical/
            __init__.py         facade
            group.py
            vibration.py        VibrationSourceRelation
    derived/
      defects/
        __init__.py
        relation.py             Defects
        _unnest.py              the private expansion stage
      observations/
        __init__.py
        relation.py             Observations
        _unnest.py
  binding/
    __init__.py
    common.py                   shared stamps
    site/
      __init__.py
      binding.py                site_binding
      has_unit__unit.py         has_unit_binding
    ...
  build.py                      the composition root
  data/                         the JSON source members
  build/                        the output directory
```

Declarations live in importable modules under one package root. Every directory is an ordinary package with an `__init__.py`, and that initializer is a facade: a docstring, re-exports and `__all__`, never a declaration. A package is a grouping; a file is a declaration boundary.

The rules are:

- **No declaration and no business logic in `__init__.py`.** The initializer may re-export, so `from reference_project.graph.site import SiteNode` works; the definition site is `node.py`.
- **One file per concrete public declaration.** `graph/graph.py` holds the graph; `graph/site/node.py` the node; `graph/site/has_unit__unit.py` the edge; `relation/source/estate/sites.py` the source relation; `relation/derived/defects/relation.py` the derived relation; `binding/site/binding.py` the binding.
- **A derived relation is a package.** Its public relation lives in `relation.py`; a private stage lives beside it in `_unnest.py`. The underscore is the visibility rule in the filesystem.
- **Small files follow from small declarations.** Do not split one declaration across files to meet a line count. If a declaration file is large, question the declaration, not the file.

Every public declaration is a module-level value. `SitesSourceRelation` is a class object in `reference_project.relation.source.estate.sites`; `site_binding` is a binding value in `reference_project.binding.site.binding`. Discovery imports the modules and reads the values they expose. There is no registry file, no decorator that registers a class, no per-file declaration list and no plugin entry point.

The tree is not a filing convention. It is the import graph, the review map and the model's two axes. `asset/` names the source units. `relation/` names the domain relations, source and derived. `graph/` names what the graph asserts, with the graph declaration at its root (the topology language declares the nodes, edges and properties; the graph language declares the project's root meaning). `binding/` is the only package that imports both axes. A dependency test enforces that direction: `graph/` imports neither `relation/` nor `binding/`, and `relation/` imports neither `graph/` nor `binding/`. A reader who knows the reference project's tree can predict which declaration a build will use; a reader who knows only the output cannot.

The module-level rule has a sharp edge. A class defined inside a function or inside another class is never a declaration, because discovery reads module attributes. A class defined at module level but bound to a name beginning with an underscore is skipped, because discovery reads public names. A helper value that exists only to be unpacked into a binding is fine; a declaration that exists only as a local is not.

The type checker sees the same boundary. Declarations are ordinary Python values with ordinary annotations, so a source-relation field with the wrong value type or a binding property assigned the wrong expression is a static error before a build runs. The framework does not introduce a second language with its own type checker.

## Discovery is a stable import, not a search

`create_blueprint(namespace_path=ROOT)` resolves the project directory, takes its directory name as the top-level package name, puts the parent directory on the import path and imports the package and its submodules in sorted order. The import path insertion is temporary; it is removed after discovery.

The walk prunes four things: a directory named `build`, a directory named `node_modules`, a directory named `__pycache__` and any directory whose name is not a Python identifier, including dotted directories. It imports each package and each Python module; an `__init__.py` is imported as its package, not as a separate module. Module order is sorted; the values within one module keep their definition order.

Pruning `build` is a circularity guard. The output directory sits inside the project, and its files are not declarations. Discovery skips it by name, so a second run cannot scan the previous run's artifacts. The same project can therefore be built repeatedly without feeding its own output back into the namespace.

`build.py` is not pruned. Discovery imports it like any other module. That is why the `__main__` guard is mandatory: when the module is imported during discovery, `run_reference_build()` must not execute. The guard distinguishes "run this file as a program" from "import this project as a namespace".

The value collector is deliberately simple. It reads `vars(module)`, skips names that start with an underscore and yields each remaining object once by object identity. Re-exporting a declaration from a package `__init__.py` is safe: the module and the package expose the same object, and the second sighting is ignored. Importing a name from another package is also safe for the same reason. The collector does not inspect a class for a registration marker or walk a class hierarchy for declarations.

Because discovery imports code, import-time side effects run. A module that opens a database connection, writes a file or starts a server at import time will do so during every blueprint build. Keep top-level work declarative. The reference project's modules define classes and values; they do not perform I/O.

## The linker decides what the build contains

Discovery is broad: every public value in every module is a candidate. Linking is narrow: only the reachable closure becomes the blueprint.

The linker indexes every declaration by key within its language. It selects roots; by default the roots are every language, so the binding, data, topology, asset and expression declarations are all eligible starting points. It walks the direct references from each root, expands the closure and orders the reached declarations dependencies-first. Each reached declaration is transcribed once, and the assembled model is validated.

The reachable set is easiest to see from a binding. `site_binding` targets `SiteNode` and reads `SitesSourceRelation.row_source()`. Following those references reaches `SiteNode`, its property slots and its parent category; it reaches `SitesSourceRelation`, its nested `Premises` struct and the `Estate` asset the relation names. The binding itself is reached because it is a public value in the namespace. A source relation that no binding reads and no derived relation references is not reached, even though it is defined and importable. The blueprint is the subgraph the build uses, not a dump of the project.

The reference project has five source relations and two derived relations. Every one is read by at least one binding or by a derived relation, so all seven enter the blueprint. All fourteen bindings enter. The two categories enter because concrete components descend from them. The asset enters because the source relations name it. The graph declaration enters as the root of the record axis.

This is why a declaration can be valid and still absent from a build. Defining a node no binding targets, or a source relation no binding reads, adds a candidate to the project but not a record to the output. The build does not warn about unused candidates; reachability is the rule, and a whole-namespace build is not a lint pass.

A namespace may declare at most one `Graph`. Zero is legal, but then the project states no reason for the graph it builds; the reference project declares one. Two graph declarations are refused when the namespace is linked. The graph declaration is the only declaration with a project-wide scope; every other declaration enters as a root or through a reference from the reachable set.

Uniqueness is checked before reachability. Two declarations in one language that compute the same key are refused even if neither is reachable. A project cannot hide a duplicate by leaving it unbound.

## One namespace is one project

`namespace_path` accepts either a package name or a directory. A directory is resolved, its name becomes the top-level package and its parent becomes the import root. That is how `reference_project` is importable without installation: the build adds the repository root to `sys.path` for the duration of discovery.

`create_blueprint()` with no argument infers the calling file's directory. That is convenient for a script that sits beside its declarations, and it is why the reference `build.py` passes `PROJECT_ROOT` explicitly: the entry point should state its namespace rather than depend on the caller's location. A script that lives outside the project must pass a path.

The alternative declaration mode is explicit bindings.

```python
blueprint = create_blueprint(bindings=(site_binding,))
```

Explicit mode uses the supplied binding values as the starting set. The linker still follows their references, so the source relations, structs, nodes, edges and assets those bindings name enter the blueprint. It is not a way to bypass the model; it is a way to name the roots directly.

The two modes cannot be combined. `create_blueprint(namespace_path=ROOT, bindings=(site_binding,))` raises `ValueError: namespace_path cannot be combined with bindings`. `compile` has the same declaration modes, and a blueprint cannot be combined with either: `ValueError: blueprint cannot be combined with namespace_path or bindings`.

The namespace is one project. There is no merge command, no include list and no cross-project discovery. To share declarations, import them into the namespace; the imported object becomes a public value of a module in the project. To build two projects, run two builds. That limitation is deliberate: a build's reachable set should be explainable by one directory tree, not by a search path.

The same boundary explains the output directory. `build/` is inside the project for convenience, and it is pruned by name. The project owns its source and its output; the build treats only the former as declarations.

## Generated declarations are source, not a build step

The source-relation declarations in the reference project are generated. That does not make them a separate kind of declaration. They are ordinary `SourceRelation[Estate]` subclasses with `Field[T]` attributes, and the build imports them like handwritten modules.

Generation is an edit-time step. A project marks one `Asset` subclass with an asset contract:

```python
@asset_generation(
    AssetGenerationOptions(
        provider=InferDataContractProvider,
        configuration=DataContractInferenceConfig(
            mode="source_relation_group",
            layout="files",
            override={"surveys.surveyed_on": {"type": "timestamp"}},
        ),
        package="reference_project.relation.source",
    ),
)
class Estate(Asset):
    # AssetOptions(name=..., profile=..., layout=...) elided
    ...
```

The decorator is inert. It validates its options and stores them on the class; it performs no I/O, calls no provider and writes no file. The options are not `AssetOptions` fields and never enter the blueprint. The asset model stays the source contract; generation is a frontend that reads a schema once and writes declarations.

`kbs generate` is the only console command. It scans the project for contract requests, asks each provider to observe its source and writes the resulting declarations.

```console
kbs generate --project .
kbs generate --project . --check
kbs generate --project . --regenerate
kbs generate --project . --check --regenerate
kbs generate --project . --watch --debounce 500
```

| Flag | Effect |
| --- | --- |
| `--project PATH` | Project directory to scan or watch; defaults to the current directory |
| `--check` | Compare products with requests and ownership records without writing; does not re-observe sources |
| `--regenerate` | Re-observe every source and regenerate every product, including current ones |
| `--watch` | Run one pass, then watch project files and regenerate on declaration changes |
| `--debounce MS` | Watch debounce in milliseconds; defaults to 300 and must be greater than zero |

| Exit code | Meaning |
| --- | --- |
| `0` | `CURRENT` or `CHANGED`; also a watch session stopped with Ctrl+C |
| `1` | `STALE` or a generation failure |
| `2` | Usage error, including a refused flag combination |

The scan is static. It parses files that contain `asset_generation` without importing the author module, which is why the decorator must sit on one module-level `Asset` subclass with exactly one base and one inline `AssetGenerationOptions(...)` call. The provider observes the source schema and returns a generated package; the engine renders the declarations twice and requires identical text before installing anything.

The product is a package beneath the requested `package`. The reference project's source-relation group provider writes one product per group. The product is one package under `reference_project/relation/source/`: `estate/`, with one module per relation and a nested `readings/` group for the two logger feeds. A product declares each relation in one module, its group in `group.py`, and its `__init__.py` is a facade. Each product carries a `.kbs-generation.json` ownership record with the format version, provider identity, request fingerprint, source digest and the hash of every owned file. The generated header names the request and states the nullability observation. The fields use the public authoring surface: `Field[T]` for a source field, and an optional annotation only where the value type itself is optional, such as an array item.

Generated source is owned. A modified owned file refuses the next pass instead of being overwritten. Unowned files and directories are preserved. Stale products are verified before pruning, and writes are atomic.

The relationship between generation and the build is one-directional. Generation reads a source schema and writes declarations; it does not read graph data, compile a plan or execute a build. The build reads declarations; it does not re-observe the source schema to produce them. That is why the reference project can check in its generated table packages and leave `kbs generate` out of the build. The plan is reproducible from the declarations in the checkout, and re-observation is a deliberate edit-time act.

`--check` is the no-write comparison. It does not re-observe sources, so a changed source schema is invisible to it; it compares the products with the requests and ownership records. `--regenerate` performs the re-observation. Combined with `--check`, it reports source-schema drift as `STALE` without writing. `--watch` cannot be combined with either flag; a watched pass regenerates on declaration changes, not on data-source changes.

A source change alone does not make a product stale. The source digest is provenance, not a tracked input. When the schema changes, `--regenerate` is the explicit act that observes it again. Until then, the generated declarations continue to state the schema they were built from, and the build continues to use them.

Generation is optional. A project can handwrite every source relation, struct and derived relation; the build sees the same public declarations and treats them identically. The decorator and the command exist to make a large source schema cheaper to transcribe, not to create a privileged kind of source.

## The entry point is a composition root

The declarations do not name planners or an output directory. The project's entry point does.

```python
from pathlib import Path

from kg_build_system import compile, create_blueprint, execute
from kg_build_system.distribution import FileConfiguration, FilePlanner

ROOT = Path(__file__).parent
PLANNERS = (FilePlanner(FileConfiguration("graph.jsonl")),)


def main() -> None:
    plan = compile(
        blueprint=create_blueprint(namespace_path=ROOT),
        planners=PLANNERS,
    )
    report = execute(plan, output_directory=ROOT / "build")
    print(f"{report.succeeded}: {len(report.published_artifacts)} artifacts")


if __name__ == "__main__":
    main()
```

The composition root chooses the planner composition and the destination. This version publishes the graph records and nothing else. The reference project's version adds a deduplication planner, a meta-graph planner and a Neo4j planner, so it publishes three artifacts instead of one. Both are valid compositions. A different planner composition is a different `compile` call, not a change to the declarations. That is the boundary: the project states what the graph is; the entry point states which work should produce it.

`ROOT` is derived from the module file, so the output path does not depend on the process working directory. The namespace is explicit, so the same script works even when it is not the caller of `create_blueprint`. The output directory sits under the project and is pruned from discovery.

Keep declarations out of `build.py`, or at least out of its module level. A declaration defined at module level in the entry point is a public value and enters the namespace; a declaration defined inside `main()` is invisible. Neither is a good home for a table or a binding. The entry point composes; the declaration modules declare.

The `print` is a convenience for a human at a terminal. The durable report is `build_report.json`, and the durable plan is `workflow_plan.json`. A script that other code depends on should return the report or write it, not parse the printed line.

## The project is the unit of reproducibility

A project owns its declaration modules, its generated packages and their ownership records, its data source or a reference to one, its build entry point and its output directory. It does not own a registry, a manifest of declarations or a plugin descriptor. The boundary is the importable package.

Three rules follow from that boundary. Discovery imports code, so top-level work must be declarative. The namespace is one project, so shared declarations are imported rather than merged. The output directory is pruned, so a build never consumes its own records.

Within those rules, the project is the unit of reproducibility. A checkout, its declarations and one entry point produce one plan and one set of published records. The generated source-relation modules are part of that checkout, not a hidden build step. The next part opens the declarations themselves: assets and source relations, values and nullability, derived relations and grain, the graph and its meaning, bindings as fulfilment, and the generation step in full.

## Next

[Part II — Authoring a graph](/book/part-2/index) — the declarations a project contains, one layer at a time.
