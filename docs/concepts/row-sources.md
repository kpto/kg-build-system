# Row sources

A row source is a value that describes one relation of rows: the shape of a row
and the filters, joins, unions, groups and ordering that produce it.

Your data contract says what a row looks like, and the asset it names says which
logical source the rows belong to. A binding still has to answer a third
question: which rows become this record? A row source is that answer. It makes
the grain explicit, lets one plan feed several consumers, and keeps every filter
and join visible where you write it.

## The grain is a decision

A **grain** is what one row represents. `SiteTable` has one row per site,
`UnitTable` one row per unit, and `DefectTable` one row per defect.

A `DefectNode` needs the defect grain. A `HAS_DEFECT` edge needs one row per unit-and-defect pair. The same input therefore supports several grains. The choice belongs to the build, not to the input file, and a row source records it.

## The model

`Table.row_source()` starts from a data contract; `Projection.row_source()` starts
from a named relation. Both return a row source that you pass to `rows=` or pin
to a projection.

A row source is a value, not a declaration class. Every operation returns another
row source, so the operations compose:

- `where`, `union`, `distinct`, `order_by` and `unnest` preserve or narrow the
  shape of the rows.
- `join` and `group_by` generate a new shape because the row genuinely has new
  members.

The same operations are available on a table relation, a projection relation and
any derived source. A projection relation is not a special case.

A row source's shape is the type of one row. Inside an operation you receive a
**row proxy**: a typed symbolic object whose fields you read as attributes. It is
not data and not a dictionary. Binding lambdas and row-source lambdas both
receive this proxy.

!!! warning "Pass a row-source value"
    Write `UnitTable.row_source()`. A binding accepts only a row-source value;
    a declaration class is refused. A `Struct` is a shape, not a row source.

## Start from a table

The pages in this guide use the same small survey model. A site has units, and a unit has defects. A defect carries its observations as a nested array.

```python
from kg_build_system import Array, Field, Nullable, Struct, Table, field


class ObservationStruct(Struct):
    observation_uid: Field[str] = field()
    value: Field[float] = field()


from estate.assets import Estate

class SiteTable(Table[Estate]):
    site_id: Field[str] = field()
    name: Field[str] = field()
    region: Field[str] = field()


class UnitTable(Table[Estate]):
    site_id: Field[str] = field()
    unit_ref: Field[str] = field()
    unit_name: Field[str] = field()
    in_service: Field[bool] = field()
    status: Field[str] = field()
    survey_period: Field[str] = field()


class DefectTable(Table[Estate]):
    defect_id: Field[str] = field()
    unit_ref: Field[str] = field()
    title: Field[str] = field()
    severity: Field[str] = field()
    observations: Field[Array[Nullable[ObservationStruct]]] = field()
```

The unit relation is the table's own grain:

```python
unit_rows = UnitTable.row_source()
```

Pass it to a binding as `rows=unit_rows`. If you need the unit grain under a name
that other declarations can share, pin it to a projection; the
[projections](projections.md) page covers that.

## Filter, deduplicate and order

`where` takes a callable that receives a row proxy and returns a
`Selection[bool]`. A source field reads as nullable, so narrow or default it
before comparison:

```python
active_units = UnitTable.row_source().where(
    lambda unit: unit.status.alter_rows().drop_null().equals("active")
)
```

`distinct()` removes duplicate rows without changing the shape. `order_by(*keys)`
orders rows by column names, selections or callables. One `ascending` value
applies to every key, and row order is only observable through a later ordering
or a materialised relation.

A one-off filter belongs in the binding's row source. When several bindings need
the same filtered grain, name it with a projection instead.

## Expand an array with unnest

`unnest(selector)` expands one direct array field into rows and preserves every
other member of the source row. It is the row-source spelling of expansion; a
selection's `alter_rows().expand()` is the row effect for a product that already
reads the row.

```python
one_tag_per_row = UnitTable.row_source().unnest(lambda unit: unit.tags)
```

The selected field is narrowed to its item type. A null or empty array produces
no rows. Everything else in the row is repeated. Use `unnest` when the expanded
array *is* the grain of the relation; use a selection expand when the expansion
is internal to one product.

## Combine rows with union

`union(other, all=True)` stacks two row sources. `all=False` removes duplicates
from the result.

Both sides must have the same shape: the same members, external names and full
logical types, including nullability. A union never renames, casts or reorders
columns. If the shapes differ, the build refuses the union rather than guessing
which column you meant.

```python
active = UnitTable.row_source().where(
    lambda unit: unit.status.alter_rows().drop_null().equals("active")
)
retired = UnitTable.row_source().where(
    lambda unit: unit.status.alter_rows().drop_null().equals("retired")
)

all_units = active.union(retired)
```

## Join two grains

`join` combines two row sources on one equality. The callable receives one row
proxy per side and returns a pair of keys:

```python
unit_defects = UnitTable.row_source().join(
    DefectTable.row_source(),
    on=lambda unit, defect: (unit.unit_ref, defect.unit_ref),
)
```

The result has the generated shape `{on, left, right}`:

- `on` is the shared key value.
- `left` is the left input record.
- `right` is the right input record.

The records are generated structs. Read their members with `extract`, just as you
would for a declared struct:

```python
defect_title = unit_defects.shape.right.extract(lambda defect: defect.title)
```

A join key must be a scalar selection, and both sides must resolve to the same
base logical type. Their nullability may differ. Arrays and structs are not join
keys.

A null key never matches, in any join mode, because the join uses plain equality.
A left row with a null key and a right row with a null key stay unmatched, even
in a full join.

`how` selects which unmatched rows survive:

| Value | Rows kept |
| --- | --- |
| `inner` | Only matched pairs |
| `left` | Every left row, matched or not |
| `right` | Every right row, matched or not |
| `full` | Every row from both sides |

The generated records follow the join mode. `right` is nullable for a left join,
`left` is nullable for a right join, and both are nullable for a full join. `on`
is non-null for an inner join; for an outer join it is nullable when the key on a
side that `how` can leave unmatched is nullable.

### The text equality form

Instead of a key pair, `on` may return one `equals` selection. `equals` exists
only on text, so the form is text-only and needs present text on both sides:

```python
matched = UnitTable.row_source().join(
    DefectTable.row_source(),
    on=lambda unit, defect: (
        unit.unit_ref.default_to("").equals(
            defect.unit_ref.default_to("")
        )
    ),
)
```

Narrowing each side with `default_to` makes two null keys compare equal. That
differs from the key-pair form, where null keys never match. Use the pair form for
non-text keys and when null keys must stay distinct.

A join may consume another join or group. In a second join, the first generated
record becomes one side, so `row.left` can itself be a `{on, left, right}` record.

## Read another relation by key

A projection often needs one value from a second relation. `lookup` reads every
target record whose key equals this row's key and returns a nullable array of
target records:

```python
class UnitWithSiteProjection(Projection(UnitTable.row_source())):
    unit_ref = computed_field(UnitTable.unit_ref.alter_rows().drop_null())
    site_name = computed_field(
        UnitTable.site_id.lookup(SiteTable, UnitTable.site_id)
        .alter_rows().drop_null()
        .alter_rows().expand()
        .extract(lambda site: site.name)
    )
```

The lookup is a value operation, not a row-level join. Compose the grain from its
result: leave it as a nullable array for a left read, `drop_null()` for an inner
read, and `expand()` for one row per match. See
[lookup](expressions.md#read-another-relation-with-lookup).

## Group rows

`group_by(by=...)` produces one row per distinct key. The result has the generated shape `{by, members}`:

```python
by_severity = DefectTable.row_source().group_by(
    by=lambda defect: {"severity": defect.severity},
)
```

`by` returns one key selection, a mapping of names to selections, or a sequence
of `(name, selection)` pairs. A single selection is named `key`. Key names must
be public Python identifiers and unique within the group, and each key must be
scalar.

Rows whose key tuple contains a null are dropped before grouping. Every generated
key member is therefore present, and `row.by.extract(...)` needs no
`alter_rows().drop_null()`.

`members` is an array of generated records that mirror the input row. Member
order is unspecified. Grouping only collects rows; the algebra has no `count`,
`sum` or `having`.

A binding over a grouped source emits one record per group, not one per input row,
because the group has already collapsed the rows.

## Generated shapes and static typing

`join` and `group_by` build a shape while your module is imported. At edit time the result is a `DerivedRowSource[Any]`, so pyright does not list `on`, `left`, `right`, `by` or `members` as static members of the generated shape. The fields and their logical types exist at runtime, and your callables and computed fields are checked against them there. Input table and projection shapes stay statically typed. `unnest` also returns a generated shape, so read its narrowed member through `.shape`.

## Name a derived grain

Pass a derived source directly to a binding for one-off use. When more than one
consumer needs it, pin it to a projection:

```python
class UnitDefectProjection(Projection(unit_defects)):
    """One row per defect, with the unit it belongs to."""

    defect_id = computed_field(
        unit_defects.shape.right.extract(lambda defect: defect.defect_id)
        .alter_rows().drop_null()
    )
```

A projection pinned to a derived source starts without inherited outputs, so
declare them with `computed_field`. The [projections](projections.md) page
explains the output rules.

## Limits

- `join` keys must be scalar and share a base logical type. Null keys never match.
- `equals` is text-only. Use the key-pair form for other types.
- `group_by` has no aggregates and no guaranteed member order. Its keys are present and uniquely named, and null-key rows are dropped before grouping.
- `union` requires the same shape, member by member, including external names and nullability.
- `order_by` applies one direction to every key.
- A generated join, group or unnest shape is typed at runtime but is not exposed as static members; read it through `.shape`.
- `unnest` selects one direct array field; use `extract` first to reach an array inside a struct.

## What to remember

- A row source is a value; a declaration class is not one.
- The grain is the answer to "what is one row?", and the row source records it.
- `where`, `union`, `distinct`, `order_by` and `unnest` preserve or narrow the shape; `join` and `group_by` generate one.
- A null join key never matches; `equals` is text-only and needs present text.
- Group keys are present, and grouping does not aggregate.
- `lookup` reads a second relation by key without turning it into a scan of the product.

## Next steps

- [Projections](projections.md) give a reusable grain a name and typed outputs.
- [Bindings](bindings.md) consume a row source and produce graph records.

## Reference

[Row sources reference](../reference/row-sources.md) lists every operation, its arguments, the generated shapes and the errors.
