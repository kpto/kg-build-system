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
  and be composed into the engine in `manifest.py`. `hello_emitter.py` is the
  minimal example; it does not import the operation's authoring module.
- A relation operation MUST be a `RelationOperationSpec` plus a `RowSourceEmitter`
  in this directory. Its output is plan-local until a `DerivedRelation` or
  `Stage` publishes it with a matching grain. `count_rows.py` is the minimal
  global count; its emitter is composed with
  `DuckDbInstructionEmitter().with_row_sources(...)`.
- A module MUST NOT be a registry, a plugin entry point or a declaration. The
  composition is `manifest.py`: import the planner and executor there and add
  them to the workflow.
- `hello_world.py` is the minimal adapter. Its test adds a one-step consumer and
  reads the relation as the graph would read it.

## Composition

`manifest.py` holds the only composition. Add the adapter's planner to the
workflow's planners and its executor to the workflow's toolchain:

```python
from kg_build_system import DEFAULT_TOOLCHAIN, default_toolchain
from kg_build_system.distribution import FileConfiguration, FilePlanner
from project.modules.hello_world import HelloWorldExecutor, HelloWorldPlanner

toolchain = default_toolchain(
    planners=(
        FilePlanner(FileConfiguration("graph.jsonl")),
        HelloWorldPlanner(),
    ),
    executors=(*DEFAULT_TOOLCHAIN.executors, HelloWorldExecutor()),
)
```

`Workflow(..., toolchain=toolchain)` takes a toolchain or a planner tuple, never
both. Replace `HelloWorldPlanner` with the adapter that reads your format. The
hello example needs the consumer its test supplies; a real adapter's output type
is the `core/data/table/<relation>` the core planners already read.

## A real adapter

The hello example has one fixed relation. A real adapter reads the relations the
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
the adapter serves, then `hello_world.py`.

## Gate

`tests/test_input_adapter.py` and the project's own contract tests. A join, a
filter, an identifier translation, a deduplication, an aggregation or an array
expansion in an adapter is a model defect: the decision belongs elsewhere.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY follow RFC 2119.
