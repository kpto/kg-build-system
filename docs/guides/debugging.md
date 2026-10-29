# Debugging

Failures arrive while a binding is written, while the blueprint is validated, while modules are wired, or while records are evaluated.

| Stage | Typical exception |
| --- | --- |
| writing a binding | `TypeError` |
| creating a blueprint | `ValueError` |
| compiling a contract | `ValueError`, an assembly error |
| running a build | `RuntimeError`, `TypeError`, failed report |

If `compile` succeeds, the declarations and module composition are structurally
sound; the remaining problem is data, runtime configuration, or a module's check.

## Common author errors

### Nullable key

```text
build_key must not be nullable
```

The key expression may be null. Every source field reads as nullable, so this
includes a field declared `Field[str]`. Decide what absence means:

```python
build_key=row.identifier.alter_rows().drop_null()  # drop rows without an identity
build_key=row.identifier.default_to("none")        # keep them under one placeholder
```

`drop_null()` filters the binding's rows, so edges that pointed at those
identities will not find them. `default_to()` keeps the row but gives every
absent identifier the same identity. Prefer a real source identifier.

`build_key must be a scalar` means an array or struct was used. Narrow a nullable
array and turn a flat array into text with
`row.tags.alter_rows().drop_null().sort().unique().concat(":")`, or use one item.

### Missing property

```text
SiteNode.closed_on must be assigned a value selection or expression
```

Every declared property needs a value. An omitted constructor argument leaves the
property declaration in the value object, and the binding factory refuses it.
Assign the property, or remove it from the component if this graph does not use
it.

A hand-assembled binding can instead fail at compile time:

```text
binding 'binding:node:site:...' must map every declared component property exactly once
```

At run time a non-null property is guarded:

```text
site.name is null for build_key site-17
```

A statically non-null expression that nevertheless produces null stops the
build. Fix the expression with `default_to(...)`, make the property nullable, or
narrow the source value with `alter_rows().drop_null()`. Because every source
field reads as nullable, a required property already needs one of those choices
when it is declared.

### Property type mismatch

```text
SiteNode.name expects UnitType(name='str'), but the expression resolves to
UnitType(name='int')
```

The expression's logical type must match the slot. A non-null value may satisfy a
nullable slot; the reverse is not allowed. Convert at the expression layer rather
than changing topology to match the input.

### Join, group and union

These are row-source errors, raised when the plan is built:

```text
join key expressions must have the same logical type
join keys must be scalar expressions
join on must return a (left key, right key) pair or one equals expression
union row sources must have the same shape
group_by keys must be scalar expressions
group_by key names must be unique
group_by key names must be Python identifiers
```

- Join keys must share a base type. Nullability may differ; null keys never
  match. The key-pair form is general, and the `equals` form is text-only.
- A union compares member names, logical types and nullability. Rename, cast or
  narrow in the sources so the shapes are identical; a union never adapts them.
- Group keys must be scalar, public Python identifiers and unique. Rows with a
  null key are dropped before grouping, so the generated `by` members are
  non-null — do not add `drop_null()` to a key read.
- A projection must be pinned: `Projection(source.row_source())` for a relation,
  `Projection(derived)` for a joined, grouped, unioned or filtered plan.

### Projection is not pinned

```text
ElementProjection must be pinned to a row source: Projection(source.row_source())
```

Declare the pin at class creation. A direct `class P(Projection):` is refused,
and so is a projection with no output fields. A derived plan is already a row
source, so pass it directly: `Projection(joined)`.

### Unmatched endpoint

For an abstract declared endpoint, the binding needs a concrete token:

```text
source_node must name the declared endpoint category DocumentedAbstractNode:
pass endpoint(...) for that side
```

Name a concrete component that descends from the category, passing it as
`source_node=endpoint(DefectNode)` and `target_node=endpoint(SurveyVisitNode)` for
the two sides. A token outside the category produces `must equal or descend from
the declared endpoint category`.

An edge key that matches no node key is not checked at build time. The edge is
written anyway and fails later when a graph database imports it. Use the same
expression on both sides:

```python
build_key=row.site_id.alter_rows().drop_null().expression.prepend("site::")
source_build_key=row.site_id.alter_rows().drop_null().expression.prepend("site::")
```

For Neo4j, an endpoint node that is not bound at all fails at compile time:

```text
edge component 'observed_during' requires bound source and target node components
```

### No candidate producer

These are composition errors, not data errors:

```text
workflow cannot be assembled:
  file::write.records:core.graph.node.site takes core/graph.node.site,
  which no other step writes
```

A step declares an input that no registered module produces. With the supplied
modules this usually means a custom module without its producer, or a module
listed for a component the build never binds. Check `{binding.component for
binding in blueprint.bindings}` before suspecting the module.

The companion message is:

```text
nothing reads collapse_exact_duplicates::site.distinct, ...
```

A record-rewriting module produced records that no output consumed. Move it
before the output modules, or remove it. See
[Modules: ordering and composition](../concepts/modules.md#ordering-and-composition).

Two modules competing for the same input make the wiring indeterminate. Register
one, reorder them, or remove the extra producer.

### Fan-out

There is no single message. The symptom is a record count that is a multiple of
the expected count, with repeated build keys in the output.

Look for an `alter_rows().expand()` before the binding. Every expansion
multiplies rows; an expansion inside a property expression multiplies the record
without changing its key. Move it into a projection whose grain is the repeated
thing, or bind that grain separately. If the rows really are the same fact, add
a [deduplication or merge module](../concepts/modules.md); if they differ, fix
the key.

### Duplicate ids

Repeated build keys are allowed by default: the core module unions all bindings
for a component. Two bindings targeting the same node each emit records. Use one
binding at the correct grain, or add `CollapseExactDuplicatesModule` for identical
rows or `MergeCompatibleFactsModule` for compatible facts.

Duplicate declaration names are different:

```text
component names must be unique
table names must be unique
projection names must be unique
logical source names must be unique
module IDs must be unique
... fields 'x' and 'y' share external name 'name'
... properties 'x' and 'y' share external name 'name'
```

Two classes can infer one logical name, such as `RecordNode` and
`RecordAbstractNode`. Name one explicitly with `NodeOptions(name="record_entry")`.
A table and a projection cannot share a logical name because both are logical
relations; a field and its neighbour cannot share an external name even when the
Python attributes differ.

Final and structural inheritance errors are declaration errors too:

```text
a final Table may not inherit from another final Table
a final Projection may not inherit from another final Projection
a final TableGroup may not inherit from another final TableGroup
... cannot inherit from concrete graph component ...
... has more than one abstract category parent: ...
table groups must declare at least one member
```

Use `projection_base()` to reuse a pinned plan, `StructTemplate` to share data
fields, and a category parent plus templates to share topology. A concrete
component is terminal; a category is the parent, not a base to instantiate.

Bindings discovered from one namespace are deduplicated by identity; two
separately written bindings are not. Two bindings targeting one component are
unioned into that component's records; only two *modules* producing one artifact
type make the wiring ambiguous.

## Reading the messages

| Message | Meaning | Fix |
| --- | --- | --- |
| `references unknown field 'x' on logical source 'y'` | the field does not exist | correct the name or add the field |
| `references unknown logical source 'x'` | no table or projection has that name | import it or check `options.name` |
| `expressions reference undiscoverable logical sources: x` | a projection input is outside the namespace | add the source, or move the projection |
| `no source bound for: x` | a required table has no `bind_source` | add the source binding |
| `keys must be non-null scalar expressions` | a key is nullable or composite | narrow it, or build a scalar composite |
| `binding ... targets an incompatible component` | node and edge kinds differ | bind a node to a node |
| `may not target abstract component` | a category is a target | target a concrete descendant |
| `join key expressions must have the same logical type` | the two keys have different base types | align the key types, or convert before joining |
| `join keys must be scalar expressions` | a key is an array or struct | use a scalar member |
| `union row sources must have the same shape` | names, types or nullability differ | make both operands identical |
| `group_by keys must be scalar expressions` | a group key is an array or struct | use a scalar member |
| `group_by key names must be unique` | two keys share a name | rename one key |
| `must be pinned to a row source` | a projection has no pin | use `Projection(source.row_source())` or `Projection(derived)` |
| `share external name` | two fields, outputs or properties collide | rename one externally |
| `a final ... may not inherit ...` | concrete declaration used as a base | share through a template or category |
| `neo4j target cannot export ...` | unsupported property type | change the type or omit Neo4j |

## Inspecting a blueprint

The blueprint is the frozen description before modules run:

```python
blueprint = create_blueprint(modules=modules)
print([(c.kind, c.name, c.abstract) for c in blueprint.components])
print([(p.name, p.logical_type) for p in next(
    c for c in blueprint.components if c.name == "site").properties])
print([(b.component, b.debug_name) for b in blueprint.bindings])
```

To understand a count, read the binding's row source and key:

```python
for binding in blueprint.bindings:
    if binding.component == "site":
        print(binding.row_source, binding.build_key)
```

The blueprint can be passed back to `compile(blueprint=..., modules=...)`; supply
the modules again because they define the work.

## Inspecting a contract

The contract adds module composition and the ordered work each module will do.
Two author-facing handles are enough for most investigations:

```python
contract = compile(blueprint=blueprint, modules=modules)
print(contract.workflow_fingerprint)
print(contract.provenance["compile"]["blueprint_fingerprint"])
```

To see the full plan, read `workflow_contract.json` in the output directory after
a build. That document names the modules, their configuration and the steps that
will run. It is an output, not an input: do not edit it and expect a build to
accept it.

## Smoke builds

Before the full build, compile and run a small graph with one output module:

```python
import json
from collections import Counter
from pathlib import Path

from kg_build_system import BuildRuntime, build, compile
from kg_build_system.modules import (
    FileModule, FileModuleConfiguration, register_module,
)

modules = (register_module(FileModule, FileModuleConfiguration("graph.jsonl")),)
contract = compile(namespace_path=Path("graph_pipeline"), modules=modules)
report = build(contract, BuildRuntime(),
               output_directory=Path("/tmp/kg-smoke"), monitor=False)
print(report.succeeded, report.unresolved_failures)
rows = [json.loads(line) for line in Path("/tmp/kg-smoke/graph.jsonl").read_text().splitlines()]
print(Counter((row["kind"], row["type"]) for row in rows))
print(Counter(row["build_key"] for row in rows if row["type"] == "site"))
```

If no file appears, check `build_report.json` for unresolved failures and
`workflow_contract.json` for the modules that ran. If the build raises, the last
monitor message names the failing step.

For systematic checks, add `MetaGraphModule` and compare its counts with the
source. An exact multiple is fan-out; zero usually means a filter or source path
problem. Run `RejectConflictingNonNullValuesModule` with `fail_on_error=False`
and read any findings report before turning failure on.

## What to remember

- Most failures are one of four things: a nullable key, a missing property, an
  unmatched endpoint, or fan-out.
- Fix the declaration or the expression, not the output.
- Compile first; it catches shape errors before any data is read.
- Use `create_blueprint` and `workflow_contract.json` to see what will run.
- A smoke build with `MetaGraphModule` counts records and exposes fan-out.

Related pages: [Bindings](../concepts/bindings.md),
[Sources](../concepts/sources.md), [Compile and build](../concepts/build.md), and
[Modelling patterns](patterns.md).
