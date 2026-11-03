# Join, group and union relations

Combine row sources when one record needs facts from two relations, when one
record represents a group, or when several same-shaped sources feed one
relation.

## Before you begin

- Know the grain of each source: what one row means. See
  [Row sources and grain](../concepts/row-sources.md).
- Know the properties each target component declares. See
  [Topology](../concepts/topology.md).
- Decide whether you are producing one record from two relations (`join`), one
  record per group (`group_by`), or one relation from same-shaped sources
  (`union`).
- Read [Bindings](../concepts/bindings.md) and
  [Projections](../concepts/projections.md) before you publish a combined grain.

The examples use these declarations:

```python
from kg_build_system import (
    Field, Node, NodeValues, PropertySlot, Projection, Table,
    computed_field, field, node_binding, property,
)


class MeterTable(Table):
    meter_id: Field[str] = field()
    site_id: Field[str] = field()
    label: Field[str] = field()


class ReadingTable(Table):
    reading_id: Field[str] = field()
    site_id: Field[str] = field()
    meter_id: Field[str] = field()
    kwh: Field[float] = field()


class CurrentMeterTable(Table):
    meter_id: Field[str] = field()
    site_id: Field[str] = field()
    label: Field[str] = field()


class RetiredMeterTable(Table):
    meter_id: Field[str] = field()
    site_id: Field[str] = field()
    label: Field[str] = field()


class ReadingNode(Node):
    kwh: PropertySlot[float] = property()
    meter_label: PropertySlot[str | None] = property()


class MeterSummaryNode(Node):
    readings: PropertySlot[str] = property()


class MeterNode(Node):
    label: PropertySlot[str | None] = property()
```

## Steps

### Step 1: Choose the operation that matches the grain

| You need | Use | Result |
| --- | --- | --- |
| values from two relations in one record | `join` | one row per matching pair |
| one record per distinct key | `group_by` | one row per non-null key tuple |
| one relation from sources with the same shape | `union` | rows appended, optionally deduplicated |

Join when the result has the same grain as one side and the other side adds
values. For example, a reading keeps one row per reading and gains its meter's
label.

Bind separately when each relation produces its own record. A source row that
already carries both a site identifier and a unit reference does not need a join
to produce an edge: bind the unit node and the `HAS_UNIT` edge from their own
rows. A join is not a substitute for an edge.

Do not use a join to collect rows. A group is one record per key and uses
`group_by`; a union appends rows and uses `union`.

### Step 2: Join on the key that matches the record

A join has one equality. Use the key pair form for every scalar type:

```python
reading_rows = ReadingTable.row_source().join(
    MeterTable.row_source(),
    on=lambda reading, meter: (reading.meter_id, meter.meter_id),
    how="left",
)
```

The join key is not the graph build key. The join key decides which rows match;
the build key identifies the record that the binding emits. Here the reading
identifier remains the build key:

```python
reading_binding = node_binding(
    target=ReadingNode,
    rows=reading_rows,
    bind=lambda row: NodeValues(
        build_key=row.left.extract(lambda reading: reading.reading_id)
        .alter_rows().drop_null(),
        properties=ReadingNode(
            kwh=row.left.extract(lambda reading: reading.kwh)
            .alter_rows().drop_null(),
            meter_label=row.right.extract(lambda meter: meter.label),
        ),
    ),
)
```

`row.left` and `row.right` are generated records, not row sources. Read their
members with `extract`.

Choose `how` by what should survive:

- `inner` keeps only matching pairs.
- `left` keeps every left row; `right` is nullable when unmatched.
- `right` keeps every right row; `left` is nullable when unmatched.
- `full` keeps both unmatched sides; both records are nullable.

Keys must share a base type. Nullability may differ. A null key never matches in
any mode, so an inner join drops it and an outer join leaves the other side
unmatched. If a missing key should match a placeholder, default both sides
deliberately before joining; otherwise filter the row or accept the unmatched
result.

For a composite natural key, build one scalar key on each side with the same
expression. The pair form accepts that scalar; there is no multi-key join:

```python
on=lambda reading, meter: (
    reading.site_id.alter_rows().drop_null()
    .expression.prepend("site::").append("::meter::")
    .append(reading.meter_id.alter_rows().drop_null().expression),
    meter.site_id.alter_rows().drop_null()
    .expression.prepend("site::").append("::meter::")
    .append(meter.meter_id.alter_rows().drop_null().expression),
)
```

Use the text-only `equals` form only when both sides are present text. It is
narrower than the pair form and it makes null handling a choice at the
expression, not a property of the join.

### Step 3: Group on scalar, non-null keys

`group_by` produces `{by, members}`. The key names become fields of `by`; rows
whose key tuple contains a null are dropped before grouping. The generated key
members are therefore non-null, so do not add `drop_null()` to a key read.

```python
by_meter = ReadingTable.row_source().group_by(
    by=lambda reading: {"meter_id": reading.meter_id},
)

meter_summary_binding = node_binding(
    target=MeterSummaryNode,
    rows=by_meter,
    bind=lambda row: NodeValues(
        build_key=row.by.extract(lambda key: key.meter_id),
        properties=MeterSummaryNode(
            readings=row.members
            .transform_items(
                lambda member: member.extract(
                    lambda item: item.reading_id,
                )
            )
            .drop_null_items()
            .sort()
            .concat("|"),
        ),
    ),
)
```

Group keys must be scalar, public Python identifiers, and unique within the
group. A group collects members; it does not aggregate them. There is no count,
sum or `having`. If an absent key should form its own group, default it before
grouping:

```python
by_meter_with_placeholder = ReadingTable.row_source().group_by(
    by=lambda reading: {
        "meter_id": reading.meter_id.default_to("unmetered"),
    },
)
```

Member order is unspecified. Sort the transformed members before `concat` when
the output must be stable.

### Step 4: Union only identical shapes

`union` compares external names, logical types and nullability member by member.
Both sides must have the same shape; a union never renames, casts or reorders
columns.

```python
all_meters = CurrentMeterTable.row_source().union(
    RetiredMeterTable.row_source(),
    all=False,
)

meter_binding = node_binding(
    target=MeterNode,
    rows=all_meters,
    bind=lambda row: NodeValues(
        build_key=row.meter_id.alter_rows().drop_null(),
        properties=MeterNode(label=row.label),
    ),
)
```

`all=True` keeps duplicate rows. `all=False` removes rows that are identical in
every column; it does not deduplicate by build key. Two rows with the same key
and different labels both remain.

When the source shapes differ, publish each side through a projection with the
same outputs. The projection is where a rename, cast or null decision belongs:

```python
class CurrentMeterShape(Projection(CurrentMeterTable.row_source())):
    meter_id = computed_field(
        CurrentMeterTable.meter_id.alter_rows().drop_null()
    )
    label = computed_field(
        CurrentMeterTable.label.default_to("Unlabelled meter")
    )


class RetiredMeterShape(Projection(RetiredMeterTable.row_source())):
    meter_id = computed_field(
        RetiredMeterTable.meter_id.alter_rows().drop_null()
    )
    label = computed_field(
        RetiredMeterTable.label.default_to("Unlabelled meter")
    )


all_meters = CurrentMeterShape.row_source().union(
    RetiredMeterShape.row_source(),
)
```

### Step 5: Publish a joined or grouped grain as a projection

Pass a derived row source directly to `Projection(...)` when more than one
binding needs the same joined or grouped grain. Declare the outputs from the
generated shape.

```python
class ReadingGrainProjection(Projection(reading_rows)):
    """One row per reading, with the meter label when it matches."""

    reading_id = computed_field(
        reading_rows.shape.left.extract(
            lambda reading: reading.reading_id,
        ).alter_rows().drop_null()
    )
    kwh = computed_field(
        reading_rows.shape.left.extract(
            lambda reading: reading.kwh,
        ).alter_rows().drop_null()
    )
    meter_label = computed_field(
        reading_rows.shape.right.extract(lambda meter: meter.label)
    )
```

A grouped source is pinned the same way:

```python
class MeterSummaryProjection(Projection(by_meter)):
    """One row per meter, with its readings collected."""

    meter_id = computed_field(
        by_meter.shape.by.extract(lambda key: key.meter_id)
    )
    readings = computed_field(
        by_meter.shape.members
        .transform_items(
            lambda member: member.extract(
                lambda item: item.reading_id,
            )
        )
        .drop_null_items()
        .sort()
        .concat("|")
    )
```

Bind the projection through its row source. Its outputs carry the type and
nullability declared by `computed_field`:

```python
reading_binding = node_binding(
    target=ReadingNode,
    rows=ReadingGrainProjection.row_source(),
    bind=lambda row: NodeValues(
        build_key=row.reading_id,
        properties=ReadingNode(
            kwh=row.kwh,
            meter_label=row.meter_label,
        ),
    ),
)
```

`derived.projection_base()` is the variant that inherits the generated shape's
fields. Use it when consumers should read `on`, `left`, `right`, `by` or
`members` directly.

## Verify

Compile and run a smoke build, then count the records the combined grain
produced:

```python
import json
from collections import Counter
from pathlib import Path

from kg_build_system import compile, execute
from kg_build_system.distribution import FileConfiguration, FilePlanner

planners = (FilePlanner(FileConfiguration("graph.jsonl")),)
plan = compile(planners=planners)
report = execute(plan, output_directory=Path("build"))
print(report.succeeded, report.unresolved_failures)

rows = [
    json.loads(line)
    for line in Path("build/graph.jsonl").read_text().splitlines()
]
print(Counter(row["type"] for row in rows))
print(Counter(row["build_key"] for row in rows if row["type"] == "reading"))
```

Check four things:

- The joined or grouped component has the expected number of records.
- No build key appears more times than its grain allows.
- An outer join's nullable side produced the properties you expected, including
  nulls where nothing matched.
- A union produced the combined rows, not two separate source shapes.

Add `MetaGraphPlanner` when you want exact counts per component and category
alongside the records. See
[Compile, execute and outputs](../concepts/build-and-outputs.md).

## Troubleshoot

| Message or symptom | What to change |
| --- | --- |
| `join key expressions must have the same logical type` | Convert one key to the other's base type before the join. Nullability may differ; base type may not. |
| `join keys must be scalar expressions` | Use a scalar member, or build one scalar composite key on each side. |
| `join on must return a (left key, right key) pair or one equals expression` | Return a two-item tuple of scalar inputs, or one text `equals` expression. |
| An inner join returned fewer rows than expected | At least one key is null. Use an outer join, default the key deliberately, or filter the row. |
| `union row sources must have the same shape` | Align external names, logical types and nullability with projections. |
| `group_by keys must be scalar expressions` | Use a scalar member, not an array or struct. |
| `group_by key names must be unique` | Rename one key in the `by` mapping. |
| `group_by key names must be Python identifiers` | Use a public name such as `meter_id`, not a display label. |
| A grouped row is missing | Its key tuple contained a null and was dropped. Default the key before grouping if a placeholder group is correct. |
| `projections require a row source` | Pin the plan: `Projection(joined)` or `Projection(grouped)`. An unpinned projection must have outputs that read exactly one source. |
| Duplicate build keys after a join | The join matched more than one row on one side. Decide the grain and move the many side to its own projection or binding. |
| Duplicate build keys after a union | `all=False` removes identical rows, not repeated keys. Fix the key or add a deduplication or merging planner. |

## Next steps

- [Projections](../concepts/projections.md) explains pins and named grains.
- [Bindings](../concepts/bindings.md) explains keys and property null handling.
- [Modelling patterns](patterns.md) covers identity, fan-out and edge endpoints.
- [Debug a build](debug.md) shows how to read the report and inspect counts.
- The [row-source reference](../reference/row-sources.md) lists the operations
  and generated shapes.
- The [projection reference](../reference/projections.md) and
  [binding reference](../reference/bindings.md) list the public declaration
  surface.
