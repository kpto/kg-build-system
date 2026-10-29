# Row sources

A **row source** is the value that says which rows a binding or projection
reads. It exists so that row grain is an explicit, typed value: the author can
see every filter, join, grouping and expansion that produces a record, and the
same plan can be reused or named instead of copied into each consumer.

`Table.row_source()` and `Projection.row_source()` start it; `where`, `union`,
`join`, `group_by`, `distinct` and `order_by` derive from it. Every derived
operation returns another row source, so the algebra composes. A projection
relation is a row source too: it supports the same operations as a table
relation. A binding consumes the result directly with `rows=...`; a projection
is only needed when the grain needs a name.

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
`all=False` deduplicates the result. Shapes are compared structurally, member by
member, including each member's external name and full logical type. A different
name, type or nullability is refused with
`union row sources must have the same shape`; a union never renames, casts or
reorders columns.

```python
everyone = EmployeeTable.row_source().union(FormerEmployeeTable.row_source())
```

## Join

`join(other, on=..., how="inner")` combines two row sources on one equality.
`on` receives one shape instance per side and returns either:

- `(left_key, right_key)`, a pair of scalar inputs; or
- one `equals` expression, which is the text-only equality operation.

The pair form is the general one. Keys must resolve to the same **base** logical
type; their nullability may differ. Arrays and structs are refused with
`join keys must be scalar expressions`, and differing base types with
`join key expressions must have the same logical type`. Null keys never match:
the lowerer emits plain SQL equality, whose three-valued result leaves a null
key unmatched in every join mode.

```python
joined = EmployeeTable.row_source().join(
    DepartmentTable.row_source(),
    on=lambda employee, department: (employee.team, department.code),
    how="left",
)
```

The `equals` form needs present text on both sides. `equals` exists only on
`StrExpression`, so narrow or default each side first. Defaulting makes null
keys compare equal, which is different from the pair form:

```python
matched = EmployeeTable.row_source().join(
    DepartmentTable.row_source(),
    on=lambda employee, department: (
        employee.team.default_to("").expression.equals(
            department.code.default_to("").expression
        )
    ),
)
```

The generated shape is `{on, left, right}`:

- `on` is the join key. It is non-null for an inner join; for an outer join it is
  nullable when the surviving side's key can be null.
- `left` and `right` mirror the input rows. The side that `how` can leave
  unmatched is nullable: `right` for `left`, `left` for `right`, both for `full`.
  A join may consume another join or group and nest its generated records.

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
members, exactly as for a declared struct. A second join sees the first join as
one side:

```python
nested = joined.join(
    OfficeTable.row_source(),
    on=lambda pair, office: (pair.on, office.region),
)
# nested.shape.left is the `{on, left, right}` record from `joined`.
```

## Group

`group_by(by=...)` produces `{by, members}`. `by` receives the shape instance and
returns one key input (named `key`), a mapping of names to inputs, or
`(name, input)` pairs:

```python
by_team = EmployeeTable.row_source().group_by(
    by=lambda row: {"team": row.team},
)
```

`by` is a generated record of the named keys. Key names must be public Python
identifiers and unique within the group; keys must be scalar inputs. Rows whose
key tuple contains a null are dropped before grouping, so **every generated key
member is non-null**. `row.by.extract(...)` therefore needs no
`alter_rows().drop_null()`.

`members` is an array of generated record mirrors of the input row. Member order
is unspecified, and grouping only collects members; count/sum/having aggregates
do not exist. A binding over `by_team` emits one record per group, not one per
input row, because `group_by` has already collapsed the rows.

```python
node_binding(
    target=TeamNode,
    rows=by_team,
    bind=lambda row: NodeValues(
        build_key=row.by.extract(lambda key: key.team),
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

A projection can pin a derived plan directly. Pass the source itself to
`Projection(...)`; a `Table` or `Projection` relation has `.row_source()`, while
a derived source is already one:

```python
class TeamPairsProjection(Projection(joined)):
    key = computed_field(joined.shape.on)
    employee = computed_field(
        joined.shape.left.extract(lambda left: left.id).alter_rows().drop_null()
    )
```

`derived.projection_base()` gives the same grain a name and inherits its fields.
Declare outputs with `computed_field`; the source expressions are the generated
shape's members:

```python
class TeamPairsProjection(joined.projection_base()):
    key = computed_field(joined.shape.on)
    employee = computed_field(
        joined.shape.left.extract(lambda left: left.id).alter_rows().drop_null()
    )
```

Compilation materialises every non-scan plan as a named relation in dependency
order. A projection or binding then reads the derived relation like any other
row source; the algebra is not inlined into each consumer. That is why a join
or group is computed once even when several bindings read it.

## Limits

- Generated `join` and `group_by` shapes are `DerivedRowSource[Any]` at edit
  time. Their fields are correct and typed at runtime, but pyright does not
  expose `on`/`left`/`right`/`by`/`members` as static members of the generated
  shape. Input shapes remain statically typed.
- `join` keys must be scalar and share a base type; nullability may differ, and
  null keys never match.
- `equals` is text-only. Use the key-pair form for non-text keys.
- `group_by` has no aggregates and no guaranteed member order. Its keys are
  non-null, unique names; null-key rows are dropped before grouping.
- `order_by` applies one direction to all keys.
