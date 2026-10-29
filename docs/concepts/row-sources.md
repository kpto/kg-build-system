# Row sources

A **row source** is the value that says which rows a projection or binding reads.
`Table.row_source()` and `Projection.row_source()` start it; `where`, `union`,
`join`, `group_by`, `distinct` and `order_by` derive from it. A binding consumes
the result directly with `rows=...`; a projection is only needed when the grain
needs a name.

```python
from kg_build_system import Node, NodeValues, node_binding

active = EmployeeTable.row_source().where(
    lambda row: row.status.alter_rows().drop_null().expression.equals("active")
)

node_binding(
    target=EmployeeNode,
    rows=active,
    bind=lambda row: NodeValues(
        build_key=row.id.alter_rows().drop_null(),
        properties=EmployeeNode(name=row.name.default_to("unknown")),
    ),
)
```

`rows=` takes a row-source **value**. `rows=EmployeeTable` is rejected; write
`EmployeeTable.row_source()`. A `Struct` is a shape, not a row source.

## Filters and row order

`where(predicate)` keeps rows whose predicate is true. The predicate receives a
symbolic shape instance and returns a `BoolExpression`; it cannot be a bare
expression. Source fields read as nullable, so narrow or default before
comparing.

`distinct()` removes duplicate rows. `order_by(*keys, ascending=True)` orders the
result; a key may be a column name, a selection, an expression, or a callable
receiving the shape. One direction applies to every key, and row order is only
observable through later ordering or a materialised relation.

```python
recent = (
    EmployeeTable.row_source()
    .where(lambda row: row.active.alter_rows().drop_null().expression)
    .distinct()
    .order_by("team", ascending=True)
)
```

## Union

`union(other, all=True)` concatenates two row sources with the **same shape**.
`all=False` deduplicates the result. Shapes are compared structurally; a
different shape is refused.

```python
everyone = EmployeeTable.row_source().union(FormerEmployeeTable.row_source())
```

## Join

`join(other, on=..., how="inner")` combines two row sources on one equality.
`on` receives the two shape instances and returns either `(left_key, right_key)`
or one `equals` expression. Keys must be scalar and have the same logical type.

```python
joined = EmployeeTable.row_source().join(
    DepartmentTable.row_source(),
    on=lambda employee, department: (employee.team, department.code),
    how="left",
)
```

The generated shape is `{on, left, right}`:

- `on` is the join key. It is non-null for an inner join; for an outer join it is
  nullable when the surviving side can have a null key.
- `left` and `right` mirror the input rows. The side that `how` can leave
  unmatched is nullable: `right` for `left`, `left` for `right`, both for `full`.
- Null keys never match; the lowerer emits plain SQL equality.

```python
node_binding(
    target=EmployeeDepartmentNode,
    rows=joined,
    bind=lambda row: NodeValues(
        build_key=row.on.default_to("unmatched"),
        properties=EmployeeDepartmentNode(
            employee=row.left.extract(lambda left: left.id),
            department=row.right.extract(lambda right: right.label),
        ),
    ),
)
```

`row.left` and `row.right` are generated records; use `extract` for their
members, exactly as for a declared struct.

## Group

`group_by(by=...)` produces `{by, members}`. `by` receives the shape instance and
returns one key input, a mapping of names to inputs, or `(name, input)` pairs:

```python
by_team = EmployeeTable.row_source().group_by(
    by=lambda row: {"team": row.team},
)
```

`by` is a generated record of the named keys; key names must be identifiers.
`members` is an array of generated record mirrors of the input row. Rows whose
key tuple contains a null are dropped before grouping. Member order is
unspecified, and grouping only collects members; count/sum/having aggregates do
not exist.

```python
node_binding(
    target=TeamNode,
    rows=by_team,
    bind=lambda row: NodeValues(
        build_key=row.by.extract(lambda key: key.team).alter_rows().drop_null(),
        properties=TeamNode(
            members=row.members
            .transform_items(lambda member: member.extract(lambda item: item.id))
            .drop_null_items()
            .concat("|"),
        ),
    ),
)
```

## Projections over derived sources

`derived.projection_base()` gives the derived grain a name and inherits its
fields. Declare outputs with `computed_field`; the source expressions are the
generated shape's members:

```python
class TeamPairsProjection(joined.projection_base()):
    key = computed_field(joined.shape.on)
    employee = computed_field(
        joined.shape.left.extract(lambda left: left.id).alter_rows().drop_null()
    )
```

Compilation materialises every non-scan plan as a named relation in dependency
order. A projection or binding then reads the derived relation like any other
row source; the algebra is not inlined into each consumer.

## Limits

- Generated `join` and `group_by` shapes are `DerivedRowSource[Any]` at edit
  time. Their fields are correct and typed at runtime, but pyright does not
  expose `on`/`left`/`right`/`by`/`members` as static members of the generated
  shape. Input shapes remain statically typed.
- `join` keys must have the same scalar logical type; null keys never match.
- `group_by` has no aggregates and no guaranteed member order.
- `order_by` applies one direction to all keys.
