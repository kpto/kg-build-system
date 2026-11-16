---
title: Derived relations reference
summary: "The exact DerivedRelation and Stage surface: the contract, pinning a row source, computed_field outputs, dependencies, row behaviour and naming."
section: reference
perspective: reference
order: 110
status: normative
verified: 2026-11-15
sources:
  - kg_build_system/distribution/languages/data/model/public/declarations.py
  - kg_build_system/distribution/languages/data/model/public/fields.py
  - kg_build_system/distribution/languages/data/service/public/fields.py
  - kg_build_system/distribution/languages/data/service/_private/declarations.py
  - kg_build_system/distribution/languages/data/service/_private/descriptors.py
---

## Surface

A derived relation names one row plan, publishes typed outputs computed from that row and states a contract a consumer may depend on. `DerivedRelation` is a shape, a row source and a published relation. `DerivedRelation(source)` pins exactly one row-source value; subclass it, declare the contract in `options`, declare at least one output with `computed_field`, and name the class.

`Stage` is the private counterpart. A stage pins one row source and declares outputs, but it is not a consumer relation, is not bindable and carries no meaning. Use a stage for one reviewable step inside a derived relation; use a derived relation for anything a binding or another declaration reads.

| Need | Write |
| --- | --- |
| Pin a relation or derived plan | `class R(DerivedRelation(source))` |
| State the relation's promise | `options = DerivedRelationOptions(contract=Contract(definition=..., meaning=...))` |
| Publish an output | `computed_field(selection, definition=FieldDefinition(...), name=..., meaning=..., annotations=...)` |
| Read the derived relation as a relation | `R.row_source()` |
| Keep one step private | `class DefectCauseStage(Stage(source))` with `options = StageOptions(definition=...)` |

The model and the choice of grain are on [Project rows](/book/part-2/05-grain-and-projections), the binding rules on the [Grain spec](/appendix/spec/grain), and the subject index entry for [Grain](/appendix/subjects/grain). Selection typing is on the [Selection spec](/appendix/spec/selection), the subject index entry for [Selection](/appendix/subjects/selection), and the exact value surface on [Expressions reference](/appendix/reference/expressions). The source algebra is on [Row sources reference](/appendix/reference/row-sources); declarations are on [Declarations](/appendix/reference/declarations); a derived relation is consumed by [Bindings](/appendix/reference/bindings) that target [Topology](/appendix/reference/topology).

## Details

The examples use these declarations:

```python
from kg_build_system import (
    Array, Claim, Contract, Definition, Field, FieldDefinition, Meaning,
    Omitted, SourceRelation, SourceRelationOptions, Struct, field,
)


class ContactStruct(Struct):
    email: Field[str] = field(meaning=Omitted)


from estate.assets import Estate

class SiteSourceRelation(SourceRelation[Estate]):
    options = SourceRelationOptions(
        contract=Contract(
            definition=Definition(grain="one row per site", identity=("site_id",)),
            meaning=Meaning(claims=(Claim("One row names one estate site."),)),
        ),
    )
    site_id: Field[str] = field(
        definition=FieldDefinition(value="the site's stable identifier"),
        meaning=Omitted,
    )
    name: Field[str] = field(
        definition=FieldDefinition(value="the site's display name"),
        meaning=Omitted,
    )
    region_id: Field[str] = field(
        definition=FieldDefinition(value="the region the site belongs to"),
        meaning=Omitted,
    )
    tags: Field[Array[str]] = field(
        definition=FieldDefinition(value="the site's tags"),
        meaning=Omitted,
    )
    contacts: Field[Array[ContactStruct]] = field(
        definition=FieldDefinition(value="the site's contact records"),
        meaning=Omitted,
    )


class ReadingSourceRelation(SourceRelation[Estate]):
    options = SourceRelationOptions(
        contract=Contract(
            definition=Definition(grain="one row per reading", identity=("reading_id",)),
            meaning=Meaning(claims=(Claim("One row names one logger reading."),)),
        ),
    )
    reading_id: Field[str] = field(
        definition=FieldDefinition(value="the reading's stable identifier"),
        meaning=Omitted,
    )
    site_id: Field[str] = field(
        definition=FieldDefinition(value="the site the reading belongs to"),
        meaning=Omitted,
    )
```

### `DerivedRelation(source)`

```text
DerivedRelation(source: RowSource[S]) -> type[DerivedRelation]
```

`DerivedRelation(source)` returns a base pinned to one row source. Subclass it, declare at least one output with `computed_field`, and give it a contract in `options`.

| Parameter | Type | Meaning |
| --- | --- | --- |
| `source` | row-source value | The relation or derived plan the derived relation reads |

```python
from kg_build_system import (
    Claim, Contract, Definition, DerivedRelation, DerivedRelationOptions,
    FieldDefinition, Meaning, Omitted, Purpose, computed_field,
)


class SiteDerivedRelation(DerivedRelation(SiteSourceRelation.row_source())):
    """One row per site, with a display label."""

    options = DerivedRelationOptions(
        contract=Contract(
            definition=Definition(grain="one row per site", identity=("site_id",)),
            meaning=Meaning(
                purpose=Purpose("Name a site for a graph reference."),
                claims=(Claim("One row carries one site's display label."),),
            ),
        ),
    )
    site_id = computed_field(
        SiteSourceRelation.site_id.alter_rows().drop_null(),
        definition=FieldDefinition(value="the site's stable identifier"),
        meaning=Omitted,
    )
    label = computed_field(
        SiteSourceRelation.name.alter_rows().drop_null().prepend("site::"),
        definition=FieldDefinition(value="the site's display label"),
        meaning=Omitted,
    )
```

`DerivedRelation(SiteSourceRelation.row_source())` pins the relation and records its filters in the compiled declaration. A filtered, joined, grouped or unioned source is passed directly: `DerivedRelation(joined)`. The pin does not copy fields; declare the outputs explicitly.

A derived relation is final and terminal. It may not inherit from another final `DerivedRelation`; pin a new source instead.

| Member | Returns | Use |
| --- | --- | --- |
| `options` | `DerivedRelationOptions` | Identity, annotations and the contract |
| `row_source()` | `RelationRowSource[Self]` | Read the derived relation as a relation; `.shape` is a generated view carrying the declaration's field selections |

| Error | Trigger |
| --- | --- |
| `requires a row source` | `DerivedRelation()` is called without a source, or a class is declared as `class R(DerivedRelation)` |
| `derived relations must declare at least one computed_field` | The derived relation has no output |
| `a final DerivedRelation may not inherit from another final DerivedRelation` | A final derived relation inherits another final derived relation |
| `a derived relation requires a Contract with a Definition and a Meaning` | `options.contract` is absent or incomplete |
| `a derived relation contract requires a purpose` | The contract's meaning carries claims only |
| `rows must be a row source value; use SourceRelation.row_source() or DerivedRelation.row_source()` | `DerivedRelation` is pinned to a declaration class rather than a row-source value |

### The contract

A derived relation is a published relation, so its options carry a `Contract`, not a bare `Meaning`:

```python
Contract(
    definition=Definition(grain: str, identity: tuple[str, ...]),
    meaning=Meaning(purpose=Purpose(...), claims=()),
)
```

| Part | States | Required |
| --- | --- | --- |
| `Definition` | What one row is and what identifies it | Yes; `grain` is non-empty and `identity` names real outputs |
| `Meaning` | The relation's purpose, claims and limitations | Yes; at least one unit, including a purpose |

The definition is the grain a binding checks. The meaning is the domain use, not a description of the step that produced the relation. A derived relation may have several consumers; the contract is the same for all of them.

A stage has no contract. It carries a `Definition` and no `Meaning`, because it is not a promise to a consumer.

### `computed_field()`

```python
def computed_field[T: DeclaredValue] (
    value: Selection[T],
    *,
    definition: FieldDefinition | None = None,
    name: str | None = None,
    annotations: Sequence[Annotation] = (),
    meaning: Meaning | type[Omitted],
) -> Field[T]: ...
```

Declares one output. `value` is a selection; the output is typed by its logical type. A `FieldDefinition` is optional: it states what the output, its unit and its absence mean, and the relation contract never copies it.

| Parameter | Type | Meaning | Default |
| --- | --- | --- | --- |
| `value` | `Selection[T]` | The output selection | Required |
| `definition` | `FieldDefinition or None` | What the output, its unit and its absence mean | `None`; state it wherever the name and type cannot answer |
| `name` | `str or None` | External output name | Snake case of the attribute; one trailing `_` is removed |
| `annotations` | `Sequence[Annotation]` | Portable output metadata | `()` |
| `meaning` | `Meaning or Omitted` | The output's own meaning, or the explicit opt-out | Required |

```python
class SiteOutputDerivedRelation(DerivedRelation(SiteSourceRelation.row_source())):
    options = DerivedRelationOptions(contract=...)
    site_id = computed_field(
        SiteSourceRelation.site_id.alter_rows().drop_null(),
        name="site_id",
        definition=FieldDefinition(value="the site's stable identifier"),
        meaning=Omitted,
    )
    region_id = computed_field(
        SiteSourceRelation.region_id,
        definition=FieldDefinition(value="the region the site belongs to"),
        meaning=Omitted,
    )
```

| Output selection | Read result |
| --- | --- |
| Present scalar | `Selection[T]` |
| Nullable scalar | `Selection[Nullable[T]]` |
| Present array | `Selection[Array[T]]` |
| Nullable array | `Selection[Nullable[Array[T]]]` |
| Present struct | `Selection[S]` |
| Nullable struct | `Selection[Nullable[S]]` |

`field()` is not legal for a derived-relation output; a derived relation has no source columns of its own. Reading `SiteDerivedRelation.site_id` anywhere returns the relation's materialised output, not the selection that produced it.

| Error | Trigger |
| --- | --- |
| `<Class>.<attribute> must be declared with computed_field()` | `field()` is used for an output |
| `<Class> fields 'x' and 'y' share external name 'name'` | Two outputs resolve to the same external name |
| `<Class>.<attribute> must have a Field[T] annotation` | The output has no `Field[T]` annotation |
| `computed field names must be non-empty` | `computed_field(..., name="")` |

### Outputs and dependencies

- A derived relation has one driving source. All output selections must read that source, possibly through chained expansions and struct navigation.
- A reference to another derived relation's output is a dependency, not an embedded row plan. Reading that field reuses the named relation.
- Derived relation dependencies must be acyclic. A cycle fails compilation with `derived relation dependency cycle includes 'name'`.
- A derived relation that references two unrelated relations fails compilation with `a relational product requires one driving source; additional sources must be introduced by an explicit lookup`. Build the relation first and pin it, or use `lookup` to read the second relation by key.
- A derived relation name must be unique among derived relations and among logical source names; source relations and derived relations share the relation namespace.

```python
joined = SiteSourceRelation.row_source().join(
    ReadingSourceRelation.row_source(),
    on=lambda site, reading: (site.site_id, reading.site_id),
    how="left",
)


class SiteReadingDerivedRelation(DerivedRelation(joined)):
    """One row per site-reading pair."""

    options = DerivedRelationOptions(contract=...)
    site_id = computed_field(
        joined.shape.left.extract(lambda left: left.site_id)
        .alter_rows().drop_null(),
        definition=FieldDefinition(value="the site's stable identifier"),
        meaning=Omitted,
    )
    reading_id = computed_field(
        joined.shape.right.extract(lambda right: right.reading_id),
        definition=FieldDefinition(value="the reading's stable identifier"),
        meaning=Omitted,
    )
```

A grouped source is pinned the same way.

| Compile error | Trigger |
| --- | --- |
| `a relational product requires one driving source; additional sources must be introduced by an explicit lookup` | Outputs read unrelated relations |
| `derived relation dependency cycle includes 'name'` | Derived relations depend on each other in a cycle |
| `derived relation names must be unique` | Two derived relations share a logical name |
| `logical source names must be unique` | A derived relation and a source relation share a logical name |

A second relation can be read inline with `lookup`, without making it a scan of the derived relation:

```python
class SiteWithRegionDerivedRelation(DerivedRelation(SiteSourceRelation.row_source())):
    options = DerivedRelationOptions(contract=...)
    site_id = computed_field(
        SiteSourceRelation.site_id.alter_rows().drop_null(),
        definition=FieldDefinition(value="the site's stable identifier"),
        meaning=Omitted,
    )

    region_name = computed_field(
        SiteSourceRelation.region_id.lookup(
            RegionSourceRelation, SiteSourceRelation.region_id
        )
        .alter_rows().drop_null()
        .alter_rows().expand()
        .extract(lambda region: region.name),
        definition=FieldDefinition(value="the region's display name"),
        meaning=Omitted,
    )
```

### Row behaviour

Every field in one derived relation shares a single row plan. An expansion or a drop written for one output applies to the whole relation:

```python
class ContactDerivedRelation(DerivedRelation(SiteSourceRelation.row_source())):
    """One row per contact."""

    options = DerivedRelationOptions(contract=...)
    site_id = computed_field(
        SiteSourceRelation.site_id.alter_rows().drop_null(),
        definition=FieldDefinition(value="the site's stable identifier"),
        meaning=Omitted,
    )
    email = computed_field(
        SiteSourceRelation.contacts.alter_rows().drop_null()
        .alter_rows().expand()
        .extract(lambda contact: contact.email)
        .alter_rows().drop_null(),
        definition=FieldDefinition(value="the contact's email address"),
        meaning=Omitted,
    )
```

`SiteSourceRelation.contacts` is expanded once, so every output sees one row per contact. Expanding two unrelated arrays multiplies the two fan-outs. A further new grain needs its own derived relation, not a second expansion in the same class.

### Stages

A stage is a private step inside one derived relation:

```python
# relation/derived/defect_relation/_stage_cause.py
from kg_build_system import (
    Definition, FieldDefinition, Omitted, Stage, StageOptions,
    computed_field,
)


class DefectCauseStage(Stage(DefectSourceRelation.row_source())):
    options = StageOptions(
        definition=Definition(
            grain="one row per defect cause",
            identity=("defect_id", "cause_id"),
        ),
    )
    defect_id = computed_field(
        DefectSourceRelation.defect_id.alter_rows().drop_null(),
        definition=FieldDefinition(value="the defect's stable identifier"),
        meaning=Omitted,
    )
    cause_id = computed_field(
        DefectSourceRelation.cause_id.alter_rows().drop_null(),
        definition=FieldDefinition(value="the cause's stable identifier"),
        meaning=Omitted,
    )
```

| Rule | Stage | DerivedRelation |
| --- | --- | --- |
| Names a class | `class Name(Stage(source))` | `class Name(DerivedRelation(source))` |
| Carries a `Definition` | Yes | Yes |
| Carries a `Meaning` | No | Yes, with a purpose |
| Consumer relation | No | Yes |
| Stored in `data.derived_relations` | `visibility="internal"` | `visibility="public"` |
| Bindable | No; `StageRowSource` | Yes; `RelationRowSource` |
| Importable outside its package | No | Yes |
| Appears in the viewer | No | Yes |

A stage has no `Contract`, no purpose, no claims and no limitations. The meaning of the rows is stated once, on the `DerivedRelation`, and the binding that reads it states the fulfilment. A structure test refuses a stage import across a package boundary; `Stage.row_source()` returns a `StageRowSource`, and `node_binding` and `edge_binding` refuse it at construction and in the type checker.

### A published relation is record-agnostic

- A published derived relation must be stateable without the graph record it feeds.
- It must not name the record's property names, build key, endpoint tokens or component class.
- If a relation exists only to produce one record's fields, it is a record-shaped staging relation: keep it private as a stage or move the decision to the binding.
- The binding is the only place that knows both the relation and the record.

A relation whose definition is the record's grain, whose outputs are the record's properties and whose identity is the record's key is the record in disguise. The binding would then copy, not fulfil. State the domain relation and let the binding resolve identity, coverage and the gaps.

### Naming and options

```python
from kg_build_system import DerivedRelationOptions

class SiteLabelDerivedRelation(DerivedRelation(SiteSourceRelation.row_source())):
    options = DerivedRelationOptions(
        name="site_label",
        contract=Contract(
            definition=Definition(
                grain="one row per site",
                identity=("site_id",),
            ),
            meaning=Meaning(
                purpose=Purpose("Read each site's shared display label."),
            ),
        ),
    )

    site_id = computed_field(
        SiteSourceRelation.site_id.alter_rows().drop_null(),
        definition=FieldDefinition(value="the site's stable identifier"),
        meaning=Omitted,
    )
    label = computed_field(
        SiteSourceRelation.name.alter_rows().drop_null().prepend("site::"),
        definition=FieldDefinition(value="the site's display label"),
        meaning=Omitted,
    )
```

The name defaults to the class name with one `DerivedRelation` suffix removed and converted to snake case, so `SiteLabelDerivedRelation` becomes `site_label`. The contract carries the relation's meaning; it is not inherited. `options.annotations` attaches portable metadata. An explicit `computed_field(name=...)` wins over the output's snake-case attribute name.

| Error | Trigger |
| --- | --- |
| `DerivedRelation.options must be a DerivedRelationOptions value` | `options` is not a `DerivedRelationOptions` |
| `<Class> is a DerivedRelation declaration: declare DerivedRelationOptions, not template options` | `options = StructOptionsTemplate(...)` on a derived relation |
| `derived relation names must be non-empty` | `DerivedRelationOptions(name="")` |

For a binding that reads a published derived relation, see [Bindings reference](/appendix/reference/bindings). For the declaration surface, see [Declarations](/appendix/reference/declarations). For the algebra that produces the pinned source, see [Row sources](/appendix/reference/row-sources).
