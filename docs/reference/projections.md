# Projections

A projection names one row plan and publishes typed outputs computed from that
row.

`Projection` is both a shape and a row source. The model and the choice of
grain are on [Projections](../concepts/projections.md); the source algebra is
on [Row sources](row-sources.md); expression typing is on
[Expressions and selections](expressions.md).

The examples use these declarations:

```python
from kg_build_system import Field, Struct, Table, TableOptions, field
from kg_build_system import Array


class ContactStruct(Struct):
    email: Field[str] = field()


class SiteTable(Table):
    options = TableOptions(name="sites")
    site_id: Field[str] = field()
    name: Field[str] = field()
    region: Field[str] = field()
    parent_site: Field[str] = field()
    tags: Field[Array[str]] = field()
    contacts: Field[Array[ContactStruct]] = field()


class ReadingTable(Table):
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
        SiteTable.name.alter_rows().drop_null().expression.prepend("site::")
    )
```

`Projection(SiteTable.row_source())` pins the relation and records its filters in
the compiled definition. A filtered, joined, grouped or unioned source is passed
directly: `Projection(joined)`. The pin does not copy fields; declare the outputs
explicitly.

The compatibility form declares the class without a pin and marks outputs with
`projection_field(...)`. Its plan is derived from the one source its outputs
read; prefer the pinned form because it states the grain directly. The
constructor is documented once on
[Declarations](declarations.md#projection_field).

A projection is final and terminal. It may not inherit from another final
`Projection`; reuse a shape with `projection_base()` or pin a new source.

| Member | Returns | Use |
| --- | --- | --- |
| `row_source()` | `RelationRowSource[Any]` | Read the projection as a relation |
| `where(predicate)` | `DerivedRowSource[Self]` | Shorthand for `row_source().where(...)` |
| `projection_base()` | A dynamic projection base | Inherit the output fields under a new base |

| Error | Trigger |
| --- | --- |
| `projections require a row source` | An unpinned projection's outputs do not resolve to one driving source, at compile |
| `projections must declare at least one computed_field` | The projection has no effective output |
| `a final Projection may not inherit from another final Projection` | A final projection inherits another final projection |

## `computed_field()` in a projection

```python
def computed_field(
    value: ValueInput[T],
    *,
    name: str | None = None,
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> Field[T]: ...
```

Declares one projection output. `value` is a selection or expression; the output
is typed by its logical type and nullability.

| Parameter | Type | Meaning | Default |
| --- | --- | --- | --- |
| `value` | `ValueInput[T]` | The output expression | Required |
| `name` | `str or None` | External output name | Snake case of the attribute; one trailing `_` is removed |
| `description` | `str or None` | Output description | The string below the assignment |
| `annotations` | `Sequence[Annotation]` | Portable output metadata | `()` |

```python
class SiteOutputProjection(Projection(SiteTable.row_source())):
    site_id = computed_field(
        SiteTable.site_id.alter_rows().drop_null(),
        name="site_id",
    )
    parent = computed_field(SiteTable.parent_site)
```

| Output expression | Read result |
| --- | --- |
| Non-null scalar | `ValueSelection[T]` |
| Nullable scalar | `NullableSelection[T]` |
| Present array | `ArraySelection[T]` |
| Nullable array | `NullableSelection[Array[T]]` |
| Present struct | `StructSelection[S]` |
| Nullable struct | `NullableSelection[S]` |

`field()` is not legal for a projection output; a projection has no source
columns of its own. Reading `SiteProjection.site_id` anywhere returns the
projection's materialised output, not the expression that produced it.

| Error | Trigger |
| --- | --- |
| `<Class>.<attribute> must be declared with computed_field()` | `field()` is used for an output |
| `expected a value selection or value expression` | `value` is neither |
| `<Class> fields 'x' and 'y' share external name 'name'` | Two outputs resolve to the same external name |

## `projection_base()`

```text
Table.projection_base() -> type
Projection.projection_base() -> type
RelationRowSource.projection_base() -> type
DerivedRowSource.projection_base() -> type
```

Returns a dynamic projection base that carries the source's plan and inherits its
fields as computed outputs. It is available on a table, a projection, a relation
row source and a derived row source.

```python
north = SiteTable.row_source().where(
    lambda site: site.region.alter_rows().drop_null().expression.equals("north")
)


class NorthernSitesProjection(north.projection_base()):
    """The northern sites under a name bindings can share."""


class NorthernLabelsProjection(NorthernSitesProjection.projection_base()):
    label = computed_field(
        NorthernSitesProjection.site_id.alter_rows().drop_null()
        .expression.prepend("site::")
    )
```

Inherited fields are typed from the fields' declared access, so a `Field[str]`
arrives present and a `Field[str | None]` arrives nullable. Declare additional
outputs with `computed_field` as usual.
A declared field with the same Python attribute shadows the inherited one, as
normal Python attribute shadowing works; two fields with the same external name
but different attributes are rejected at class creation.

The base returned by `projection_base()` is not a final projection and does not
enter the build by itself. Only the named class you finish enters.

| Error | Trigger |
| --- | --- |
| `<Class> fields 'x' and 'y' share external name 'name'` | An inherited and a declared field have the same external name |

## Outputs and dependencies

- A projection has one driving source. All output expressions must read that
  source, possibly through chained expansions and struct navigation.
- A reference to another projection's output is a dependency, not an embedded
  row plan. Reading that field reuses the named relation.
- Projection dependencies must be acyclic. A cycle fails compilation with
  `projection dependency cycle includes 'name'`.
- A projection that references two unrelated relations fails compilation with
  `a relational product requires one driving source; additional sources must be
  introduced by an explicit lookup`. Build the relation first and pin it, or use
  `projection_base()` on the derived source.
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

A grouped source is pinned the same way. `joined.projection_base()` is the
variant that inherits the generated shape's fields.

| Compile error | Trigger |
| --- | --- |
| `a relational product requires one driving source; additional sources must be introduced by an explicit lookup` | Outputs read unrelated relations |
| `projection dependency cycle includes 'name'` | Projections depend on each other in a cycle |
| `rows must be a row source value; use Table.row_source() or Projection.row_source()` | `Projection` is pinned to a declaration class rather than a row-source value |
| `projection names must be unique` | Two projections share a logical name |
| `logical source names must be unique` | A projection and a table share a logical name |
| `sources require a final Table or TableGroup` | `bind_source` targets a projection |

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
    )
```

`SiteTable.contacts` is expanded once, so every output sees one row per contact.
Expanding two unrelated arrays multiplies the two fan-outs. A further new grain
needs its own projection, not a second expansion in the same class.

## Naming and options

```python
from kg_build_system import ProjectionOptions


class SiteLabelProjection(SiteProjection.projection_base()):
    options = ProjectionOptions(
        name="site_label",
        description="One row per site, with the shared display label.",
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

## What to remember

- Prefer pinning a projection at class creation with `Projection(source)`; the
  unpinned `projection_field` form is a compatibility spelling.
- Outputs use `computed_field`; they carry the expression's type and
  nullability.
- Reading a projection field returns its materialised output, not the
  calculation behind it.
- One projection has one driving source. Join, group or union in the row source
  you pin.
- All outputs share one row plan, so an expansion or drop affects the whole
  projection.
- `projection_base()` names a source and inherits its fields; only the finished
  named class enters the build.

Next: [Reference index](index.md) collects every authoring name by task.
