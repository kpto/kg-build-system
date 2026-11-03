# Debug a build

Find the stage that failed, read the report, and change the declaration,
composition or input that caused it.

## Before you begin

- Run `create_blueprint` and `compile` before `build`. They check declarations
  and module wiring without reading data.
- Know where the build writes its outputs.
  [Compile, build and outputs](../concepts/build-and-outputs.md) covers the
  lifecycle and the output files.
- Keep [Bindings](../concepts/bindings.md),
  [Row sources](../concepts/row-sources.md),
  [Projections](../concepts/projections.md) and
  [Modules](../concepts/modules.md) open while you work.

A normal investigation starts with these calls:

```python
from pathlib import Path

from kg_build_system import build, compile, create_blueprint
from kg_build_system.distribution import (
    FileModule, FileModuleConfiguration, register_module,
)

modules = (
    register_module(FileModule, FileModuleConfiguration("graph.jsonl")),
)
blueprint = create_blueprint()
contract = compile(blueprint=blueprint, modules=modules)
report = build(contract, output_directory=Path("build"), monitor=False)
```

If `create_blueprint` or `compile` raises, fix that error before running
`build`. A compile failure is a declaration or composition problem, not a data
problem.

## Steps

### Step 1: Read the report first

`build` returns a `WorkflowReport`. It records failures, published artifacts and
provenance:

```python
print(report.succeeded)

for failure in report.unresolved_failures:
    print(failure.module_id, failure.step_id, failure.message)

for failure in report.recovered_failures:
    print("recovered:", failure.module_id, failure.message)

for artifact in report.published_artifacts:
    print(artifact.type.namespace, artifact.type.name)
```

- `succeeded` is true when `unresolved_failures` is empty.
- `unresolved_failures` are the failures that stopped an output.
- `recovered_failures` are failures a later stage handled.
- `published_artifacts` lists what the output modules published.

The same report is written to `build/build_report.json`. The contract is written
to `build/workflow_contract.json` before execution starts, so it exists even
when the run fails.

### Step 2: Find the stage

| Stage | Typical exception | What it means |
| --- | --- | --- |
| writing a binding, projection or row source | `TypeError` | a declaration value is malformed |
| `create_blueprint` | `ValueError` | declarations, names or sources disagree |
| `compile` | `ValueError` or a workflow assembly error | module composition cannot be wired |
| `build` | an unsuccessful report | data, runtime configuration or a module check failed |

A successful `compile` means the declarations are structurally sound. The
remaining problem is input data, runtime configuration or a check inside a
module.

### Step 3: Fix row-source and projection errors

These fail while the plan is built or validated:

| Message | What to change |
| --- | --- |
| `join key expressions must have the same logical type` | Convert one key to the other's base type before joining. Nullability may differ; base type may not. |
| `join keys must be scalar expressions` | Use a scalar member. For a composite key, build one scalar string on each side. |
| `join on must return a (left key, right key) pair or one equals expression` | Return a two-item tuple of scalar inputs, or one text `equals` expression. |
| `union row sources must have the same shape` | Make external names, logical types and nullability identical. Rename, cast or narrow through projections; a union never adapts a shape. |
| `group_by keys must be scalar expressions` | Use a scalar member, not an array or struct. |
| `group_by key names must be unique` | Rename one key in the `by` mapping. |
| `group_by key names must be Python identifiers` | Use a public name such as `status`, not a display label. |

A null join key never matches. If an inner join returns fewer rows than
expected, inspect the key column for nulls; choose an outer join, default the key
deliberately, or filter the row. A null group key drops the row before grouping.
Default the key before `group_by` when a placeholder group is correct.

A projection has one row plan. Prefer pinning it at class creation:

```python
class ReadingGrainProjection(Projection(reading_rows)):
    reading_id = computed_field(
        reading_rows.shape.left.extract(
            lambda reading: reading.reading_id,
        ).alter_rows().drop_null()
    )
```

`Projection(source.row_source())` pins a relation. A joined, grouped, unioned or
filtered plan is already a row source, so pass it directly, as
`Projection(reading_rows)`. The compatibility form leaves the class unpinned and
declares outputs with `projection_field(...)`; its plan is derived from the one
source those outputs read. If no single source is derivable, compilation fails
with `projections require a row source`. A projection with no effective output
also fails; declare at least one output. A projection that reads two unrelated
relations fails with `a relational product requires one driving source`; build
the join in the row source and pin the result.

### Step 4: Fix declaration and composition errors

**Duplicate names.** These are declaration errors:

```text
component names must be unique
table names must be unique
projection names must be unique
logical source names must be unique
module IDs must be unique
... fields 'x' and 'y' share external name 'name'
... properties 'x' and 'y' share external name 'name'
```

Give the declaration an explicit name with `NodeOptions(name=...)`,
`EdgeOptions(name=...)`, `TableOptions(name=...)` or
`ProjectionOptions(name=...)`. Rename a field or property with its `name=`
argument. A table and a projection cannot share a logical name because both are
logical relations. Register a module once.

**Missing sources and fields.** These are reference errors:

| Message | What to change |
| --- | --- |
| `no source bound for: x` | Add `bind_source(target=XTable, config=...)` for every table the bindings read. |
| `references unknown logical source 'x'` | Import the table or projection, or check its `options.name`. |
| `references unknown field 'x' on logical source 'y'` | Correct the field name or add the field to the declaration. |
| `expressions reference undiscoverable logical sources: x` | Move the projection inside the discovered namespace, or add the source it reads. |

**Inheritance and category errors.** These are declaration errors too:

```text
a final Table may not inherit from another final Table
a final Projection may not inherit from another final Projection
a final TableGroup may not inherit from another final TableGroup
... cannot inherit from concrete graph component ...
... has more than one abstract category parent: ...
table groups must declare at least one member
```

Final declarations are terminal. Share source fields with `StructTemplate`,
share rows with `projection_base()`, and share topology through one category
parent plus templates. A category is a parent, not a base to instantiate; bind a
concrete descendant.

**Other frequent declaration errors.** These usually fail when the binding is
written or compiled:

| Message | What to change |
| --- | --- |
| `build_key must not be nullable` | Narrow it with `alter_rows().drop_null()`, or default it deliberately. |
| `build_key must be a scalar` | Use a scalar member, or turn a flat array into text with `concat`. |
| `... must be assigned a value selection or expression` | Assign every declared property, including inherited ones. Remove the property from the component if this graph does not use it. |
| `source_node must name the declared endpoint category ...` | Pass `endpoint(ConcreteNode)` for the abstract side. |
| `... must equal or descend from the declared endpoint category` | Name a concrete node that descends from the category. |
| `edge component '...' requires bound source and target node components` | Bind and export both endpoint node components for the target. |
| `workflow cannot be assembled` or `no candidate producer` | A step reads an artifact no module writes. Remove a module registered for an unbound component, or fix the binding that should produce it. |
| `nothing reads ...` | A rewriting module is after the output modules. Move it before them or remove it. |

An edge key that matches no node key is not checked at build time. The edge is
written anyway and fails when a graph database imports it. Use the same
expression on both sides:

```python
build_key=row.site_id.alter_rows().drop_null().expression.prepend("site::")
source_build_key=(
    row.site_id.alter_rows().drop_null().expression.prepend("site::")
)
```

### Step 5: Inspect a build that succeeds but writes the wrong records

A successful build can still have the wrong grain, duplicate keys or an edge
that points at no node. Count the records before reading individual rows:

```python
import json
from collections import Counter
from pathlib import Path

rows = [
    json.loads(line)
    for line in Path("build/graph.jsonl").read_text().splitlines()
]
print(Counter((row["kind"], row["type"]) for row in rows))

keys = Counter(
    row["build_key"] for row in rows if row["type"] == "reading"
)
print({key: count for key, count in keys.items() if count > 1})
```

Use `meta_graph.json` for exact counts per component and category. An exact
multiple of the expected count is fan-out; zero usually means a filter, a
missing source, or the wrong namespace.

Fan-out has no single message. Look for an `alter_rows().expand()` before the
binding, a join that matched more than one row, or several bindings targeting
one component. Move the repeated grain into its own projection or binding. Use
`CollapseExactDuplicatesModule` for identical rows and
`MergeCompatibleFactsModule` for compatible same-key facts only when the rows
really are one fact.

### Where to look

| File or value | What it tells you |
| --- | --- |
| `build/build_report.json` | the same failures, artifacts and provenance as the returned report |
| `build/workflow_contract.json` | the modules, steps and configuration that ran |
| `build/graph.jsonl` | node and edge records, build keys and endpoint keys |
| `build/meta_graph.json` | effective topology, exact record counts and example values |
| `contract.contributions` and `contract.connections` | the compiled steps and their wiring |
| `blueprint.graph.nodes`, `blueprint.graph.edges` and `blueprint.bindings` | what the build will target and read |

Inspect the blueprint when a component or binding is missing:

```python
print([(node.name, node.abstract) for node in blueprint.graph.nodes])
print([(node.name, node.abstract) for node in blueprint.graph.edges])
print([(binding.component, getattr(binding, "debug_name", None)) for binding in blueprint.bindings])

for binding in blueprint.bindings:
    if binding.component == "reading":
        print(binding.identity, binding.rows)
```

The blueprint can be passed back to `compile(blueprint=..., modules=...)`;
supply the modules again because they define the work.

## Verify

After a fix, run the three calls again:

```python
blueprint = create_blueprint()
contract = compile(blueprint=blueprint, modules=modules)
report = build(contract, output_directory=Path("build"), monitor=False)
```

Check that:

- `create_blueprint` and `compile` complete without an exception.
- `report.succeeded` is true and `report.unresolved_failures` is empty.
- The record count per component matches the intended grain.
- No build key repeats more often than one record should.
- Every edge endpoint key exists in the target component's records.

For a focused check, run a smoke build with `FileModule` only, then add the
other output modules after the counts are correct. See
[Compile, build and outputs](../concepts/build-and-outputs.md).

## Troubleshoot

| Symptom | What to do |
| --- | --- |
| The same exception appears before any data is read | Fix the declaration or expression. `build` cannot repair a compile error. |
| The report is unsuccessful but no file appears | Read `unresolved_failures` and `workflow_contract.json`. The failure names the module and step. |
| The graph file is missing | The output module is not registered, its path is relative to the output directory, or its step failed. Check `published_artifacts`. |
| The record count is an exact multiple | Find the expansion or many-side join that multiplied the rows. Move it to its own grain. |
| The record count is zero | Check `no source bound for`, the source path, a `drop_null` in a key or property, and the discovered namespace. |
| An edge points at a missing node | The endpoint key expression differs from the node binding, or the node row was filtered out. |
| A required property is null at run time | Default it, make the property nullable, or drop the row deliberately. |
| A validation module reports findings without failing | Inspect the published findings report, fix the data or the binding, then turn `fail_on_error` on. |

## Next steps

- [Join, group and union](relations.md) covers composite keys, null keys and
  named grains.
- [Modelling patterns](patterns.md) covers identity, fan-out and edge endpoints.
- [Bindings](../concepts/bindings.md) explains key and property null handling.
- [Modules](../concepts/modules.md) explains composition and ordering.
- The [compile and build reference](../reference/compile.md) lists the public
  calls and report fields.
- The [bindings reference](../reference/bindings.md) and
  [modules reference](../reference/modules.md) list the declaration and
  composition surfaces behind the messages.
