# Row sources

A row source names the rows a binding or projection reads and the typed shape of
one row.

`row_source()`, `where`, `unnest`, `union`, `join`, `group_by`, `distinct` and
`order_by` are the authoring algebra. The model is explained on
[Row sources and grain](../concepts/row-sources.md); the values that read a row
are on [Expressions and selections](expressions.md); naming a plan is on
[Projections](projections.md).

## `row_source()`

```text
Table.row_source() -> RelationRowSource[Self]
Projection.row_source() -> RelationRowSource[Any]
```

Returns the relation row source for a table or projection. The relation's
`.shape` is the shape class of one row.

```python
from kg_build_system import Field, Table, TableOptions, field


from estate.assets import Estate

class SiteTable(Table[Estate]):
    options = TableOptions(name="sites")
    site_id: Field[str] = field()
    name: Field[str] = field()
    region: Field[str] = field()


class ReadingTable(Table[Estate]):
    options = TableOptions(name="readings")
    reading_id: Field[str] = field()
    site_id: Field[str] = field()
    region: Field[str] = field()
    value: Field[float] = field()


sites = SiteTable.row_source()       # RelationRowSource[SiteTable]
```

A binding takes a row-source **value**. It does not accept a declaration class
such as `Table` or `Projection`. A `Struct` or `ComputedStruct` is not a row
source.

| Error | Trigger |
| --- | --- |
| `rows must be a row source value; use Table.row_source() or Projection.row_source()` | A row-source operation receives a declaration class or other non-value |
| `rows must be a row source value; use Table.row_source()` | A binding factory receives a non-row-source value |

## The algebra

Every derived operation returns another row source, so calls compose.

| Operation | Signature | Returns | Shape |
| --- | --- | --- | --- |
| `where` | `where(predicate: Callable[[S], Selection[bool]])` | `DerivedRowSource[S]` | Unchanged |
| `unnest` | `unnest(selector: Callable[[S], Selection[Array[I]]])` | `DerivedRowSource[S]` with the selected member narrowed to `I` | Narrowed |
| `union` | `union(other, *, all: bool = True)` | `DerivedRowSource[S]` | Unchanged |
| `join` | `join(other, *, on, how="inner")` | `DerivedRowSource[Any]` | `{on, left, right}` |
| `group_by` | `group_by(*, by)` | `DerivedRowSource[Any]` | `{by, members}` |
| `distinct` | `distinct()` | `DerivedRowSource[S]` | Unchanged |
| `order_by` | `order_by(*keys, ascending: bool = True)` | `DerivedRowSource[S]` | Unchanged |

## `where()`

```text
RowSource.where(
    predicate: Callable[[S], Selection[bool]],
) -> DerivedRowSource[S]
```

Keeps rows whose predicate is true. The predicate receives a typed row proxy, not
the declaration class, and must return a `Selection[bool]`.

| Parameter | Type | Meaning |
| --- | --- | --- |
| `predicate` | `Callable[[S], Selection[bool]]` | Receives the row proxy and returns a row predicate |

```python
depots = SiteTable.row_source().where(
    lambda site: site.name.alter_rows().drop_null().equals("Depot")
)
```

A source field reads as nullable, so narrow or default it before comparing. A
null predicate is not true, so its row is dropped.

| Error | Trigger |
| --- | --- |
| `where requires a callable predicate` | A bare selection is passed |
| `where predicates must return a Selection[bool]` | The callable returns another type |

## `unnest()`

```text
RowSource.unnest(
    selector: Callable[[S], Selection[Array[I]] | Selection[Nullable[Array[I]]]],
) -> DerivedRowSource[S]
```

Expands one direct array member into rows, one row per item. The result keeps every
other field and narrows the selected field to its item shape. A null or empty
array produces no rows.

```python
one_tag_per_row = SiteTable.row_source().unnest(lambda site: site.tags)
```

The selected member is read through `.shape`:

```python
class TagProjection(Projection(one_tag_per_row)):
    site_id = computed_field(
        one_tag_per_row.shape.site_id.alter_rows().drop_null()
    )
    tag = computed_field(one_tag_per_row.shape.tags)
```

`unnest` is the row-source spelling of expansion. `Selection.expand` remains a
selection row effect for a product that already reads the row.

| Error | Trigger |
| --- | --- |
| `unnest requires a callable selector` | `selector` is not callable |
| `unnest selectors must return an array Selection` | The selector returns a non-array |
| `unnest requires a selector that reads one declared field` | The selector reads a computed expression rather than a direct field |
| `unnest field 'x' is not a member of its input shape` | The selected field is not a member of the source shape |

## `union()`

```text
RowSource.union(
    other: RowSource,
    *,
    all: bool = True,
) -> DerivedRowSource[S]
```

Concatenates two row sources with the same shape. `all=False` removes duplicate
rows.

| Parameter | Type | Meaning | Default |
| --- | --- | --- | --- |
| `other` | row-source value | The right operand | Required |
| `all` | `bool` | Keep duplicates | `True` |

Shapes are compared member by member: external name and full logical type,
including nullability. A union never renames, casts or reorders columns.

```python
# ArchivedSiteTable declares the same fields as SiteTable.
everyone = SiteTable.row_source().union(ArchivedSiteTable.row_source())
```

| Error | Trigger |
| --- | --- |
| `union row sources must have the same shape` | A member name, type or nullability differs |

## `join()`

```text
RowSource.join(
    other: RowSource,
    *,
    on: Callable[[S, R], tuple[Selection[Any], Selection[Any]] | Selection[bool]],
    how: str = "inner",
) -> DerivedRowSource[Any]
```

Combines two row sources on one equality. `on` receives one row proxy per side
and returns either:

- `(left_key, right_key)`, a pair of scalar selections; or
- one `equals` selection, the text-only equality operation.

| Parameter | Type | Meaning | Default |
| --- | --- | --- | --- |
| `other` | row-source value | The right side | Required |
| `on` | callable | Returns a key pair or one `equals` selection | Required |
| `how` | `"inner"`, `"left"`, `"right"` or `"full"` | Which side may be unmatched | `"inner"` |

The key pair is the general form. Keys must resolve to the same base logical
type; their nullability may differ. Arrays and structs are refused. Null keys
never match in any join mode.

```python
site_readings = SiteTable.row_source().join(
    ReadingTable.row_source(),
    on=lambda site, reading: (site.site_id, reading.site_id),
    how="left",
)
```

The `equals` form needs present text on both sides. Defaulting makes null keys
compare equal, unlike the pair form:

```python
matched = SiteTable.row_source().join(
    ReadingTable.row_source(),
    on=lambda site, reading: (
        site.region.default_to("").equals(reading.region.default_to(""))
    ),
)
```

| Error | Trigger |
| --- | --- |
| `join on must be a callable returning a key pair` | `on` is not callable |
| `join on must return a (left key, right key) pair` | The callable returns a non-pair, non-`equals` value |
| `join on must return a (left key, right key) pair or one equals expression` | A Boolean selection is not a single equality |
| `join key expressions must have the same logical type` | The pair resolves to different base types |
| `join keys must be scalar expressions` | A key is an array or struct |
| `join how must be 'inner', 'left', 'right', or 'full'` | `how` is another value |

## `group_by()`

```text
RowSource.group_by(
    *,
    by: Callable[[S], Selection[Any] | Mapping[str, Selection[Any]] | Sequence[tuple[str, Selection[Any]]]],
) -> DerivedRowSource[Any]
```

Groups rows by one or more scalar selections. `by` returns one key selection
(named `key`), a mapping of names to selections, or `(name, selection)` pairs.

```python
by_region = SiteTable.row_source().group_by(
    by=lambda site: {"region": site.region},
)

region = by_region.shape.by.extract(lambda key: key.region)
members = by_region.shape.members
```

Rows whose key tuple contains a null are dropped before grouping, so every
generated `by` member is present. Key names must be public Python identifiers and
unique within the group; keys must be scalar selections.

`members` is an array of generated record mirrors of the input row. Member order
is unspecified, and grouping only collects members: count, sum and having
aggregates do not exist. A binding over a grouped source emits one record per
group, not one per input row.

| Error | Trigger |
| --- | --- |
| `group_by by must be a callable` | `by` is not callable |
| `group_by requires at least one key` | The callable returns no key |
| `group_by key names must be Python identifiers` | A key name is not an identifier |
| `group_by key names must be unique` | Two keys share a name |
| `group_by keys must be scalar expressions` | A key is an array or struct |
| `generated shape member '_name' must be a public Python identifier` | A key name starts with `_` |

## `distinct()` and `order_by()`

```text
RowSource.distinct() -> DerivedRowSource[S]

RowSource.order_by(
    *keys: str | Selection[Any] | Callable[[S], Selection[Any]],
    ascending: bool = True,
) -> DerivedRowSource[S]
```

`distinct()` removes duplicate rows without changing the shape.

`order_by()` orders rows by one or more keys. A key may be a column name, a
selection, or a callable receiving the row proxy. One direction applies to every
key. Row order is observable only through later ordering or a materialised
relation.

```python
recent = (
    SiteTable.row_source()
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

## Generated shapes

`join` produces `{on, left, right}`:

| Member | Type | Nullability |
| --- | --- | --- |
| `on` | The shared key base type | Present for an inner join; nullable for an outer join when the surviving side's key can be null |
| `left` | A record mirror of the left row | Nullable for `right` and `full`; present for `inner` and `left` |
| `right` | A record mirror of the right row | Nullable for `left` and `full`; present for `inner` and `right` |

`left` and `right` are generated records; read their members with `extract`.
A join may consume another join or group and nest its generated records.

```python
key = site_readings.shape.on
site_name = site_readings.shape.left.extract(lambda left: left.name)
reading_value = site_readings.shape.right.extract(lambda right: right.value)
```

`group_by` produces `{by, members}`:

| Member | Type | Nullability |
| --- | --- | --- |
| `by` | A record of the named keys | Every key member is present |
| `members` | An array of record mirrors of the input row | Present array; item order unspecified |

`row.by.extract(...)` needs no `drop_null()`. The `members` array is read like
any other array:

```python
site_ids = by_region.shape.members.transform_items(
    lambda member: member.extract(lambda item: item.site_id)
).drop_null_items()
```

`unnest` keeps the input shape and narrows the selected member to the array item.
Read the narrowed member through `.shape`.

## Types and limits

`Table.row_source()` and `Projection.row_source()` return a
`RelationRowSource[Self]` or `RelationRowSource[Any]`. Every derived operation
returns a `DerivedRowSource`; both are frozen row-source values with a `.shape`.

| Operation | Static result |
| --- | --- |
| `where`, `union`, `distinct`, `order_by` | `DerivedRowSource[S]` with the input shape |
| `unnest` | `DerivedRowSource[S]` with a generated narrowed shape |
| `join`, `group_by` | `DerivedRowSource[Any]` with a generated shape |

A generated `join`, `group_by` or `unnest` shape is correct at runtime, but a
static type checker sees its members through `.shape` as `Any`. Input shapes
remain statically typed. Use `.shape.on`, `.shape.left`, `.shape.right`,
`.shape.by`, `.shape.members` and the narrowed `.shape` member explicitly.

## What to remember

- `row_source()` starts the algebra; the algebra requires a value. A binding does
  not accept a declaration class.
- `where`, `union`, `distinct` and `order_by` preserve shape; `unnest` narrows
  one member; `join` and `group_by` generate a shape.
- Join keys are scalar and share a base type. Null keys never match.
- Group keys are scalar and present; null-key rows are dropped.
- `join`, `group_by` and `unnest` return generated shapes; read them through
  `.shape`.
- A row source is a value, not a schema or a class.

Next: [Projections](projections.md) give a row plan a name and typed outputs.
