# Row sources

A row source is a value that describes one relation of rows: the shape of a row and the filters, joins, unions, groups and ordering that produce it.

Your data contract says what a row looks like, and a source says where the rows live. A binding still has to answer a third question: which rows become this record? A row source is that answer. It makes the grain explicit, lets one plan feed several consumers, and keeps every filter and join visible where you write it.

## The grain is a decision

A **grain** is what one row represents. `SiteTable` has one row per site, `UnitTable` one row per unit, and `DefectTable` one row per defect.

A `DefectNode` needs the defect grain. A `HAS_DEFECT` edge needs one row per unit-and-defect pair. The same input therefore supports several grains. The choice belongs to the build, not to the input file, and a row source records it.

## The model

`Table.row_source()` starts from a data contract; `Projection.row_source()` starts from a named relation. Both return a row source that you pass to `rows=` or pin to a projection.

A row source is a value, not a declaration class. Every operation returns another row source, so the operations compose:

- `where`, `union`, `distinct` and `order_by` preserve the shape of the rows.
- `join` and `group_by` generate a new shape because the row genuinely has new members.

The same operations are available on a table relation, a projection relation and any derived source. A projection relation is not a special case.

A row source's shape is the type of one row. Inside an operation you receive a **shape instance**: a symbolic object whose fields you read as attributes. It is not data and not a dictionary.

!!! warning "Prefer a row-source value"
    Row-source operations take a value, so write `UnitTable.row_source()`. A
    binding also accepts `rows=UnitTable` and converts it to `row_source()` for
    compatibility, but the explicit value states the plan. A `Struct` is a shape,
    not a row source.

## Start from a table

The pages in this guide use the same small survey model. A site has units, and a unit has defects. A defect carries its observations as a nested array.

```python
from kg_build_system import Array, Field, Struct, Table, field


class ObservationStruct(Struct):
    observation_uid: Field[str] = field()
    value: Field[float] = field()


class SiteTable(Table):
    site_id: Field[str] = field()
    name: Field[str] = field()
    region: Field[str] = field()


class UnitTable(Table):
    site_id: Field[str] = field()
    unit_ref: Field[str] = field()
    unit_name: Field[str] = field()
    in_service: Field[bool] = field()
    status: Field[str] = field()
    survey_period: Field[str] = field()


class DefectTable(Table):
    defect_id: Field[str] = field()
    unit_ref: Field[str] = field()
    title: Field[str] = field()
    severity: Field[str] = field()
    observations: Field[Array[ObservationStruct | None]] = field()
```

The unit relation is the table's own grain:

```python
unit_rows = UnitTable.row_source()
```

Pass it to a binding as `rows=unit_rows`. If you need the unit grain under a name that other declarations can share, pin it to a projection; the [projections](projections.md) page covers that.

## Filter, deduplicate and order

`where` takes a callable that receives a shape instance and returns a Boolean
expression. A field declared nullable, or a nullable expression, must be narrowed
or defaulted before comparison; a `Field[str]` is already present:

```python
active_units = UnitTable.row_source().where(
    lambda unit: unit.status.alter_rows().drop_null().expression.equals("active")
)
```

`distinct()` removes duplicate rows without changing the shape. `order_by(*keys)` orders rows by column names, selections, expressions or callables. One `ascending` value applies to every key, and row order is only observable through a later ordering or a materialised relation.

A one-off filter belongs in the binding's row source. When several bindings need the same filtered grain, name it with a projection instead.

## Combine rows with union

`union(other, all=True)` stacks two row sources. `all=False` removes duplicates from the result.

Both sides must have the same shape: the same members, external names and full logical types, including nullability. A union never renames, casts or reorders columns. If the shapes differ, the build refuses the union rather than guessing which column you meant.

```python
active = UnitTable.row_source().where(
    lambda unit: unit.status.alter_rows().drop_null().expression.equals("active")
)
retired = UnitTable.row_source().where(
    lambda unit: unit.status.alter_rows().drop_null().expression.equals("retired")
)

all_units = active.union(retired)
```

## Join two grains

`join` combines two row sources on one equality. The callable receives one shape instance per side and returns a pair of keys:

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

The records are generated structs. Read their members with `extract`, just as you would for a declared struct:

```python
defect_title = unit_defects.shape.right.extract(lambda defect: defect.title)
```

A join key must be a scalar expression, and both sides must resolve to the same base logical type. Their nullability may differ. Arrays and structs are not join keys.

A null key never matches, in any join mode, because the join uses plain equality. A left row with a null key and a right row with a null key stay unmatched, even in a full join.

`how` selects which unmatched rows survive:

| Value | Rows kept |
| --- | --- |
| `inner` | Only matched pairs |
| `left` | Every left row, matched or not |
| `right` | Every right row, matched or not |
| `full` | Every row from both sides |

The generated records follow the join mode. `right` is nullable for a left join, `left` is nullable for a right join, and both are nullable for a full join. `on` is non-null for an inner join; for an outer join it is nullable when the key on a side that `how` can leave unmatched is nullable.

### The text equality form

Instead of a key pair, `on` may return one `equals` expression. `equals` exists only on `StrExpression`, so it is text-only and needs present text on both sides:

```python
matched = UnitTable.row_source().join(
    DefectTable.row_source(),
    on=lambda unit, defect: (
        unit.unit_ref.default_to("").expression.equals(
            defect.unit_ref.default_to("").expression
        )
    ),
)
```

Narrowing each side with `default_to` makes two null keys compare equal. That differs from the key-pair form, where null keys never match. Use the pair form for non-text keys and when null keys must stay distinct.

A join may consume another join or group. In a second join, the first generated record becomes one side, so `row.left` can itself be a `{on, left, right}` record.

## Group rows

`group_by(by=...)` produces one row per distinct key. The result has the generated shape `{by, members}`:

```python
by_severity = DefectTable.row_source().group_by(
    by=lambda defect: {"severity": defect.severity},
)
```

`by` returns one key input, a mapping of names to inputs, or a sequence of `(name, input)` pairs. A single input is named `key`. Key names must be public Python identifiers and unique within the group, and each key must be scalar.

Rows whose key tuple contains a null are dropped before grouping. Every generated key member is therefore non-null, and `row.by.extract(...)` needs no `alter_rows().drop_null()`.

`members` is an array of generated records that mirror the input row. Member order is unspecified. Grouping only collects rows; the algebra has no `count`, `sum` or `having`.

A binding over a grouped source emits one record per group, not one per input row, because the group has already collapsed the rows.

## Generated shapes and static typing

`join` and `group_by` build a shape while your module is imported. At edit time the result is a `DerivedRowSource[Any]`, so pyright does not list `on`, `left`, `right`, `by` or `members` as static members of the generated shape. The fields and their logical types exist at runtime, and your callables and computed fields are checked against them there. Input table and projection shapes stay statically typed.

## Name a derived grain

Pass a derived source directly to a binding for one-off use. When more than one consumer needs it, pin it to a projection:

```python
class UnitDefectProjection(unit_defects.projection_base()):
    """One row per defect, with the unit it belongs to."""
```

`projection_base()` inherits the generated shape's fields as outputs. A projection pinned with `Projection(unit_defects)` starts without inherited outputs, so declare them with `computed_field`. Both pin the same plan; the [projections](projections.md) page explains the choice.

## Limits

- `join` keys must be scalar and share a base logical type. Null keys never match.
- `equals` is text-only. Use the key-pair form for other types.
- `group_by` has no aggregates and no guaranteed member order. Its keys are non-null and uniquely named, and null-key rows are dropped before grouping.
- `union` requires the same shape, member by member, including external names and nullability.
- `order_by` applies one direction to every key.
- A generated join or group shape is open to static tools even though its fields are typed at runtime.

## What to remember

- A row source is a value; a declaration class is not one.
- The grain is the answer to "what is one row?", and the row source records it.
- `where`, `union`, `distinct` and `order_by` preserve the shape; `join` and `group_by` generate one.
- A null join key never matches; `equals` is text-only and needs present text.
- Group keys are non-null, and grouping does not aggregate.

## Next steps

- [Projections](projections.md) give a reusable grain a name and typed outputs.
- [Bindings](bindings.md) consume a row source and produce graph records.

## Reference

[Row sources reference](../reference/row-sources.md) lists every operation, its arguments, the generated shapes and the errors.
