# Projections

A projection names one row plan and publishes typed outputs computed from that
row.

`Projection` is both a shape and a row source. The model and the choice of
grain are on [Projections](../concepts/projections.md); the source algebra is
on [Row sources](row-sources.md); selection typing is on
[Expressions and selections](expressions.md).

The examples use these declarations:

```python
from kg_build_system import Field, Struct, Table, TableOptions, field
from kg_build_system import Array


class ContactStruct(Struct):
    email: Field[str] = field()


from estate.assets import Estate

class SiteTable(Table[Estate]):
    options = TableOptions(name="sites")
    site_id: Field[str] = field()
    name: Field[str] = field()
    region: Field[str] = field()
    tags: Field[Array[str]] = field()
    contacts: Field[Array[ContactStruct]] = field()


class ReadingTable(Table[Estate]):
    options = TableOptions(name="readings")
    reading_id: Field[str] = field()
    site_id: Field[str] = field()
```

## `Projection(source)`

```text
Projection(source: RowSource[S]) -> type[Projection]
```

`Projection(source)` returns a base pinned to one row source. Subclass it,
declare at least one output with `computed_field`, and name the class.

| Parameter | Type | Meaning |
| --- | --- | --- |
| `source` | row-source value | The relation or derived plan the projection reads |

```python
from kg_build_system import Projection, computed_field


class SiteProjection(Projection(SiteTable.row_source())):
    """One row per site, with a display label."""

    site_id = computed_field(SiteTable.site_id.alter_rows().drop_null())
    label = computed_field(
        SiteTable.name.alter_rows().drop_null().prepend("site::")
    )
```

`Projection(SiteTable.row_source())` pins the relation and records its filters in
the compiled declaration. A filtered, joined, grouped or unioned source is passed
directly: `Projection(joined)`. The pin does not copy fields; declare the outputs
explicitly.

A projection is final and terminal. It may not inherit from another final
`Projection`; pin a new source instead.

| Member | Returns | Use |
| --- | --- | --- |
| `row_source()` | `RelationRowSource[Any]` | Read the projection as a relation |

| Error | Trigger |
| --- | --- |
| `requires a row source` | `Projection()` is called without a source, or a class is declared as `class P(Projection)` |
| `projections must declare at least one computed_field` | The projection has no output |
| `a final Projection may not inherit from another final Projection` | A final projection inherits another final projection |
| `rows must be a row source value; use Table.row_source() or Projection.row_source()` | `Projection` is pinned to a declaration class rather than a row-source value |

## `computed_field()`

```python
def computed_field[T: DeclaredValue](
    value: Selection[T],
    *,
    name: str | None = None,
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> Field[T]: ...
```

Declares one projection output. `value` is a selection; the output is typed by
its logical type.

| Parameter | Type | Meaning | Default |
| --- | --- | --- | --- |
| `value` | `Selection[T]` | The output selection | Required |
| `name` | `str or None` | External output name | Snake case of the attribute; one trailing `_` is removed |
| `description` | `str or None` | Output description | The string below the assignment |
| `annotations` | `Sequence[Annotation]` | Portable output metadata | `()` |

```python
class SiteOutputProjection(Projection(SiteTable.row_source())):
    site_id = computed_field(
        SiteTable.site_id.alter_rows().drop_null(),
        name="site_id",
    )
    region = computed_field(SiteTable.region)
```

| Output selection | Read result |
| --- | --- |
| Present scalar | `Selection[T]` |
| Nullable scalar | `Selection[Nullable[T]]` |
| Present array | `Selection[Array[T]]` |
| Nullable array | `Selection[Nullable[Array[T]]]` |
| Present struct | `Selection[S]` |
| Nullable struct | `Selection[Nullable[S]]` |

`field()` is not legal for a projection output; a projection has no source
columns of its own. Reading `SiteProjection.site_id` anywhere returns the
projection's materialised output, not the selection that produced it.

| Error | Trigger |
| --- | --- |
| `<Class>.<attribute> must be declared with computed_field()` | `field()` is used for an output |
| `<Class> fields 'x' and 'y' share external name 'name'` | Two outputs resolve to the same external name |
| `<Class>.<attribute> must have a Field[T] annotation` | The output has no `Field[T]` annotation |
| `computed field names must be non-empty` | `computed_field(..., name="")` |

## Outputs and dependencies

- A projection has one driving source. All output selections must read that
  source, possibly through chained expansions and struct navigation.
- A reference to another projection's output is a dependency, not an embedded
  row plan. Reading that field reuses the named relation.
- Projection dependencies must be acyclic. A cycle fails compilation with
  `projection dependency cycle includes 'name'`.
- A projection that references two unrelated relations fails compilation with
  `a relational product requires one driving source; additional sources must be
  introduced by an explicit lookup`. Build the relation first and pin it, or use
  `lookup` to read the second relation by key.
- A projection name must be unique among projections and among logical source
  names; tables and projections share the relation namespace.

```python
joined = SiteTable.row_source().join(
    ReadingTable.row_source(),
    on=lambda site, reading: (site.site_id, reading.site_id),
    how="left",
)


class SiteReadingProjection(Projection(joined)):
    """One row per site-reading pair."""

    site_id = computed_field(
        joined.shape.left.extract(lambda left: left.site_id)
        .alter_rows().drop_null()
    )
    reading_id = computed_field(
        joined.shape.right.extract(lambda right: right.reading_id)
    )
```

A grouped source is pinned the same way.

| Compile error | Trigger |
| --- | --- |
| `a relational product requires one driving source; additional sources must be introduced by an explicit lookup` | Outputs read unrelated relations |
| `projection dependency cycle includes 'name'` | Projections depend on each other in a cycle |
| `projection names must be unique` | Two projections share a logical name |
| `logical source names must be unique` | A projection and a table share a logical name |

A second relation can be read inline with `lookup`, without making it a scan of
the projection:

```python
class SiteWithRegionProjection(Projection(SiteTable.row_source())):
    site_id = computed_field(SiteTable.site_id.alter_rows().drop_null())

    region_name = computed_field(
        SiteTable.region_id.lookup(RegionTable, SiteTable.region_id)
        .alter_rows().drop_null()
        .alter_rows().expand()
        .extract(lambda region: region.name)
    )
```

## Row behaviour

Every field in one projection shares a single row plan. An expansion or a drop
written for one output applies to the whole projection:

```python
class ContactProjection(Projection(SiteTable.row_source())):
    """One row per contact."""

    site_id = computed_field(SiteTable.site_id.alter_rows().drop_null())
    email = computed_field(
        SiteTable.contacts.alter_rows().drop_null()
        .alter_rows().expand()
        .extract(lambda contact: contact.email)
        .alter_rows().drop_null()
    )
```

`SiteTable.contacts` is expanded once, so every output sees one row per contact.
Expanding two unrelated arrays multiplies the two fan-outs. A further new grain
needs its own projection, not a second expansion in the same class.

## Naming and options

```python
from kg_build_system import ProjectionOptions


class SiteLabelProjection(Projection(SiteTable.row_source())):
    options = ProjectionOptions(
        name="site_label",
        description="One row per site, with the shared display label.",
    )

    site_id = computed_field(SiteTable.site_id.alter_rows().drop_null())
    label = computed_field(
        SiteTable.name.alter_rows().drop_null().prepend("site::")
    )
```

The name defaults to the class name with one `Projection` suffix removed and
converted to snake case, so `SiteLabelProjection` becomes `site_label`.
`options.description` wins over the class docstring; description is not
inherited. `options.annotations` attaches portable metadata. An explicit
`computed_field(name=...)` wins over the output's snake-case attribute name.

| Error | Trigger |
| --- | --- |
| `Projection.options must be a ProjectionOptions value` | `options` is not a `ProjectionOptions` |
| `<Class> is a Projection declaration: declare ProjectionOptions, not template options` | `options = StructOptionsTemplate(...)` on a projection |
| `projection names must be non-empty` | `ProjectionOptions(name="")` |

## What to remember

- Pin a projection at class creation with `Projection(source)`; there is no
  unpinned form.
- Outputs use `computed_field`; they carry the selection's type.
- Reading a projection field returns its materialised output, not the
  calculation behind it.
- One projection has one driving source. Join, group or union in the row source
  you pin; read a second relation by key with `lookup`.
- All outputs share one row plan, so an expansion or drop affects the whole
  projection.

Next: [Reference index](index.md) collects every authoring name by task.
