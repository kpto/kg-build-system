# Projections

A projection is a named relation. It fixes one row plan, gives that plan a
logical name, and publishes a fixed set of typed output fields. The name is the
point: other declarations refer to the projection, not to the expression tree
that computes it. Once declared, it can feed any number of bindings and later
projections, and each consumer receives the same rows with the same outputs.

## What a projection is

`Projection` is both a `Shape` and a `RowSource`. As a shape it has fields that
selections and expressions can read; as a row source it can be passed as
`rows=` to a binding. `Projection.row_source()` returns that row source
explicitly as a `RelationRowSource`.

Reading `DefectProjection.defect_id` anywhere returns a reference to the
projection's output field. It does not re-evaluate, copy or embed the
expression that produced it. This is what lets projections compose without
duplicating row plans.

A projection is not a `Table`. It has no physical source of its own; its rows
come from the row source it pins. [Sources](sources.md) covers the physical
side.

## Declaring a projection

Every projection is pinned to a row source at class creation time. Pass the
source's row source to `Projection(...)`, declare at least one output with
`computed_field(expression)`, and name the class:

!!! note "The examples use the framework's reference project"
    `reference_project` is a small worked project in the framework repository.
    In your project, substitute your own tables; the projection API is the same.

```python
from kg_build_system import Projection, computed_field

from reference_project.table.surveys import SurveysTable

area = SurveysTable.areas.alter_rows().expand()
element = area.extract(lambda value: value.elements).alter_rows().expand()


class ElementProjection(Projection(SurveysTable.row_source())):
    """One row per surveyed element."""

    survey_id = computed_field(SurveysTable.survey_id.alter_rows().drop_null())
    unit_ref = computed_field(element.extract(lambda value: value.unit_ref))
```

`class ElementProjection(Projection):` is rejected at class creation with
`ElementProjection must be pinned to a row source:
Projection(source.row_source())`. The pin records the source relation
and its filters in the projection's definition; consumers of the projection see
those rows. The pin names the row source; it does not copy fields. Declare the
outputs explicitly.

A projection's type is inferred from each expression, including nullability.
`computed_field` is the only way to declare an output; `field()` is rejected
because a projection has no source columns of its own. A non-null expression
publishes a non-null field, and a nullable expression publishes a nullable field
until you narrow it with `alter_rows().drop_null()` or `default_to(...)`; both are
covered in [Expressions](expressions.md).

!!! warning "Projections are final"

    A projection class with no effective output field fails at class creation. A
    final projection is terminal: it may not inherit from another final
    `Projection`. Shape reuse is expressed with `projection_base()` or by pinning
    a new source.

### Row behaviour

Every field in one projection shares a single row plan. An
`alter_rows().expand()` or `alter_rows().drop_null()` written for one field
therefore applies to the whole projection. Expanding `areas` produces one row
per area; expanding `elements` on top produces one row per element. Expanding
two unrelated arrays multiplies the two fan-outs. The second grain must be its
own projection, as the reference project does.

## When to create one

Create a projection when at least one of these is true.

- **Several consumers need the same rows.** Four bindings reading the same
  filtered, flattened grain is one projection referenced four times. Repeating
  the plan in four bindings means four places to change.
- **The rows have a genuinely new grain.** An expansion changes the row count,
  so the result cannot live in the source's own relation. The reference
  project's `DefectProjection` flattens a survey document to one row per defect,
  and `ObservationProjection` consumes it to reach one row per observation.
- **You need a stable name in the build.** Diagnostics, the blueprint and other
  projections refer to the projection's logical name. An anonymous filtered row
  source has no such name.

Do not create one merely to rename a field or filter for a single binding.

## The difference from `where`

`Table.row_source().where(predicate)` and
`Projection.row_source().where(predicate)` return a `DerivedRowSource`, not a
projection. `Table.where(predicate)` and `Projection.where(predicate)` are the
shorthand. The result preserves the shape and filters rows;
`DerivedRowSource.where(predicate)` chains another filter and still preserves
the shape. It does not add outputs, change the grain, or enter the build under
a name.

```python
from kg_build_system import Field, Table, any_of, field


class SiteRow(Table):
    site_id: Field[str] = field()
    name: Field[str] = field()
    region: Field[str] = field()


north = SiteRow.row_source().where(
    lambda site: any_of(
        site.region.alter_rows().drop_null().expression.equals("north"),
        site.region.alter_rows().drop_null().expression.equals("west"),
    )
)
```

The predicate receives a symbolic shape instance and reads source fields through
nullable selections, so comparisons narrow first. Pass `north` as `rows=` for a
one-off binding; the binding receives the filtered rows and no named relation is
created. The distinction is:

| | `where(...)` result | Named projection |
| --- | --- | --- |
| Is a class you can import and reuse | No, an instance | Yes |
| Can add outputs | No | Yes |
| Can change the grain | No | Yes |
| Has a logical name | No | Yes |
| Referenced by `computed_field` elsewhere | No | Yes |

Use `where` for a one-off filter. Use a projection when the filtered or
reshaped rows are a fact other declarations depend on.

## Reusing a row plan with `projection_base`

`projection_base()` turns a row source into a class base that carries that
source's plan and inherited output fields. It exists on `Table`, on `Projection`,
on `RelationRowSource`, and on `DerivedRowSource`, so a filtered source can be
named without repeating its predicate:

```python
class NorthernSitesProjection(north.projection_base()):
    """The northern and western sites, under a name bindings can share."""
```

The base inherits the source's fields as computed outputs, all typed from the
source's nullable access. Read them as nullable selections, exactly like the
fields they came from. When the subclass declares fields of its own, declare them
with `computed_field` as usual:

```python
class NorthernLabelsProjection(NorthernSitesProjection.projection_base()):
    label = computed_field(
        NorthernSitesProjection.site_id.alter_rows().drop_null()
        .expression.prepend("site::")
    )
```

Inherited fields keep working. A declared field with the same Python attribute
shadows the inherited one, exactly as Python attribute shadowing works. Two
fields with the same external name but different attributes are rejected at
class creation. The base returned by `projection_base()` is not a final
projection and does not itself enter the build; only the named class you finish
does.

## Projections built on projections

A projection field may read another projection's output. Because that read is a
reference to the named relation, no row plan is embedded twice:

```python
from kg_build_system import Projection, computed_field

from reference_project.table.projections.defects import DefectProjection

observation = DefectProjection.observations.alter_rows().expand()


class ObservationProjection(Projection(DefectProjection.row_source())):
    """One row per observation taken against a defect."""

    defect_id = computed_field(DefectProjection.defect_id)
    observation_uid = computed_field(
        observation.extract(lambda value: value.observation_uid)
    )
```

`defect_id` keeps the nullability of the defect projection's output; narrow it in
the binding if the consumer needs a present value. This is the normal way to
change grain: build the coarser relation once, then consume its outputs at the
next grain. Projection dependencies must be acyclic; a cycle fails compilation
and names the projections involved.

## Computed structs

A `ComputedStruct` is a value-record declaration: its members are declared with
`computed_field`, and each member is typed by its expression. It is usable as a
field type (`Field[SomeComputedStruct]`) and through `extract`, exactly like a
source struct. It is **not** a table or a row source: it has no
`row_source()`, cannot be bound, and cannot be a table-group member.

```python
from kg_build_system import ComputedStruct, Field, Table, computed_field, field


class ReadingTable(Table):
    reading_uid: Field[str] = field()
    deg_c: Field[float] = field()


class ReadingSummaryStruct(ComputedStruct):
    """The members a reading summary exposes."""

    reading_uid = computed_field(ReadingTable.reading_uid.alter_rows().drop_null())
    deg_c = computed_field(ReadingTable.deg_c)


class SummaryTable(Table):
    reading_uid: Field[str] = field()
    summary: Field[ReadingSummaryStruct] = field()
```

The member expression fixes the member's type. `extract` composes the
nullability of the record that carries the struct with that member type:

```python
summary = SummaryTable.summary.alter_rows().drop_null()   # StructSelection
uid = summary.extract(lambda value: value.reading_uid)    # ValueSelection[str]
deg_c = summary.extract(lambda value: value.deg_c)        # NullableSelection[float]
```

A present parent leaves a non-null member non-null; the same member under a
nullable parent becomes nullable. A nullable source field that carries the
struct reads nullable, like every other source field.

## Naming and describing the relation

A projection's name is inferred from its class name: one trailing `Projection`
is removed and the rest becomes snake case. `DefectProjection` becomes
`defect`. Override it with `ProjectionOptions`, which also carries a
description and annotations:

```python
from kg_build_system import ProjectionOptions


class SurveyDefectProjection(DefectProjection.projection_base()):
    options = ProjectionOptions(
        name="survey_defect",
        description="One row per defect found during a survey.",
    )
```

A projection name must be unique among projections and among table names,
because both are logical relation names that field references resolve against.
Naming a projection `surveys` while a table called `surveys` exists fails
compilation. `options.description` wins over the class docstring;
`options.annotations` attaches portable metadata, described in
[Annotations and descriptions](annotations.md).

`computed_field` accepts `name`, `description` and `annotations`. `name` is the
output's external name and defaults to the Python attribute in snake case.
`description` documents it; a string written below the assignment is not read.
`annotations` is a sequence of `Annotation` values carried in the blueprint. Two
outputs in one projection may not share an external name.

## One driving source

A projection has one driving source. All field expressions must read that
source, possibly through chained expansions and struct navigation. Referencing
two unrelated relations from one projection is not an implicit cross product;
the build fails with `a relational product requires one driving source;
additional sources must be introduced by an explicit lookup`.

The error names an explicit lookup, but the current API has no join operation to
create one. Combine two relations by binding each side separately, or build the
combined value in a row source that already contains it. Do not rely on a
projection to join them.

Name a projection when more than one declaration reads the same rows, give a
new grain its own projection, and let nullability show through rather than
assuming it. Continue with [Topology](topology.md) to give these rows graph
meaning, and [Bindings](bindings.md) to connect them.

## What to remember

- A projection is a named relation with its own row plan and typed outputs.
- `Projection(source.row_source())` is required; a direct `class P(Projection)`
  is rejected.
- Projection outputs use `computed_field`; they carry the expression's type and
  nullability.
- Give a new grain a projection, and give one grain reused by several bindings a
  projection too.
- Reading a projection field reuses its output, not the calculation behind it.
- A `ComputedStruct` is a value record, not a row source.
- One projection has one driving source. The current API has no join; combine
  relations through separate bindings.

Next: [Topology](topology.md) gives these rows graph meaning.
