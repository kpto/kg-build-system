---
title: Row sources reference
summary: "The exact row-source algebra: where, unnest, union, join, group_by, distinct, order_by and generated shapes."
section: reference
perspective: reference
order: 100
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/distribution/languages/data/model/public/row_sources.py
  - kg_build_system/distribution/languages/data/model/public/declarations.py
  - kg_build_system/distribution/languages/data/model/public/shapes.py
  - kg_build_system/distribution/languages/data/service/_private/rows.py
  - kg_build_system/distribution/languages/data/service/_private/shapes.py
---

## Surface

A row source names the rows a binding or derived relation reads and the typed shape of one row. `row_source()`, `where`, `unnest`, `union`, `join`, `group_by`, `distinct` and `order_by` are the authoring algebra; every derived operation returns another row source, so calls compose. A row source is a value, not a declaration class or a schema.

| Operation | Grain effect | Result shape |
| --- | --- | --- |
| `where(predicate)` | Keeps rows whose predicate is true | Unchanged |
| `unnest(selector)` | One row per array item | Selected member narrowed |
| `union(other, all=True)` | Stacks same-shaped rows; `all=False` removes duplicates | Unchanged |
| `join(other, on=..., how="inner")` | Combines two row sources on one equality | `{on, left, right}` |
| `group_by(by=...)` | One row per key; null keys are dropped | `{by, members}` |
| `distinct()` | Removes duplicate rows | Unchanged |
| `order_by(*keys, ascending=True)` | Orders rows | Unchanged |

The model and the choice of grain are on [Set the grain](/book/part-2/05-grain-and-projections), the binding rules on the [Grain spec](/appendix/spec/grain), and the subject index entry for [Grain](/appendix/subjects/grain). The values that read a row are on [Expressions reference](/appendix/reference/expressions); naming a plan is on [Derived relations reference](/appendix/reference/derived-relations). Declarations are on [Declarations](/appendix/reference/declarations), a binding consumes a row-source value on [Bindings](/appendix/reference/bindings), and binding targets are on [Topology](/appendix/reference/topology).

## Details

### `row_source()`

```text
SourceRelation.row_source() -> RelationRowSource[Self]
DerivedRelation.row_source() -> RelationRowSource[Self]
```

Returns the relation row source for a source relation or derived relation. The relation's `.shape` is the shape class of one row.

```python
from kg_build_system import Field, Omitted, SourceRelation, SourceRelationOptions, field


from estate.assets import Estate

class SiteSourceRelation(SourceRelation[Estate]):
    # Contract and field definitions are stated in full on Declarations.
    options = SourceRelationOptions(contract=...)
    site_id: Field[str] = field(meaning=Omitted)
    name: Field[str] = field(meaning=Omitted)
    region: Field[str] = field(meaning=Omitted)


class ReadingSourceRelation(SourceRelation[Estate]):
    options = SourceRelationOptions(contract=...)
    reading_id: Field[str] = field(meaning=Omitted)
    site_id: Field[str] = field(meaning=Omitted)
    region: Field[str] = field(meaning=Omitted)
    value: Field[float] = field(meaning=Omitted)


sites = SiteSourceRelation.row_source()       # RelationRowSource[SiteSourceRelation]
```

A binding takes a row-source **value**. It does not accept a declaration class such as `SourceRelation` or `DerivedRelation`. A `Struct` or `ComputedStruct` is not a row source. A `Stage` returns a `StageRowSource`, which a binding refuses.

| Error | Trigger |
| --- | --- |
| `rows must be a published row source value; use SourceRelation.row_source() or DerivedRelation.row_source()` | A row-source operation receives a declaration class, a stage or another non-value |
| `rows must be a published row source value; use SourceRelation.row_source()` | A binding factory receives a non-row-source value or a stage |

### The algebra

Every derived operation returns another row source, so calls compose.

| Operation | Signature | Returns | Shape |
| --- | --- | --- | --- |
| `where` | `where(predicate: Callable[[S], Selection[bool]])` | `DerivedRowSource[S]` | Unchanged |
| `unnest` | `unnest(selector, *, out: type[Out])` | `DerivedRowSource[Out]` | Declared by `out` |
| `union` | `union(other, *, all: bool = True)` | `DerivedRowSource[S]` | Unchanged; `other` is `RowSource[S]` |
| `join` | `join(other, *, on, how="inner")` | `DerivedRowSource[InnerJoinedShape[S, S2, K]]` and the matching left/right/full shape | `{on, left, right}` |
| `group_by` | `group_by(*, keys: type[K], by)` | `DerivedRowSource[GroupedShape[S, K]]` | `{by, members}` |
| `distinct` | `distinct()` | `DerivedRowSource[S]` | Unchanged |
| `order_by` | `order_by(*keys, ascending: bool = True)` | `DerivedRowSource[S]` | Unchanged |
| `custom_op` | `custom_op(operation, **parameters)` | `DerivedRowSource[Out]` | Declared by the relation operation |

### `where()`

```text
RowSource.where(
    predicate: Callable[[S], Selection[bool]],
) -> DerivedRowSource[S]
```

Keeps rows whose predicate is true. The predicate receives a typed row proxy, not the declaration class, and must return a `Selection[bool]`.

| Parameter | Type | Meaning |
| --- | --- | --- |
| `predicate` | `Callable[[S], Selection[bool]]` | Receives the row proxy and returns a row predicate |

```python
depots = SiteSourceRelation.row_source().where(
    lambda site: site.name.alter_rows().drop_null().equals("Depot")
)
```

A source field reads as nullable, so narrow or default it before comparing. A null predicate is not true, so its row is dropped.

| Error | Trigger |
| --- | --- |
| `where requires a callable predicate` | A bare selection is passed |
| `where predicates must return a Selection[bool]` | The callable returns another type |

### `unnest()`

```text
RowSource.unnest(
    selector: Callable[[S], Selection[Array[I]] | Selection[Nullable[Array[I]]]],
    *,
    out: type[Out],
) -> DerivedRowSource[Out]
```

Expands one direct array member into rows, one row per item. The result keeps every other field and narrows the selected field to its item shape. A null or empty array produces no rows.

The output shape cannot be derived from `S`: one named member changes type. Declare it with `out`:

```python
from kg_build_system import Nullable, Selection, Shape

from estate.relations import SiteTags


class TaggedSite(Shape):
    site_id: Selection[Nullable[str]]
    tag: Selection[str]


one_tag_per_row = SiteTags.row_source().unnest(
    lambda site: site.tags,
    out=TaggedSite,
)
```

The runtime validates `out` against the generated shape: every member, external name and logical type. The narrowed member reads exactly:

```python
from kg_build_system import Omitted
from kg_build_system import DerivedRelation, DerivedRelationOptions, computed_field


class TagDerivedRelation(DerivedRelation(one_tag_per_row)):
    # Contract and output definitions are stated in full on Derived relations.
    options = DerivedRelationOptions(contract=...)
    site_id = computed_field(
        one_tag_per_row.shape.site_id,
        meaning=Omitted,
    )
    tag = computed_field(one_tag_per_row.shape.tag, meaning=Omitted)
```

`unnest` is the row-source spelling of expansion. `Selection.expand` remains a selection row effect for a product that already reads the row.

| Error | Trigger |
| --- | --- |
| `unnest requires a callable selector` | `selector` is not callable |
| `unnest selectors must return an array Selection` | The selector returns a non-array |
| `unnest requires a selector that reads one declared field` | The selector reads a computed expression rather than a direct field |
| `unnest field 'x' is not a member of its input shape` | The selected field is not a member of the source shape |

### `union()`

```text
RowSource.union(
    other: RowSource,
    *,
    all: bool = True,
) -> DerivedRowSource[S]
```

Concatenates two row sources with the same shape. `all=False` removes duplicate rows.

| Parameter | Type | Meaning | Default |
| --- | --- | --- | --- |
| `other` | row-source value | The right operand | Required |
| `all` | `bool` | Keep duplicates | `True` |

Shapes are compared member by member: external name and full logical type, including nullability. A union never renames, casts or reorders columns.

```python
# ArchivedSiteSourceRelation declares the same fields as SiteSourceRelation.
everyone = SiteSourceRelation.row_source().union(ArchivedSiteSourceRelation.row_source())
```

| Error | Trigger |
| --- | --- |
| `union row sources must have the same shape` | A member name, type or nullability differs |

### `join()`

```text
RowSource.join(
    other: RowSource[S2],
    *,
    on: Callable[[S, S2], tuple[Selection[K], Selection[K]]],
    how: Literal["inner", "left", "right", "full"] = "inner",
) -> DerivedRowSource[InnerJoinedShape[S, S2, K]]
   | DerivedRowSource[LeftJoinedShape[S, S2, K]]
   | DerivedRowSource[RightJoinedShape[S, S2, K]]
   | DerivedRowSource[FullJoinedShape[S, S2, K]]
```

Combines two row sources on one equality. `on` receives one row proxy per side and returns `(left_key, right_key)`, a pair of scalar selections.

| Parameter | Type | Meaning | Default |
| --- | --- | --- | --- |
| `other` | `RowSource[S2]` | The right side; `S2` is inferred | Required |
| `on` | callable | Returns the two key selections | Required |
| `how` | `"inner"`, `"left"`, `"right"` or `"full"` | Which side may be unmatched | `"inner"` |

Keys must resolve to the same base logical type; their nullability may differ. Arrays and structs are refused. Null keys never match in any join mode. `K` is inferred from the key pair; `how` selects the returned shape and its nullability.

```python
site_readings = SiteSourceRelation.row_source().join(
    ReadingSourceRelation.row_source(),
    on=lambda site, reading: (site.site_id, reading.site_id),
    how="left",
)
# DerivedRowSource[LeftJoinedShape[SiteSourceRelation, ReadingSourceRelation, str]]
```

The generated shape is precise:

| Member | Inner | Left | Right | Full |
| --- | --- | --- | --- | --- |
| `on` | `Selection[K]` | `Selection[Nullable[K]]` | `Selection[Nullable[K]]` | `Selection[Nullable[K]]` |
| `left` | `Selection[S]` | `Selection[S]` | `Selection[Nullable[S]]` | `Selection[Nullable[S]]` |
| `right` | `Selection[S2]` | `Selection[Nullable[S2]]` | `Selection[S2]` | `Selection[Nullable[S2]]` |

```python
site_name = site_readings.shape.left.extract(lambda site: site.name)
reading_value = site_readings.shape.right.extract(
    lambda reading: reading.value,
)
```

`extract` accepts the source row shape, so the join record is read without a cast.

| Error | Trigger |
| --- | --- |
| `join on must be a callable returning a key pair` | `on` is not callable |
| `join on must return a (left key, right key) pair` | The callable returns a non-pair value |
| `join key expressions must have the same logical type` | The two keys differ in base type |
| `join keys must be scalar expressions` | A key is an array or struct |
| `join key expressions must have the same logical type` | The pair resolves to different base types |
| `join keys must be scalar expressions` | A key is an array or struct |
| `join how must be 'inner', 'left', 'right', or 'full'` | `how` is another value |

### `group_by()`

```text
RowSource.group_by(
    *,
    keys: type[K],
    by: Callable[[S], Mapping[str, Selection[Nullable[ScalarValue]]] | Sequence[tuple[str, Selection[Nullable[ScalarValue]]]] | Selection[Nullable[ScalarValue]]],
) -> DerivedRowSource[GroupedShape[S, K]]
```

Groups rows by one or more scalar selections. `keys` declares the present key shape; `by` returns one key selection (named `key`), a mapping of names to selections, or `(name, selection)` pairs. The generated grouped shape is derived; only the key shape is declared.

```python
from kg_build_system import Nullable, Selection, Shape


class SiteRegionKey(Shape):
    region: Selection[str]


by_region = SiteSourceRelation.row_source().group_by(
    keys=SiteRegionKey,
    by=lambda site: {"region": site.region},
)

# DerivedRowSource[GroupedShape[SiteSourceRelation, SiteRegionKey]]
region = by_region.shape.by.extract(lambda key: key.region)  # Selection[str]
members = by_region.shape.members                            # Selection[Array[SiteSourceRelation]]
```

Rows whose key tuple contains a null are dropped before grouping, so every generated `by` member is present. Key names must be public Python identifiers and unique within the group, and must name exactly the members of `keys`; keys must be scalar selections.

`members` is an array of generated record mirrors of the input row. Member order is unspecified, and grouping only collects members: count, sum and having aggregates do not exist. A binding over a grouped source emits one record per group, not one per input row.

| Error | Trigger |
| --- | --- |
| `group_by by must be a callable` | `by` is not callable |
| `group_by requires at least one key` | The callable returns no key |
| `group_by keys must name exactly the members of its key shape` | A key name is missing or extra |
| `group_by key names must be Python identifiers` | A key name is not an identifier |
| `group_by key names must be unique` | Two keys share a name |
| `group_by keys must be scalar expressions` | A key is an array or struct |
| `generated shape member '_name' must be a public Python identifier` | A key name starts with `_` |

### `distinct()` and `order_by()`

```text
RowSource.distinct() -> DerivedRowSource[S]

RowSource.order_by(
    *keys: str | Selection[object] | Callable[[S], Selection[object]],
    ascending: bool = True,
) -> DerivedRowSource[S]
```

`distinct()` removes duplicate rows without changing the shape.

`order_by()` orders rows by one or more keys. A key may be a column name, a selection, or a callable receiving the row proxy. One direction applies to every key. Row order is observable only through later ordering or a materialised relation.

```python
recent = (
    SiteSourceRelation.row_source()
    .where(lambda site: site.name.alter_rows().drop_null().equals("Depot"))
    .distinct()
    .order_by("region", ascending=True)
)
```

| Error | Trigger |
| --- | --- |
| `order_by requires at least one key` | No key is supplied |
| `order_by column 'x' is not a member of the row source` | A string key is not an external member name |
| `order_by keys must be expressions or column names` | A key is another value |

### Relation operations

A value operation computes one value for one row. A **relation operation** consumes one row source and produces one row source with a declared output shape and grain. It is the surface for a grain-changing operation, such as a global count.

```python
from kg_build_system import RelationOperation, RelationOperationSpec, Selection, Shape


class CountRow(Shape):
    count: Selection[int]


COUNT_ROWS = RelationOperationSpec(
    name="count_rows",
    output=CountRow,
    grain="one_total",
)
count_rows = RelationOperation(COUNT_ROWS)

counts = EventSourceRelation.row_source().custom_op(count_rows)
# DerivedRowSource[CountRow]
```

| Field | Meaning |
| --- | --- |
| `name` | The operation identity carried by the plan node and the emitter. |
| `output` | The declared output shape; every member is a present `Selection[...]`. |
| `grain` | `one_per_input_row`, `one_per_group` or `one_total`. |
| `parameters` | Optional JSON values; the typed call accepts only JSON parameters in this version. |

The plan carries a `RowOperationDTO`: the operation name, one input plan, the parameters, the output shape fields and the grain. The engine supplies the SQL emitter:

```python
from kg_build_system.distribution.languages.data.model.internal.dto import (
    RowOperationDTO,
)
from kg_build_system.distribution.modules.duckdb import (
    DuckDbInstructionEmitter,
    DuckDbSqlEmitter,
)


class CountRowsEmitter:
    node_type = RowOperationDTO

    def emit(self, plan, context):
        return f"SELECT COUNT(*) AS count FROM {context.relation_for(plan.input)}"


engine = DuckDbSqlEmitter(
    instruction_emitter=(
        DuckDbInstructionEmitter().with_row_sources(CountRowsEmitter())
    ),
)
```

`RowSourceEmitter`, `RowSourceEmissionContext` and `SqlNode` are public from `kg_build_system.distribution.modules.duckdb`. The emitter is registered by exact `node_type`; no dispatcher edit and no registry.

A relation operation is not a published relation by itself. Its output is plan-local; a `Stage` or `DerivedRelation` must publish it with a `Definition` whose grain agrees with the operation's grain. The runtime validates the generated output members against `output` and the plan node against its declared grain.

Limits: one input row source, JSON parameters only, and no arbitrary expression arguments in this version. These are the first surface, not a permanent restriction.

### Generated shapes

`join` produces `{on, left, right}` and returns `InnerJoinedShape`, `LeftJoinedShape`, `RightJoinedShape` or `FullJoinedShape`, selected by `how`:

| Member | Type | Nullability |
| --- | --- | --- |
| `on` | `Selection[K]` for `inner`; `Selection[Nullable[K]]` for an outer join | Present for an inner join; nullable for an outer join |
| `left` | `Selection[S]` for `inner`/`left`; `Selection[Nullable[S]]` for `right`/`full` | By join mode |
| `right` | `Selection[S2]` for `inner`/`right`; `Selection[Nullable[S2]]` for `left`/`full` | By join mode |

`left` and `right` are generated records; read their members with `extract`. A join may consume another join or group and nest its generated records.

```python
key = site_readings.shape.on
site_name = site_readings.shape.left.extract(lambda left: left.name)
reading_value = site_readings.shape.right.extract(lambda right: right.value)
```

`group_by` produces `{by, members}` and returns `GroupedShape[S, K]`:

| Member | Type | Nullability |
| --- | --- | --- |
| `by` | `Selection[K]`, the declared key shape | Every key member is present |
| `members` | `Selection[Array[S]]` | Present array; item order unspecified |

`by.extract(...)` needs no `drop_null()`. The `members` array is read like any other array:

```python
site_ids = by_region.shape.members.transform_items(
    lambda member: member.extract(lambda item: item.site_id)
).drop_null_items()
```

`unnest` returns `DerivedRowSource[Out]`; `out` declares the narrowed shape. The runtime validates the generated members against it.

### Types and limits

`SourceRelation.row_source()` and `DerivedRelation.row_source()` return a `RelationRowSource[Self]`, and a `Stage` returns a `StageRowSource[Self]`. Reading a field through `.shape` is typed by the declaration's field selections; `.shape` is a generated view at runtime, so it carries the same fields but is not the declaration class itself. A stage row source is not bindable. Every derived operation returns a `DerivedRowSource`; both are frozen row-source values with a `.shape`.

| Operation | Static result |
| --- | --- |
| `where`, `union`, `distinct`, `order_by` | `DerivedRowSource[S]` with the input shape |
| `unnest` | `DerivedRowSource[Out]` declared by `out` |
| `join` | `DerivedRowSource[InnerJoinedShape[S, S2, K]]`, `LeftJoinedShape`, `RightJoinedShape` or `FullJoinedShape` |
| `group_by` | `DerivedRowSource[GroupedShape[S, K]]` |

A generated `join`, `group_by` or `unnest` shape is statically typed. `join` and `group_by` derive it from the inputs and keys; `unnest` requires `out=Out` because the type system cannot replace one named member. The runtime validates every generated member, external name and logical type against the static shape.
