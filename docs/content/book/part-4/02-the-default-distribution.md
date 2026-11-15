---
title: "19. The default distribution"
summary: "The shipped graph system is one composition of the kernel protocols; its defaults are replaceable choices, while graph meaning stays a model rule."
section: book
perspective: book
part: IV
chapter: 19
order: 42
status: normative
verified: 2026-11-11
sources:
  - kg_build_system/api.py
  - kg_build_system/distribution/implementations.py
  - kg_build_system/distribution/service/internal/emission.py
  - tests/test_reference_build.py
---

## One composition, not the edge of the world

A graph author meets the distribution before meeting the kernel. `Table`, `Field`, `Node`, `Edge`, `create_blueprint`, `compile` and `execute` come from the graph system. A first build can run end to end without naming a protocol, a toolchain or an instruction kind. That convenience creates a natural mistake: the shipped graph system looks like the framework itself, and a capability it lacks looks like a capability the framework cannot express.

The mistake is worth stating plainly because Part IV argues against it. The default distribution is one composition of the kernel protocols. It contains the graph languages, the blueprint and its interpreter, the core planners, the DuckDB source planner and emitter, the file, meta-graph and Neo4j targets, the generation frontend and the CLI. Those are the parts a project uses on the first day. They are also the parts a project can replace, one object at a time, while keeping the rest of the build.

The qualification is equally important. For a graph build, the distribution is not optional. A custom language can run on the kernel alone; nodes, edges, bindings and a blueprint cannot. The default distribution is replaceable as a composition and required as the graph meaning root. Both statements hold because they answer different questions: one asks which implementation supplies a protocol, the other asks what a graph means.

## The languages and the blueprint

The distribution owns eight language packages, but they do not all plug into the kernel in the same way. Six are kernel languages with a `Language` adapter. Two are value languages read inside the declarations of the others.

| Language | Role | Kernel adapter |
| --- | --- | --- |
| `expressions` | Inline value expressions and their typed leaves. | `ExpressionsLanguage` |
| `asset` | One logical source unit and its descriptive layout. | `AssetLanguage` |
| `data` | Tables, fields, relations and projections. | `DataLanguage` |
| `topology` | Nodes, edges, categories and templates. | `TopologyLanguage` |
| `binding` | The row-to-record mapping. | `BindingLanguage` |
| `graph` | One project-level graph declaration and its purpose. | `GraphLanguage` |
| `annotations` | Labels, descriptions and other attached values. | Value language, embedded |
| `semantics` | Purposes, limitations and claims. | Value language, embedded |

The first six produce symbols. The last two supply values that other declarations carry: an annotation on a field, a semantics fragment on a node or edge, the purpose of the graph. Treating them as separate adapters would add language objects that produce no symbols of their own. Treating them as mere comments would lose the distinction between a descriptive string and a purpose with a limitation and a contextless claim. They are value languages because their values are embedded in declaration DTOs, not because they are informal.

`BlueprintLinker` is the distribution's `Linker`. It indexes the kernel languages in a fixed order: expressions, asset, data, topology, binding, graph. The first five are required; graph is optional. It selects roots by language, walks the authoring reference closure, transcribes each reachable declaration once and assembles the result into a `GraphBlueprint`. The symbol graph is the linker's working state; the blueprint is the delivered semantic model.

The blueprint has five fields: graph, data, assets, bindings and an optional graph declaration. It carries nodes, edges, relations, fields, properties, assets and operations as semantic roles, connected by typed refs such as `NodeRef`, `FieldRef` and `PropertyRef`. It does not carry Python paths, declaration expressions or symbol ids. That is the interpreter's contribution: it takes the language DTOs and assembles them into one model without letting the linker's working vocabulary leak into the artifact.

A new declaration syntax plugs in here. A language discovers declarations, derives keys, reports direct references and transcribes symbols; the linker and interpreter do the rest. The blueprint does not need to know how the syntax was written, and the planners do not need to know which language produced a relation. This is why a new syntax is a language rung on the ladder rather than a change to every planner.

## The core planners and the source planner

The default composition has five planners in two groups. Four share `component_id="core"`: `RowSourcePlanner`, `ProjectionPlanner`, `BindingPlanner` and `RecordsPlanner`. They share one `CorePlan` in `PlanContext.shared` and emit row-source, projection, binding and aggregate-record steps. `DuckDbSourcePlanner` has `component_id="duckdb"` and emits one `source.<relation>` step per compatible asset-backed relation.

The split is deliberate. The core planners decide how rows are derived; the source planner decides how a relation is read. A projection does not know whether its input came from Parquet, JSON or a table already materialised in DuckDB. A source step publishes a relation; the core steps consume it. A new source format is another planner with its own component, not an edit to the row algebra.

`Planner.plan` emits steps and stops there. The four core planners do not execute SQL, open a connection or write a file. They describe the relation plan and attach instructions. The executor that claims the instruction kind performs the side effect. Planning and execution are separate objects because a plan must be inspectable before it runs, and because the same plan vocabulary must carry an engine that the planner does not import.

The default toolchain expresses the group rule directly. `default_toolchain` adds the generic source planner unless a supplied planner claims `duckdb`, and adds the four core planners unless a supplied planner claims `core`. A project that supplies a core planner therefore replaces the group without disabling the source planner. A project that supplies a source planner replaces the source without touching the core. The rule is not a registry lookup; it is a component-identity check in the composition root.

## DuckDB, the emitter and the engine boundary

DuckDB appears in the default composition in three places: a source planner, an SQL emitter and an executor with a resource provider. The arrangement is more interesting than the product name suggests.

The core planners consume an engine-neutral relation plan and an injected `SqlEmitter`. `DuckDbSqlEmitter` implements that protocol. `SqlEmitter` lives under `kg_build_system/distribution/service/internal/emission.py`; it is a distribution service protocol, not a kernel protocol. Core imports the relation plan and the emitter interface, never the DuckDB module. The kernel never sees SQL, a connection or an engine object.

The executor side is equally explicit. `DuckDbExecutor` claims the exact instruction kind for SQL on DuckDB and declares the DuckDB resource it reads. `DuckDbResourceProvider` opens that resource on `PipelineStarted` and disposes it on finish or halt. A second engine implements another `SqlEmitter` and an executor that claims another exact kind, for example `("sql", "other")`. The core planners do not change, the plan vocabulary does not change and the kernel protocol set does not change.

This is the concrete meaning of "another storage engine is a composition". The engine boundary has two halves: emission and execution. A new engine must supply both, plus the resource lifecycle and the type mapping. That is real work, not a naming exercise. It is also local work: no graph declaration, blueprint field or core planner needs a new branch.

The exact-kind rule keeps the boundary honest. `InstructionKind(operation, engine)` is a two-segment role type. Dispatch compares it exactly. There is no prefix matching, wildcard kind or family dispatch, so a new executor cannot silently claim every SQL instruction. It claims one kind, and the runtime refuses a plan whose kind has no claimant before any step runs.

## Targets and the shape of publication

The output modules follow the same pattern. `FilePlanner` and `FileExecutor` write JSON Lines; `MetaGraphPlanner` and `MetaGraphExecutor` write a meta-graph document and an optional self-contained page; `Neo4jPlanner` and `Neo4jExecutor` write Parquet files and an import script; `ConflictValidationPlanner` and `ConflictReportExecutor` produce an in-memory conflict report.

A target does not build the graph. It publishes openings the graph already produced. The target planners are deferred and read the `core.graph.**` publications they receive; the executors write them. The instruction kinds are exact: `file`, `meta_graph`, `neo4j` and `conflict_report` each have their own. A target cannot claim a prefix or a family of kinds.

The publication model explains why targets compose without touching the core. A `Publication` is an output that is also a final workflow artifact. It is addressable downstream like an output and appears in the report after execution, but it is exempt from the rule that every ordinary output must be read. A graph can therefore publish nodes and edges whether or not a target is present. Adding a target adds a reader, not a new graph shape.

The targets also show the limit of the composition. The file target rewrites its whole file on every run; the Neo4j target is export-only; the meta-graph is a description, not a query surface. Those are current algorithms of the shipped modules, not properties of the kernel. A project that needs an incremental file writer or a live Neo4j connection composes another module with another exact kind.

## Generation and the CLI are not the build

Generation sits upstream of the build. It observes a source, runs a provider and renders declarations. `@asset_contract` is an inert decorator on an `Asset` subclass; it is outside `AssetOptions` and outside the blueprint. The build imports the resulting declarations and never invokes generation. `compile` and `execute` never invoke it either. Generated and handwritten declarations enter the same language, blueprint, plan and execution path.

The CLI is a frontend, not the public API. It offers `kbs generate`; it does not offer a build subcommand. A project ships a build by calling `create_blueprint`, `compile` and `execute` from Python, or by wrapping those calls in its own script. The narrow CLI is an interface limit of the default composition, not a statement that a build cannot be automated. Another frontend adds commands around the same calls.

Keeping generation and the CLI outside the build protects a simple invariant: an execution is a function of a plan and a runtime configuration, not of an edit-time tool or a command-line session. Generation may change the declarations before a build; the CLI may start a build; neither is part of the plan that runs.

## What is replaceable and what is a model rule

The useful review question is not "is this the default?" but "what kind of default is it?" The table below separates a replaceable choice from a model rule. The distinction returns in Chapter 21 as the first two limit kinds.

| Concern | Default composition | Kind | Replacement |
| --- | --- | --- | --- |
| Languages | Expressions, asset, data, topology, binding, graph | Replaceable default | Another `Language` |
| Linker | `BlueprintLinker` | Replaceable default | Another `Linker` |
| Source formats | Parquet, JSON and CSV through DuckDB | Replaceable default | Another source planner and executor |
| Core row algebra | `group_by` collects; no majority vote | Current algorithm | A module with a planner and executor |
| SQL engine | `DuckDbSqlEmitter` | Replaceable default | Another `SqlEmitter` and executor |
| Targets | File, meta-graph and Neo4j modules | Replaceable default | Another output module |
| Resources | DuckDB and runtime providers | Replaceable default | Another `ResourceProvider` |
| Composition | `Toolchain` only; no registry | Model rule | Another `Toolchain`; not a registry |
| Graph property shape | Scalar or flat array of non-null scalars | Model rule | Reify a nested object as nodes and edges |
| Edge direction | Directed `Edge[Source, Target]` | Model rule | Reify the assertion or add a language kind |
| Instruction dispatch | Exact instruction kinds | Model rule | Another executor claims another exact kind |
| Python payload | `{module, qualname}` reference | Model rule | A new executor kind or external service |
| Asset layout | Descriptive, not an access contract | Model rule | No extension; a planner may interpret it |

A replaceable default names the object that replaces it. A current algorithm names the planner or module that carries another method. A model rule names why no composition should carry the alternative. The first two invite a new object; the third invites a model change, which is a different review with a different cost.

Calling the default distribution the framework boundary collapses these rows. Under that mistake, a missing source format looks like a kernel defect, a scalar graph property looks like an arbitrary restriction, and a new engine looks like a fork. The correct reading is narrower and more useful: the kernel defines the jobs, the distribution supplies one set of workers, and the table says which worker can be replaced.

## The composition root

`api.py` is the composition root. It owns `default_toolchain`, `DEFAULT_TOOLCHAIN`, `create_blueprint`, `compile` and `execute`. The distribution supplies implementations; the composition root decides which ones a default graph build receives.

`compile` is a pure consumer of a blueprint. It creates one when the caller does not supply it, then asks the toolchain to plan the model. It records the source blueprint document under the plan provenance, so a serialized plan carries the model that produced it. It reads no data and writes no artifact. `execute` takes the plan and an output directory, builds a runtime configuration, writes the plan and report documents and runs the plan.

```python
from kg_build_system import compile, execute
from kg_build_system.distribution import FileConfiguration, FilePlanner

plan = compile(
    planners=(FilePlanner(FileConfiguration("graph.jsonl")),),
)
report = execute(plan, output_directory="build")
assert report.succeeded
```

A project that wants a different composition calls `default_toolchain` with its planners and executors, or constructs a `Toolchain` directly. The shortcut functions accept a supplied toolchain and a supplied engine. The composition root is therefore not a gatekeeper; it is the place where the default choices are written down once.

The default distribution is a product, not a boundary. It is the composition a graph project receives when it asks for the default graph build. The boundary is the six protocols and the values they exchange. Chapter 20 turns to the source layout and the tests that keep that boundary visible.

## Next

[20. Architecture and tests](/book/part-4/03-architecture-and-tests) — how zones, imports and contract tests make the boundary reviewable.
