# Declarations

Declarations state the shape of one row, the shape of a nested record, the name
of a relation, a table catalog and the asset those rows come from.

The declaration names come from `kg_build_system`; the representative and
canonical types come from `kg_build_system`. The meaning of each
declaration is on [Data contracts](../concepts/data-contracts.md); the asset
model is on [Assets](../concepts/assets.md) and the
[assets reference](assets.md). Expressions are on
[Expressions and selections](expressions.md), row plans on
[Row sources](row-sources.md), and named relations on
[Projections](projections.md).

## The declaration set

| Declaration | What it declares | Row source | Names an asset |
| --- | --- | --- | --- |
| `Table` | A final row shape read from one asset | Yes, through `row_source()` | Yes, `Table[Asset]` |
| `Struct` | A nested record used as a field type | No | No |
| `ComputedStruct` | A value record whose members are type witnesses | No | No |
| `Projection` | A named relation with computed outputs | Yes, through `row_source()` | No |
| `TableGroup` | A named catalog of final tables and nested groups | No | Through its members |
| `StructTemplate` | A mixin sharing fields and annotations | No | No |

`Table`, `TableGroup` and `Projection` are final: a final declaration may not
inherit from another final declaration of the same kind. `Struct` and
`ComputedStruct` are composable value records and have no finality guard.

## `field()`

```python
def field(
    *,
    name: str | None = None,
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> Field[T]: ...
```

`field()` declares a source-backed member: a table column or a source struct
member. The type argument is written in the annotation, as
`Field[T] = field()`.

| Parameter | Type | Meaning | Default |
| --- | --- | --- | --- |
| `name` | `str or None` | External field name seen by expressions and the source | Snake case of the attribute; one trailing `_` is removed |
| `description` | `str or None` | Member description | The string written directly below the assignment |
| `annotations` | `Sequence[Annotation]` | Portable metadata carried by the field | `()` |

Returns a `Field[T]` descriptor. Do not construct `Field` directly; the two
constructors decide the backing kind.

```python
from kg_build_system import Field, Table, TableOptions, field
from kg_build_system import Timestamp

from estate.assets import Estate


class VisitTable(Table[Estate]):
    """One inspection visit."""

    options = TableOptions(name="visit")
    visit_id: Field[str] = field()
    """Stable visit identifier."""
    inspected_on: Field[Timestamp] = field()
    display_name: Field[str] = field(name="name")
```

`Field[T]` accepts the eight canonical scalar types, `Array[...]` of a supported
type, a declared `Struct` or `ComputedStruct`, and a declared `CustomDataType`.
A field type must be one of those value types; `Field[SomeTable]` and
`Field[SomeProjection]` are not legal. The full type table is on
[Types](types.md).

| Error | Trigger |
| --- | --- |
| `field names must be non-empty` | `field(name="")` |
| `<Class>.<attribute> must have a Field[T] annotation` | The attribute has no `Field[T]` annotation |
| `<Class>.<attribute> is a source field and must be declared with field(), not computed_field()` | `computed_field(...)` used in a `Table` or `Struct` |
| `<Class>.<attribute> must be declared with computed_field()` | `field()` used in a `Projection` or `ComputedStruct` |
| `<Class> fields 'x' and 'y' share external name 'name'` | Two members resolve to the same external name |
| `one Field instance may not be assigned to multiple declarations` | The same `Field` object is assigned twice |
| `<Name> is a row source, not a value record; field types must be Struct or ComputedStruct declarations` | `Field[SomeTable]` or `Field[SomeProjection]` |
| `logical types must be explicit; Any is not supported` | `Field[Any]` |
| <code>logical unions are limited to T &#124; None</code> | A union with two non-null members |
| `unsupported logical type annotation: ...` | `list[T]`, `dict[K, V]` or another unsupported annotation |

## `computed_field()`

```python
def computed_field(
    value: ValueInput[T],
    *,
    name: str | None = None,
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> Field[T]: ...
```

`computed_field()` declares an expression-backed member. It is legal on a
`Projection` output and on a `ComputedStruct` member; the host decides what the
expression means.

| Parameter | Type | Meaning | Default |
| --- | --- | --- | --- |
| `value` | `ValueInput[T]` | A selection or expression that types the output | Required |
| `name` | `str or None` | External output name | Snake case of the attribute; one trailing `_` is removed |
| `description` | `str or None` | Output description | The string written directly below the assignment |
| `annotations` | `Sequence[Annotation]` | Portable metadata carried by the output | `()` |

Returns a `Field[T]` descriptor. On a `Projection`, the field is an output typed
by `value`; on a `ComputedStruct`, the field is a type witness. See
[Projections](projections.md) and [ComputedStruct](#computedstruct). The
examples use the `SiteTable` declared under [Table](#table).

```python
from kg_build_system import ComputedStruct, Projection, computed_field


class SiteProjection(Projection(SiteTable.row_source())):
    site_id = computed_field(SiteTable.site_id.alter_rows().drop_null())
    label = computed_field(
        SiteTable.name.alter_rows().drop_null().expression.prepend("site::")
    )


class SiteSummaryStruct(ComputedStruct):
    """The member types a summary record carries."""

    site_id = computed_field(SiteTable.site_id.alter_rows().drop_null())
    region = computed_field(SiteTable.region)
```

| Error | Trigger |
| --- | --- |
| `computed field names must be non-empty` | `computed_field(..., name="")` |
| `expected a value selection or value expression` | `value` is not a selection or expression |
| `<Class>.<attribute> must be declared with computed_field()` | `field()` used in a `Projection` or `ComputedStruct` |
| `<Class>.<attribute> is a source field and must be declared with field(), not computed_field()` | `computed_field(...)` used in a `Table` or `Struct` |
| `<Class> fields 'x' and 'y' share external name 'name'` | Two outputs or members resolve to the same external name |

## `projection_field()`

```python
def projection_field(
    value: ValueInput[T],
    *,
    name: str | None = None,
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> Field[T]: ...
```

`projection_field()` is the compatibility spelling of `computed_field()` for an
unpinned `Projection`. Its arguments, backing expression and resolved type are
identical; only the constructor name differs. New code should declare outputs
with `computed_field()` on a pinned projection. The older form still derives its
row plan from the output expressions:

```python
from kg_build_system import Projection, projection_field


class OldSiteProjection(Projection):
    site_id = projection_field(SiteTable.site_id)
```

The class is valid only when its outputs resolve to one driving source;
otherwise compilation fails with `projections require a row source`.

## `Field[T]`

`Field[T]` is the member descriptor. The annotation names the value type; the
constructor names the backing.

| Host | Declaration | Read result |
| --- | --- | --- |
| `Table` or source `Struct` | `Field[T]` | The present selection for the value: `ValueSelection[T]` for a scalar, `ArraySelection` for an array, `StructSelection` for a struct |
| `Table` or source `Struct` | `Field[T \| None]` | `NullableSelection[T]` |
| `Projection` | `computed_field(expression)` | Selection typed by the field expression |
| `ComputedStruct` | `computed_field(expression)` | Read only through `extract`; the witness type composed with the carrier's presence |

A source read follows the declaration: `Field[str]` reads non-null and
`Field[str | None]` reads nullable. Array item and nested member nullability stay
in the type, as in `Field[Array[str | None]]`. See [Types](types.md).

## `Table`

```python
class Table[AssetT: Asset]:
    options: TableOptions
    # field members

    @classmethod
    def row_source(cls) -> RelationRowSource[Self]: ...

    @classmethod
    def where(cls, predicate: Callable[[Self], BoolExpression]) -> DerivedRowSource[Self]: ...

    @classmethod
    def projection_base(cls) -> type: ...
```

A `Table` is a typed shape, a row source and the name of the asset its rows come
from. It is final and becomes a relation only when a binding or projection reads
it.

```python
from estate.assets import Estate

class SiteTable(Table[Estate]):
    site_id: Field[str] = field()
```

The asset parameter is part of the declaration. A concrete table without one is
refused when the class is created.

| Member | Returns | Use |
| --- | --- | --- |
| `options` | `TableOptions` | Identity, description and annotations |
| `row_source()` | `RelationRowSource[Self]` | Start the row-source algebra |
| `where(predicate)` | `DerivedRowSource[Self]` | Shorthand for `row_source().where(...)` |
| `projection_base()` | A dynamic projection base | Inherit the table's fields as projection outputs |

The name defaults to the class name with one `Table` suffix removed and
converted to snake case, so `VisitTable` becomes `visit`. `description` defaults
to the class's own docstring; `options.description` wins. Description is not
inherited.

```python
from kg_build_system import Field, Table, TableOptions, field

from estate.assets import Estate


class SiteTable(Table[Estate]):
    """One site in the estate."""

    options = TableOptions(name="sites")
    site_id: Field[str] = field()
    name: Field[str] = field()
    region: Field[str] = field()
```

`SiteTable.site_id` is a `ValueSelection[str]` because it is declared
`Field[str]`; `SiteTable.row_source()` is the relation a binding reads. See
[Row sources](row-sources.md) for the algebra and [Projections](projections.md)
for `projection_base()`.

| Error | Trigger |
| --- | --- |
| `a final Table may not inherit from another final Table` | A `Table` subclass inherits another final `Table` |
| `X is a concrete Table without an asset; declare it as Table[Asset]` | A concrete table names no asset |
| `X must name an Asset subclass: Table[Asset]` | The parameter is not an `Asset` subclass |
| `Table.options must be a TableOptions value` | `options` is not a `TableOptions` |
| `<Class> is a Table declaration: declare TableOptions, not template options` | `options = StructOptionsTemplate(...)` on a table |
| `table names must be non-empty` | `TableOptions(name="")` |

## `Struct`

```python
class Struct:
    options: StructOptions
    # field members
```

A `Struct` is a nested-record shape. It is used as `Field[SomeStruct]`, never as
a row source, table-group member or table declaration. Its identity is the
`(module, qualname)` pair, so two structs with the same name in different modules
are distinct.

```python
from kg_build_system import Field, Struct, StructOptions, field


class ContactStruct(Struct):
    """A contact record inside a site row."""

    options = StructOptions(name="contact")
    email: Field[str] = field()
    phone: Field[str] = field()
```

A nested member keeps the nullability its declaration states: selecting `email`
from a present `ContactStruct` yields `ValueSelection[str]` for `Field[str]` and
`NullableSelection[str]` for `Field[str | None]`. A nullable carrier makes the
member nullable too. Reach members with `extract`; see
[Expressions and selections](expressions.md#extract).

| Error | Trigger |
| --- | --- |
| `Struct.options must be a StructOptions value` | `options` is not a `StructOptions` |
| `struct names must be non-empty` | `StructOptions(name="")` |
| `<Class> is a Struct declaration: declare StructOptions, not template options` | `options = StructOptionsTemplate(...)` on a struct |

## `ComputedStruct`

```python
class ComputedStruct:
    options: StructOptions
    # computed_field members
```

A `ComputedStruct` is a value-record declaration built from `computed_field`
members. It is usable as `Field[SomeComputedStruct]` and through `extract`, but
it has no `row_source()`, cannot be bound and cannot be a table-group member.

As a field type its member expressions are **type witnesses**: they fix each
member's logical type and nullability, are not evaluated, and do not add a row
plan. The carrier record supplies the value. A present carrier leaves a
non-null witness non-null; a nullable carrier makes the member nullable.

```python
from kg_build_system import (
    ComputedStruct, Field, Table, TableOptions, computed_field, field,
)

from estate.assets import Estate


class SiteSummaryStruct(ComputedStruct):
    site_id = computed_field(SiteTable.site_id.alter_rows().drop_null())
    region = computed_field(SiteTable.region)


class SummaryTable(Table[Estate]):
    options = TableOptions(name="summary")
    site_id: Field[str] = field()
    summary: Field[SiteSummaryStruct] = field()
```

| Error | Trigger |
| --- | --- |
| `ComputedStruct.options must be a StructOptions value` | `options` is not a `StructOptions` |
| `struct names must be non-empty` | `StructOptions(name="")` |
| `<Class>.<attribute> must be declared with computed_field()` | A `field()` member is declared on a computed struct |
| `<Class> is a ComputedStruct declaration: declare StructOptions, not template options` | Template options are used as the host options |

## `Projection`

```text
Projection(source: RowSource[S]) -> type[Projection]
```

`Projection(source)` returns a base pinned to one row source. Subclass it, give
the class a name and declare at least one output with `computed_field`. A
projection is a shape and a row source, but it is not a `Table` and names no
asset of its own.

An unpinned `class P(Projection)` with `projection_field(...)` outputs is the
compatibility form. Its plan is derived from the one logical source those
outputs read; the pinned form is preferred because it states the grain directly.
See [`projection_field()`](#projection_field).

```python
from kg_build_system import Projection, ProjectionOptions, computed_field


class SiteProjection(Projection(SiteTable.row_source())):
    options = ProjectionOptions(name="site_projection")
    site_id = computed_field(SiteTable.site_id.alter_rows().drop_null())
    label = computed_field(
        SiteTable.name.alter_rows().drop_null().expression.prepend("site::")
    )
```

| Error | Trigger |
| --- | --- |
| `projections require a row source` | An unpinned projection's outputs do not resolve to one driving source, at compile |
| `projections must declare at least one computed_field` | The projection has no output |
| `a final Projection may not inherit from another final Projection` | A final projection inherits another final projection |
| `projection names must be non-empty` | `ProjectionOptions(name="")` |
| `<Class>.<attribute> must be declared with computed_field()` | `field()` is used for an output |

The pin, outputs, `projection_base()` and dependency rules are on
[Projections](projections.md).

## `TableGroup`

```python
class TableGroup:
    options: TableGroupOptions
    # member attributes, or options.members
```

A `TableGroup` is a final named catalog of final tables and nested groups. It is
not a shape and not a row source. Members may be class attributes or the
`members` argument of `TableGroupOptions`.

```python
from kg_build_system import TableGroup, TableGroupOptions


class ReadingsTableGroup(TableGroup):
    """One relation per logger family."""

    options = TableGroupOptions(name="readings")
    temperature = TemperatureTable
    mechanical = MechanicalTableGroup
```

The group name defaults to the class name with one `TableGroup` suffix removed
and converted to snake case. A group is a catalog, not a source declaration: each
member table names its own asset. See [Assets](../concepts/assets.md).

| Error | Trigger |
| --- | --- |
| `table groups must declare at least one member` | The group has no table or group member |
| `table groups may contain only final Table or TableGroup declarations` | A member is not a final table or group |
| `a final TableGroup may not inherit from another final TableGroup` | A group inherits another final group |
| `table groups may not contain a cycle` | A group contains itself, directly or through nested groups |
| `a table group may include a final table only once` | The same table is reached through two catalog paths |
| `a table group has duplicate catalog paths` | Two members resolve to the same catalog path |
| `TableGroup.options must be a TableGroupOptions value` | `options` is not a `TableGroupOptions` |
| `table-group names must be non-empty` | `TableGroupOptions(name="")` |
| `<Class> is a TableGroup declaration: declare TableGroupOptions, not template options` | `options = StructOptionsTemplate(...)` on a group |

## `StructTemplate`

```python
class StructTemplate:
    options: StructOptionsTemplate
    # field members
```

`StructTemplate` shares field slots and annotation flow with `Table`, `Struct`
and `ComputedStruct`. It never becomes a declaration, has no name or description
and never enters the blueprint. Templates come first in the base list:
`class SiteTable(ProvenancedTemplate, Table[Estate])`.

A template's options must be `StructOptionsTemplate`, which carries annotations
only. A template may extend another template by naming it as its base. Mixing a
template into `Projection` or `TableGroup` is refused. A `ComputedStruct` host
accepts a template's annotations, but a source-backed template field fails there
because a computed host requires `computed_field`.

```python
from kg_build_system import (
    Field, StructOptionsTemplate, StructTemplate, Table, TableOptions, field,
)


class ProvenancedTemplate(StructTemplate):
    options = StructOptionsTemplate()
    source_version: Field[str] = field()


class SiteTable(ProvenancedTemplate, Table[Estate]):
    options = TableOptions(name="sites")
    site_id: Field[str] = field()
```

| Error | Trigger |
| --- | --- |
| `<Class> is a data template: its options must be StructOptionsTemplate, which carries no name or description — wrap it: ...` | A template uses `TableOptions` or `StructOptions` |
| `<Class> mixes StructTemplate into a non-record declaration: ...` | A template is mixed into `Projection` or `TableGroup` |
| `<Class>.<attribute> must be declared with computed_field()` | A source-backed template field reaches a `ComputedStruct` host |

## Options

| Option value | Signature | Fields |
| --- | --- | --- |
| `TableOptions` | `TableOptions(name=None, description=None, annotations=())` | Table identity, description and annotations |
| `StructOptions` | `StructOptions(name=None, description=None, annotations=())` | Struct or computed-struct identity, description and annotations |
| `ProjectionOptions` | `ProjectionOptions(name=None, description=None, annotations=())` | Projection identity, description and annotations |
| `TableGroupOptions` | `TableGroupOptions(members=(), name=None, description=None, annotations=())` | Group members plus identity, description and annotations |
| `StructOptionsTemplate` | `StructOptionsTemplate(annotations=())` | Template annotations only; no name or description |

Every option value is frozen. `name` must be non-empty when supplied.
`description` defaults to the declaration's own docstring and is never
inherited. `annotations` is a sequence of `Annotation` values; see
[Semantics and annotations](../concepts/semantics.md).

## What to remember

- `field()` declares source backing; `computed_field()` declares expression
  backing. The host decides which is legal.
- `Field[T]` names a value type. A source read follows the declaration: `Field[T]`
  is non-null and `Field[T | None]` is nullable.
- `Table`, `TableGroup` and `Projection` are final. `Struct` and
  `ComputedStruct` are value records, not row sources.
- `Table[Asset]` names the logical source of a table; the asset and its
  optional layout carry location, format and credential reference.
- A name, description and annotation are declaration metadata; they never
  become fields or graph properties.

Next: [Expressions and selections](expressions.md) turn these rows into values.
