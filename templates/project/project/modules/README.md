# Modules

**BLUF:** A project-local module is an ordinary planner and executor. A source
adapter is a decoder, not a transformer. It adds work to the workflow; it is not
a declaration layer and not an extension registry entry.

## Situation

The shipped distribution reads `parquet`, `json` and `csv` and supplies the graph
workflow. A project whose input needs another format, or whose workflow needs a
step the distribution does not ship, supplies the object here and composes it in
`manifest.py`.

## Mission

Own project-local planners, executors, engine emitters and resources. Do not own
declarations, record shapes or domain relations.

## Execution

- A source adapter MUST be a planner and executor pair: the planner emits one
  no-input step per relation, and the executor reads the input.
- A source adapter MUST preserve the source's model: the schema, column
  meanings, nullability assumptions, grain and identity the declarations already
  state. It MUST decode and cast to the declared types; it MUST NOT join, filter
  rows for a domain reason, translate identifiers, deduplicate, aggregate, expand
  an array or change the grain.
- If the bytes do not match the declared relation, the adapter MUST fail. It MUST
  NOT repair the schema, fill a missing value or drop an unreadable row.
- A source adapter SHOULD be as thin as the format requires: one step, one
  relation output and one exact instruction kind. A domain rule belongs in a
  derived relation, a stage, a binding or a later planner.
- An adapter that feeds the graph MUST output
  `CoreArtifactTypes.table(<SourceRelation name>)`, register the relation under
  the plan relation name (`AssetTable.relation`, not the logical name) and return
  its reference. No consumer declaration changes.
- A module MUST import the framework only. It MUST NOT import the project's
  declarations.
- An engine emitter MUST implement the framework's `ExpressionEmitter` protocol
  and type its operands as `Operand` and its context as `EmissionContext`. Do
  not type them as `object`, use `Any`, or hide a mismatch with
  `# type: ignore`. The conformance example (`kbs init --fixture`) has a minimal emitter.
- An operation owns one emitter. When several relation operations share the
  engine's `RowOperationDTO` node type, compose their emitters into a generic
  router; the router may dispatch by `plan.operation`, but adding an operation
  MUST add an emitter and a composition entry, not edit an `if` chain.
- A relation operation MUST be a `RelationOperationSpec` plus a `RowSourceEmitter`
  in this directory. Its output is plan-local until a `DerivedRelation` or
  `Stage` publishes it with a matching grain. The conformance example's
  `count_rows.py` is the minimal global count; its emitter is composed with
  `DuckDbInstructionEmitter().with_row_sources(...)`.
- A source adapter for a nested or semi-structured format should keep the
  declared grain. It may decode repeated elements into a nested field and let a
  private stage expand them; it must not infer a category from free text, join a
  reference, filter a domain rule, aggregate or change the grain. Preserve
  optional attributes and an absent value as absent. If an identity is a
  document position, state that and state the reorder risk.
- A module MUST NOT be a registry, a plugin entry point or a declaration. The
  composition is `manifest.py`: import the planner and executor there and add
  them to the workflow.
- The conformance example's adapter is the minimal pair; its test adds a
  one-step consumer and reads the relation as the graph would read it.

## Composition

`manifest.py` holds the only composition. Add the adapter's planner to the
workflow's planners and its executor to the workflow's toolchain:

```python
from kg_build_system import DEFAULT_TOOLCHAIN, default_toolchain
from kg_build_system.distribution import FileConfiguration, FilePlanner
from project.modules.my_format import MyFormatExecutor, MyFormatPlanner

toolchain = default_toolchain(
    planners=(
        FilePlanner(FileConfiguration("graph.jsonl")),
        MyFormatPlanner(),
    ),
    executors=(*DEFAULT_TOOLCHAIN.executors, MyFormatExecutor()),
)
```

`Workflow(..., toolchain=toolchain)` takes a toolchain or a planner tuple, never
both. Replace `MyFormatPlanner` with the adapter that reads your format. The
conformance example's adapter needs the consumer its test supplies; a real
adapter's output type is the `core/data/table/<relation>` the core planners
already read.

## A real adapter

The conformance example's adapter has one fixed relation. A real adapter reads the relations the
graph declares and emits one step for each asset it can decode:

```python
from kg_build_system.distribution.model.public.artifacts import CoreArtifactTypes
from kg_build_system.distribution.service.internal import asset_tables
from kg_build_system.kernel import Instruction, Output, PlanContext, Step


class MyFormatPlanner:
    component_id = "my_format"
    version = "1"
    runtime_fields = ()

    def plan(self, model, context: PlanContext):
        del context
        return tuple(
            Step(
                component=self.component_id,
                name=f"source.{table.relation_name}",
                inputs=(),
                outputs=(
                    Output(CoreArtifactTypes.table(table.relation_name)),
                ),
                instruction=Instruction(MY_FORMAT_KIND, {
                    "relation": table.relation,
                    "location": table.asset.layout.locator,
                }),
            )
            for table in asset_tables(model)
            if my_format(table.asset.layout) is not None
        )
```

`MY_FORMAT_KIND` and `my_format` are local to the adapter: the exact instruction
kind and the test the layout must pass.

`table.relation_name` names the artifact type; `table.relation` is the plan-local
name the executor registers; `table.columns` states the declared columns and
types. The executor decodes exactly those columns and casts to those types. It
does not invent a schema or add a domain decision.

## Support

Imports the framework only. Read `../relation/source/README.md` for the relation
the adapter serves, then the minimal adapter.

## Gate

`tests/test_input_adapter.py` and the project's own contract tests. A join, a
filter, an identifier translation, a deduplication, an aggregation or an array
expansion in an adapter is a model defect: the decision belongs elsewhere.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY follow RFC 2119.
