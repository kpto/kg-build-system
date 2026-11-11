---
title: "13. Planning the work"
summary: "Planners turn one semantic model into components, steps and a plan whose wiring is already checked."
section: book
perspective: book
part: III
chapter: 13
order: 33
status: normative
verified: 2026-11-11
sources:
  - kg_build_system/kernel/service/_private/pipeline.py
  - kg_build_system/kernel/service/_private/assembly.py
  - kg_build_system/kernel/model/public/workflow.py
  - kg_build_system/api.py
  - docs/appendix/reference/compile.md
---

The blueprint says that a `site` node exists, that `sites` is its source relation and that `site_binding` populates it. It does not say that a source-relation instruction must run before a SQL instruction, that the binding rows must be aggregated into one node stream, or that a file target should consume that stream at the end. Those are decisions about work, and they belong to planners.

`compile` is the stage that asks every planner for its work and assembles the answers into one `WorkflowPlan`. Compilation is pure. It reads the blueprint and the planner composition, reads no source rows, opens no files and returns a plan whose wiring is already checked. The same blueprint can produce different plans under different compositions; a plan is one answer, not the only possible one.

## A blueprint is meaning; a plan is work

The planner boundary is deliberately narrow. A planner receives one opaque model and a `PlanContext`. The kernel does not inspect the model or tell the planner what it contains; the distribution's planners happen to receive a `GraphBlueprint`, but the contract would be the same for any other model. This is what lets a custom planner read its own model without teaching the kernel about nodes and relations.

`PlanContext` carries two things. `runtime_configuration` holds per-component values known at plan time. `shared` is a mutable scratch space for one compile, so several planners that share a component can publish and read the same plan state.

The four core planners use that scratch space. `RowSourcePlanner`, `ProjectionPlanner`, `BindingPlanner` and `RecordsPlanner` all declare `component_id="core"` and share one `CorePlan` under `core.plan`. The row-source planner builds the relation plan, the projection planner adds projections, the binding planner materialises each binding's rows, and the records planner aggregates those rows into one node or edge stream. They are separate objects because they answer separate questions, but they describe one component because the plan's component identity is the unit a runtime configures and an operator reasons about.

The site chain crosses three components:

| Step | Component | Instruction kind | Consumes | Produces |
| --- | --- | --- | --- | --- |
| `source.sites` | `duckdb` | `source_relation/duckdb` | — | `core/data/table/sites` |
| `binding.6` | `core` | `sql/duckdb` | `core/data/table/sites` | `core/binding/site/6` |
| `aggregate.site` | `core` | `aggregate/duckdb` | `core/binding/site/6` | `core/graph/node/site` |
| `write` | `file` | `file/default` | `core/graph/**` | `file/write_result` |

The binding step's name is `binding.<index>`, where the index is the binding's position in the blueprint. The index is a plan detail, not a graph identity; the artifact type is what names the component (`binding.site`). Nothing in the file target knows how many bindings produced the site stream.

## A planner answers one question

The planner protocol is small enough to state in full.

```python
class Planner(Protocol[ModelT]):
    component_id: str
    version: str
    runtime_fields: tuple[RuntimeField, ...]

    def plan(self, model: ModelT, context: PlanContext) -> Sequence[Step]: ...
```

A planner has one identity, one version, the runtime fields its component needs, and a `plan` method. It does not execute, open data or mutate the model. It reads the model and returns steps. A planner that needs both planning and execution is two objects, not one object with two modes.

`DuckDbSourcePlanner` answers which asset-backed relations can be read. It emits one `source.<relation>` step for each relation whose asset layout resolves to a supported format. It is not an adapter and there is no adapter registry; another format is another ordinary planner producing another ordinary step. If a relation has no layout or an unsupported format, no source step is emitted, and the missing opening shows up when assembly tries to feed the reader.

`BindingPlanner` answers how one binding's rows are produced. It emits one SQL step per binding, with the identity, property and row expressions compiled into payload. `RecordsPlanner` answers how several bindings for one component become one stream. It emits a deferred aggregate step per component, with one input per contributing binding. `FilePlanner` answers where the final records go. It emits one deferred write step that reads the graph-record pattern and publishes a result.

Each planner can be replaced without changing the others. A custom planner can produce a step with any exact instruction kind, as long as an executor for that kind is present at execution. That is the extension surface: the planner composition is a tuple, and the kernel does not maintain a registry of permitted planners.

## The component is the planner's identity

Planners are grouped by `component_id`. One `Component` is published per group, carrying the agreed `version` and `runtime_fields`. Every step the group emits is assigned that component id, even if the planner wrote a different one in its `Step` value.

The grouping rule matters because several planners may describe one component. The group must agree before assembly:

- a version disagreement raises `planners for component 'core' disagree on version: '4' and '5'`;
- a runtime-field disagreement raises `planners for component 'core' disagree on runtime_fields`;
- the first planner's version and fields become the component's published values.

The site plan has three components, and their versions are not interchangeable with their names. `duckdb` is version `1`; `core` is version `4`; `file` is version `2` and declares one optional runtime field, `relative_path`. The version describes the planner implementation that produced the steps. It is not part of any step identity: bumping a component's version describes a new planner implementation, not a new step.

Runtime fields describe values the component accepts at execution; they are not values stored in the plan. `FilePlanner` publishes `relative_path` as an optional string, so an operator can replace it at execution without recompiling. Required fields are checked when the step runs, and an unknown component key is refused before the first step. The plan carries the declaration; the run carries the value.

Assembly also refuses a step whose `component` fact does not match the component it was grouped under. A planner cannot smuggle a step into another component by writing that component's id in the `Step` value. The grouping is the identity, and the step's own component must agree with it.

## A step owns one instruction

A `Step` carries the facts of one unit of work:

| Field | Meaning |
| --- | --- |
| `component` | The component id the step belongs to |
| `name` | A label inside that component |
| `inputs` | The typed openings the step consumes |
| `outputs` | The ordinary outputs and publications it produces |
| `instruction` | Exactly one `Instruction(kind, payload)` |
| `assembly_preference` | `"eager"` or `"deferred"` |

The component and name are the facts; the identity is derived. `StepId(component, name)` is the pair, and its key is `[component, name]`. The name is one key segment even when it contains dots. `projection.defect`, `binding.6` and `aggregate.site` are single segments, not nested paths. This keeps a step's display name readable without making the identity depend on how many dots it contains.

A duplicate identity is refused. Two planners in one component cannot both emit a step named `write`; the assembler reports `duplicate step id file/write`. Two planners in different components may use the same name, because the component is part of the identity.

A step owns exactly one instruction. The instruction's kind is an `InstructionKind(operation, engine)`: two non-empty segments compared exactly, with no prefix matching and no shared `"sql"` family. `sql/duckdb` is one kind. A future SQL engine is a different kind, not a member of a family that a `sql` executor can claim.

The payload is opaque to the kernel. It is JSON-compatible and is read only by the executor registered for the exact kind. SQL is payload under one instruction kind, not a plan field. That is why the plan promises no particular engine: the kind names the engine that must execute the step, and the payload states what that engine should do.

The site chain uses four kinds: `source_relation/duckdb`, `sql/duckdb`, `aggregate/duckdb` and `file/default`. Each kind is resolved independently at execution. There is no rule that a `core` component's steps must use one engine, and no rule that an engine owns a component.

## Ports are openings, not names

A step's ports are typed. An input declares an `ArtifactPattern`: the set of artifact types it accepts. An output or publication declares a concrete `ArtifactType`. An opening's identity is `OpeningId(step, direction, name)`, where the direction is part of the key. An input and an output may share the name `output` and remain distinct, because one is an input opening and the other is an output opening.

A pattern can expand into several inputs. The file target declares `ArtifactPattern.of("core", "graph", "**")`. Assembly matches every concrete graph-record type in the plan and creates one input opening per match. In the reference build that is twelve inputs: six node components and six edge components. An opening name extends the declared input name `records` with the artifact type's segments, so the site input is the key `["records", "core", "graph", "node", "site"]`. The file step does not need a list of components in its configuration; the plan's artifacts supply the list.

A connection is always a resolved output opening to a resolved input opening. There is no half-resolved connection in a delivered plan.

```json
{
  "connections": [
    {
      "input": ["core", "binding.6", "input", "table.sites"],
      "output": ["duckdb", "source.sites", "output", "output"]
    },
    {
      "input": ["core", "aggregate.site", "input", "binding.6"],
      "output": ["core", "binding.6", "output", "output"]
    },
    {
      "input": ["file", "write", "input", "records", "core", "graph", "node", "site"],
      "output": ["core", "aggregate.site", "output", "output"]
    }
  ]
}
```

The opening key includes the step, the direction and the name. A consumer reading the file connection can tell that the site records came from `aggregate.site`, and that the file step's input was expanded for the `core/graph/node/site` type. It does not have to parse the dotted display name of an artifact to recover that fact.

An ordinary `Output` is internal to the run. A `Publication` is an output that is also a final artifact. The file step's `file/write_result` is a publication; `aggregate.site`'s `core/graph/node/site` is an ordinary output. A publication is addressable downstream like any output and also appears in the workflow report. An ordinary output has no report entry.

## Assembly refuses an incomplete graph of work

Planning has two halves. The first half is planner output: components, steps, ports and instructions. The second half is wiring: choosing which output feeds which input. The assembler owns the second half, and it refuses a plan that cannot be completed.

| Refusal | What it means |
| --- | --- |
| Duplicate step id | Two steps claim one identity |
| Unfed input | No output matches an input's type |
| Unread ordinary output | A non-publication output has no consumer |
| Wiring cycle | Following connections returns to the writer |
| Step outside its component | A step's component fact disagrees with its group |
| Duplicate output name | One step gives out two artifacts under one name |

The unread-output rule is the one that changes compositions most often. A rewriting planner before an output planner produces records that the target reads. A rewriting planner after an output planner may produce records that nothing reads. Assembly refuses with `nothing reads ...` rather than letting the work disappear. A publication is exempt because its purpose is to reach the report, not a downstream step.

Wiring is deterministic. Contributions are ranked by component order, then eager before deferred, then declaration order. The assembler prefers the sole writer and sole reader of a type, then ports whose justification is unambiguous. Ranking is a compilation rule, not a runtime order. The runtime schedules dependency waves; the plan's step tuple is not a schedule.

Why insist on this at compile time? Because a plan is a reviewable artifact. An unfed input could be deferred to execution and reported as a source problem, but that would confuse "the graph reads a table that no asset provides" with "the runtime could not find the file". Assembly turns the first into a structural refusal and leaves the second to execution. The distinction is what keeps planning pure and execution honest.

Assembly validates structure, not executor availability. A plan can be assembled with an instruction kind that no executor implements; it simply cannot run. That check belongs to execution, where the toolchain's executors are known.

## Provenance makes the plan self-contained

`api.compile` records the source blueprint document under `plan.provenance["blueprint"]`. The kernel treats provenance as opaque; the composition root adds the document after the plan is assembled and returns a replaced plan. A plan serialised with `workflow_plan_to_document` therefore carries the model that produced it and can be read without a second artifact.

The plan document has four top-level members: `components`, `steps`, `connections` and `provenance`. Every identity is written as its key array. A component is `{id, version, runtime_fields}`; a step carries `id`, `inputs`, `outputs`, `instruction` and `assembly_preference`; a connection carries an input opening and an output opening. A reader can reconstruct the dependency graph, the engine required for each step and the component configuration surface without importing the distribution.

```python
from pathlib import Path

from kg_build_system import compile, create_blueprint
from kg_build_system.distribution import FileConfiguration, FilePlanner

blueprint = create_blueprint(namespace_path=Path("reference_project"))
plan = compile(
    blueprint=blueprint,
    planners=(FilePlanner(FileConfiguration("graph.jsonl")),),
)

source = next(step for step in plan.steps if step.name == "source.sites")
site = next(step for step in plan.steps if step.name == "aggregate.site")
print(source.instruction.kind)                 # source_relation/duckdb
print(site.instruction.kind)                   # aggregate/duckdb
print(site.outputs[0].type.name)               # graph.node.site
print(list(plan.provenance))                   # ['blueprint']
```

The `site` step's input type is a binding artifact for the site component. Its exact index is a plan detail, so the code asserts the stable part rather than pinning the number.

```python
binding_input = site.inputs[0].type
assert binding_input.key.segments[:3] == ("core", "binding", "site")
```

Provenance is not a schema. The kernel does not read it, merge it or validate it. `api.compile` preserves an existing mapping and adds the blueprint under one key; a plan compiled through the kernel directly may have no provenance at all. A consumer that needs the blueprint document should read `provenance["blueprint"]` only when the plan came through the canonical facade.

What the plan cannot know is whether the data exists, whether a source file is readable, whether a property is null, or whether a DuckDB query will succeed. Those are runtime facts. The plan states the work and the wiring; execution discovers the rows. That separation is the reason the next chapter begins with an exact-kind map rather than a data read.

## Next

[14. Executing and publishing](/book/part-3/03-execution-and-outputs) — how checked work becomes rows, resources and a report.
