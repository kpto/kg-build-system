# Projections

A projection is a named relation with one row plan, publishing a fixed set of typed outputs.

A row source can describe a grain, but an anonymous plan has no name and no stable output surface. When several bindings, or a later projection, need the same rows, repeating the plan in each place lets the copies drift. A projection is the name and the contract: other declarations refer to the projection, and every consumer receives the same rows with the same outputs.

## The problem: a grain with several consumers

A defect sits between a unit and an observation. The defect node, the edge from its unit, and the observation grain all start from the same rows: units joined to defects.

If each declaration writes that join itself, the build has three copies of one decision. Change the join key or the filter, and you must find every copy. A projection states the grain once.

## The model

`Projection` is both a shape and a row source. As a shape it has output fields that selections and computed fields can read; as a row source it can be passed as `rows=` to a binding.

A projection is normally **pinned** to a row source when the class is created. Pin a table or projection relation with `Projection(source.row_source())`, or pin a derived plan with `Projection(derived)`.

The compatibility spelling `class DefectProjection(Projection)` with
`projection_field(...)` outputs also works. Its row plan is derived from the one
logical source those outputs read; if they read no source or several unrelated
sources, compilation fails with `projections require a row source`. It is
supported for existing projects; a new projection should state its pin.

Declare each output with `computed_field(expression)`, or with
`projection_field(...)` in the unpinned compatibility form; the latter is the
older spelling of the same constructor. The output takes the expression's logical
type and nullability:

- A non-null expression publishes a non-null output.
- A nullable expression publishes a nullable output until you narrow or default it.

Reading a projection field anywhere else returns a reference to that materialised output, not a fresh evaluation of the expression behind it. This is what lets projections compose without embedding a row plan twice.

## Example: one row per defect

The page uses the same site, unit and defect model as [row sources](row-sources.md). A defect carries its observations as a nested array.

```python
from kg_build_system import Array, Field, Struct, Table, field


class ObservationStruct(Struct):
    observation_uid: Field[str] = field()
    value: Field[float] = field()


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

Join the two tables, then pin the join to a projection:

```python
from kg_build_system import Projection, computed_field

unit_defects = UnitTable.row_source().join(
    DefectTable.row_source(),
    on=lambda unit, defect: (unit.unit_ref, defect.unit_ref),
)


class DefectProjection(Projection(unit_defects)):
    """One row per defect, with the unit it belongs to."""

    defect_id = computed_field(
        unit_defects.shape.right.extract(lambda defect: defect.defect_id)
        .alter_rows().drop_null()
    )
    title = computed_field(
        unit_defects.shape.right.extract(lambda defect: defect.title)
    )
    severity = computed_field(
        unit_defects.shape.right.extract(lambda defect: defect.severity)
    )
    unit_ref = computed_field(
        unit_defects.shape.left.extract(lambda unit: unit.unit_ref)
    )
    observations = computed_field(
        unit_defects.shape.right.extract(lambda defect: defect.observations)
    )
```

`defect_id` is non-null because the expression drops nulls before publishing it. `title`, `severity` and `unit_ref` keep the nullability their source declarations carry. A binding that needs a present defect key can use `DefectProjection.defect_id` directly.

The defect node binding and the unit-to-defect edge binding both pass `DefectProjection.row_source()` as `rows=`. Neither repeats the join.

## A second grain

One projection has one row plan, so one projection produces one grain. Expanding the observations array changes the row count from one row per defect to one row per observation. That needs its own projection:

```python
observation = (
    DefectProjection.observations
    .alter_rows().drop_null()
    .alter_rows().expand()
)


class ObservationProjection(Projection(DefectProjection.row_source())):
    """One row per observation taken against a defect."""

    defect_id = computed_field(DefectProjection.defect_id)
    observation_uid = computed_field(
        observation.extract(lambda item: item.observation_uid)
    )
    value = computed_field(observation.extract(lambda item: item.value))
```

`ObservationProjection` pins the defect relation, expands its observations, and carries `defect_id` through. The edge from an observation back to its defect can use that output without joining the survey tables again.

## One row plan, one driving source

Every field in a projection shares a single row plan. An `alter_rows().expand()` or `alter_rows().drop_null()` written for one field applies to the whole projection, because it changes the relation rather than one value.

Two consequences follow:

- Expanding two unrelated arrays in one projection multiplies their fan-outs. Give the second grain its own projection.
- A `drop_null()` in one field can remove rows from every field in the projection. Use it when the row cannot exist without that value, and `default_to()` when the row must survive.

A projection has one driving source. All field expressions must read that source, possibly through chained expansions and struct navigation. A projection does not join implicitly: if you reference two unrelated relations, the build refuses it. Build the join, union or group in a row source and pin that result instead.

## When to create one

Create a projection when at least one of these is true:

- **Several consumers need the same rows.** One projection referenced by several bindings is one place to change.
- **The rows have a new grain.** An expansion changes the row count, so the result cannot live in the source relation.
- **The grain needs a stable name.** Diagnostics, the blueprint and other projections refer to the projection's logical name.

Do not create a projection merely to rename a field or to filter rows for a single binding. Use a row source for a one-off filter.

## Reuse a row plan with projection_base

`projection_base()` turns a row source into a class base carrying that source's plan and inherited output fields. It exists on `Table`, `Projection`, `RelationRowSource` and `DerivedRowSource`:

```python
active_units = UnitTable.row_source().where(
    lambda unit: unit.status.alter_rows().drop_null().expression.equals("active")
)


class ActiveUnitProjection(active_units.projection_base()):
    """The active units, under a name bindings can share."""
```

The base inherits the source's fields as outputs, typed from the fields' declared access. A subclass can add outputs with `computed_field`; a declared field with the same attribute shadows the inherited one. The base itself is not a final projection and does not enter the build. Only the named class you finish does.

A final projection is terminal and may not inherit from another final `Projection`. Reuse a plan with `projection_base()` or pin a new source.

## Names and descriptions

A projection's logical name is inferred from its class name: remove one trailing `Projection` and convert the rest to snake case. `DefectProjection` becomes `defect`.

`ProjectionOptions` overrides the name and carries a description and annotations:

```python
from kg_build_system import ProjectionOptions


class SurveyDefectProjection(DefectProjection.projection_base()):
    options = ProjectionOptions(
        name="survey_defect",
        description="One row per defect found during a survey.",
    )
```

A projection name must be unique among projections and table names, because both are logical relation names that field references resolve against. `options.description` wins over the class docstring; the description is own-only and is not inherited from a base.

## Computed structs

A `ComputedStruct` is a value-record declaration whose members are written with `computed_field`. It describes a record that a row already carries. It is not a table, a projection or a row source: it has no `row_source()`, cannot be bound, and cannot be a table-group member.

When you use a `ComputedStruct` as `Field[T]`, its member expressions are **type witnesses**. They fix each member's logical type and nullability, but they are not evaluated and do not become a row plan. Read the member through `extract`; the carrier row supplies the value. If a value must be calculated from another relation, declare it on a projection instead.

## Limits

- A projection declares at least one output. Prefer a pinned projection; the unpinned `projection_field` form is a compatibility spelling.
- `computed_field` declares an output. `projection_field` is the compatibility spelling; `field()` is refused because a projection has no source columns of its own.
- One projection has one row plan and one driving source. A new grain needs a new projection.
- A final projection may not inherit from another final projection.
- Projection dependencies must be acyclic; a cycle fails compilation.
- A `ComputedStruct` is a value record, not a row source. It cannot be pinned, bound or used as a table-group member.

## What to remember

- A projection is a named relation with one row plan and typed outputs.
- Prefer pinning it with `Projection(source.row_source())` or
  `Projection(derived)`; the unpinned `projection_field` form is a compatibility
  spelling.
- Reading a projection field reuses the materialised output, not the calculation.
- All fields share the row plan, so one expansion or null drop affects the whole projection.
- Give every grain its own projection, and name a grain when several declarations read it.

## Next steps

- [Topology](topology.md) gives the rows graph meaning.
- [Bindings](bindings.md) connect the projection's outputs to node and edge properties.

## Reference

[Projections reference](../reference/projections.md) lists the pinning rules, output declaration, naming options and errors.
