---
title: Declarations
summary: The exact field, source-relation, struct, derived-relation, stage and group declarations, contracts, options and refusal messages.
section: reference
perspective: reference
order: 60
status: normative
verified: 2026-11-15
sources:
  - kg_build_system/distribution/languages/data/model/public/declarations.py
  - kg_build_system/distribution/languages/data/model/public/fields.py
  - kg_build_system/distribution/languages/data/service/_private/declarations.py
  - kg_build_system/distribution/languages/data/service/_private/descriptors.py
  - tests/test_authoring_api.py
---

## Surface

Declarations state the shape of one row, the shape of a nested record, the contract of a relation and the asset those rows come from. The declaration set is `SourceRelation`, `Struct`, `ComputedStruct`, `DerivedRelation`, `Stage`, `SourceRelationGroup` and `StructTemplate`; `field()` and `computed_field()` are the only member constructors.

A relation states a contract: a `Definition` (grain and identity) and, when the relation is published with a meaning, a `Meaning` (purpose, claims and limitations) bundled as `Contract`. A `DerivedRelation` always states one and its meaning must carry a purpose. A `SourceRelation` reads its rows from one asset and may omit the contract, because the asset and its field definitions already state what the source contains; a source relation read by a binding should declare one. A `Stage` is the private sub-relation inside a derived relation: it carries a `Definition` only, is never a consumer relation and is never bindable.

Read [Declare data](/book/part-2/03-source-and-rows) for the authoring path, [Data specification](/appendix/spec/data) for the relation contract, [Types reference](/appendix/reference/types) for value types, and [Row sources](/appendix/reference/row-sources) for the algebra that turns a declaration into rows. The asset model is on [Declare an asset](/book/part-2/03-source-and-rows) and [Asset specification](/appendix/spec/asset).

## Details

The declaration names come from `kg_build_system`; the representative and canonical types come from `kg_build_system`. Selections are on [Expressions and selections](/appendix/reference/expressions), row plans on [Row sources](/appendix/reference/row-sources), and named relations on [Derived relations](/appendix/reference/derived-relations).

**The declaration set**

| Declaration | What it declares | Row source | Names an asset | Contract |
| --- | --- | --- | --- | --- |
| `SourceRelation` | A final row shape read from one asset | Yes, through `row_source()` | Yes, `SourceRelation[Asset]` | Optional `Definition` + `Meaning` |
| `Struct` | A nested record used as a field type | No | No | None |
| `ComputedStruct` | A value record whose members are type witnesses | No | No | None |
| `DerivedRelation` | A consumer relation computed from one row source | Yes, through `row_source()` | No | Required `Definition` + `Meaning` with a purpose |
| `Stage` | A private sub-relation inside one derived relation | `StageRowSource`, only inside its package | No | `Definition` only |
| `SourceRelationGroup` | A named catalog of final source relations and nested groups | No | Through its members | None |
| `StructTemplate` | A mixin sharing fields and annotations | No | No | None |

`SourceRelation`, `SourceRelationGroup` and `DerivedRelation` are final: a final declaration may not inherit from another final declaration of the same kind. `Struct` and `ComputedStruct` are composable value records and have no finality guard. `Stage` is final and package-private.

**`FieldDefinition`**

```python
FieldDefinition(
    value: str,
    unit: str | None = None,
    null_meaning: str | None = None,
)
```

A field definition states what the value means, the unit it is expressed in and what an absent value means. It is attached to a member constructor, never to a `Field` object directly.

| Field | Meaning | Required |
| --- | --- | --- |
| `value` | What the value states, in domain words | Yes; non-empty |
| `unit` | The unit the value is expressed in, or `None` when the value is a count or a label | No |
| `null_meaning` | What an absent value states, or `None` when the field is never absent | No |

A definition does not repeat facts the declaration already carries. The attribute names the field, the annotation names the logical type, and the asset and row plan carry provenance; none of them is a definition field. `unit` is a domain unit such as `metre` or `case`, not a canonical type.

**`field()`**

```python
def field[T: DeclaredValue] (
    *,
    definition: FieldDefinition | None = None,
    name: str | None = None,
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> Field[T]: ...
```

`field()` declares a source-backed member: a `SourceRelation` column or a source `Struct` member. The type argument is written in the annotation, as `Field[T] = field()`.

| Parameter | Type | Meaning | Default |
| --- | --- | --- | --- |
| `definition` | `FieldDefinition or None` | What the value, its unit and its absence mean | `None`; state it wherever the name and type cannot answer |
| `name` | `str or None` | External field name seen by selections and the source | Snake case of the attribute; one trailing `_` is removed |
| `description` | `str or None` | Member description | The string written directly below the assignment |
| `annotations` | `Sequence[Annotation]` | Portable metadata carried by the field | `()` |

Returns a `Field[T]` descriptor. Do not construct `Field` directly; the two constructors decide the backing kind. A field definition is optional: state it wherever the name and the type cannot answer what the value means, especially on a relation a binding reads. A `Struct` member may omit it.

```python
from kg_build_system import (
    Field, FieldDefinition, SourceRelation, SourceRelationOptions,
    Timestamp, field,
)

from estate.assets import Estate


class VisitSourceRelation(SourceRelation[Estate]):
    """One inspection visit."""

    options = SourceRelationOptions(name="visit")
    visit_id: Field[str] = field(
        definition=FieldDefinition(
            value="the inspection visit's stable identifier",
            null_meaning="the source holds no identifier for the visit",
        ),
    )
    inspected_on: Field[Timestamp] = field(
        definition=FieldDefinition(
            value="the instant the inspection was recorded",
            unit="timestamp",
            null_meaning="the source does not record an inspection instant",
        ),
    )
    display_name: Field[str] = field(
        name="name",
        definition=FieldDefinition(value="the visit's display label"),
    )
```

`Field[T]` accepts the eight canonical scalar types, `Array[...]` of a supported type, a declared `Struct` or `ComputedStruct`, and a declared `CustomDataType`. A field type must be one of those value types; `Field[SomeSourceRelation]` and `Field[SomeDerivedRelation]` are not legal. The full type table is on [Types reference](/appendix/reference/types).

A source `Field[T]` read yields `Selection[Nullable[T]]`. The declaration names the value type; the source owner decides presence.

| Error | Trigger |
| --- | --- |
| `field names must be non-empty` | `field(name="")` |
| `field definitions must state what the value means` | `FieldDefinition(value="")` |
| `<Class>.<attribute> must have a Field[T] annotation` | The attribute has no `Field[T]` annotation |
| `<Class>.<attribute> is a source field and must be declared with field(), not computed_field()` | `computed_field(...)` used in a `SourceRelation` or `Struct` |
| `<Class>.<attribute> must be declared with computed_field()` | `field()` used in a `DerivedRelation`, `Stage` or `ComputedStruct` |
| `<Class> fields 'x' and 'y' share external name 'name'` | Two members resolve to the same external name |
| `one Field instance may not be assigned to multiple declarations` | The same `Field` object is assigned twice |
| `<Name> is a row source, not a value record; field types must be Struct or ComputedStruct declarations` | `Field[SomeSourceRelation]` or `Field[SomeDerivedRelation]` |
| `logical types must be explicit; Any is not supported` | `Field[Any]` |
| `<Class>.<attribute> is a source field and must be declared with field(), not T \| None` | The annotation includes absence |
| `unsupported logical type annotation: ...` | `list[T]`, `dict[K, V]` or another unsupported annotation |

**`computed_field()`**

```python
def computed_field[T: DeclaredValue] (
    value: Selection[T],
    *,
    definition: FieldDefinition | None = None,
    name: str | None = None,
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> Field[T]: ...
```

`computed_field()` declares a selection-backed member. It is legal on a `DerivedRelation` output, a `Stage` output and a `ComputedStruct` member; the host decides what the selection means.

| Parameter | Type | Meaning | Default |
| --- | --- | --- | --- |
| `value` | `Selection[T]` | A selection that types the output | Required |
| `definition` | `FieldDefinition or None` | What the output, its unit and its absence mean | `None`; state it wherever the name and type cannot answer |
| `name` | `str or None` | External output name | Snake case of the attribute; one trailing `_` is removed |
| `description` | `str or None` | Output description | The string written directly below the assignment |
| `annotations` | `Sequence[Annotation]` | Portable metadata carried by the output | `()` |

Returns a `Field[T]` descriptor. On a `DerivedRelation` or `Stage`, the field is an output typed by `value`; on a `ComputedStruct`, the field is a type witness. A field definition is optional and states the output's value, unit and null meaning; the relation contract never copies field definitions.

```python
from kg_build_system import (
    ComputedStruct, DerivedRelation, FieldDefinition, computed_field,
)


class SiteDerivedRelation(DerivedRelation(SiteSourceRelation.row_source())):
    site_id = computed_field(
        SiteSourceRelation.site_id.alter_rows().drop_null(),
        definition=FieldDefinition(value="the site's stable identifier"),
    )
    label = computed_field(
        SiteSourceRelation.name.alter_rows().drop_null().prepend("site::"),
        definition=FieldDefinition(value="the site's display label"),
    )


class SiteSummaryStruct(ComputedStruct):
    """The member types a summary record carries."""

    site_id = computed_field(SiteSourceRelation.site_id.alter_rows().drop_null())
    region = computed_field(SiteSourceRelation.region)
```

| Error | Trigger |
| --- | --- |
| `computed field names must be non-empty` | `computed_field(..., name="")` |
| `<Class>.<attribute> must be declared with computed_field()` | `field()` used in a `DerivedRelation`, `Stage` or `ComputedStruct` |
| `<Class>.<attribute> is a source field and must be declared with field(), not computed_field()` | `computed_field(...)` used in a `SourceRelation` or `Struct` |
| `<Class> fields 'x' and 'y' share external name 'name'` | Two outputs or members resolve to the same external name |

**`Field[T]`**

`Field[T]` is the member descriptor. The annotation names the value type; the constructor names the backing and carries the definition.

| Host | Declaration | Read result |
| --- | --- | --- |
| `SourceRelation` or source `Struct` | `Field[T]` | `Selection[Nullable[T]]` |
| `DerivedRelation` or `Stage` | `computed_field(selection)` | Selection typed by the field's selection |
| `ComputedStruct` | `computed_field(selection)` | Read only through `extract`; the witness type composed with the carrier's presence |

A field annotation never includes absence. Source access is nullable because the source may omit the value; array item and nested value nullability stay in the value type, as in `Field[Array[Nullable[str]]]`. See [Types reference](/appendix/reference/types).

**`Contract`**

```python
Contract(
    definition: Definition,
    meaning: Meaning,
)
```

A `Contract` is the whole statement a relation makes about itself. It has two parts and no third:

| Part | States | Required |
| --- | --- | --- |
| `Definition` | Grain and identity | Yes |
| `Meaning` | Purpose, claims and limitations | Yes; at least one unit, and a purpose on a `DerivedRelation` |

A `DerivedRelation` requires a contract, because it offers a relation to consumers. A `SourceRelation` may omit one: the asset and its field definitions state what the source contains. When a source relation declares a contract it is complete, like any other contract. When a binding reads a source relation directly, declare the contract so the binding has a grain and identity to check; the audit reports a source relation read by a binding that declares none.

```python
from kg_build_system import Claim, Contract, Definition, Meaning, Purpose

contract = Contract(
    definition=Definition(
        grain="one row per site",
        identity=("site_id",),
    ),
    meaning=Meaning(
        purpose=Purpose(
            "Name each site once for the graph.",
            limitations=(
                "A site the register does not hold is absent.",
            ),
        ),
        claims=(Claim("A site identifier is stable across releases."),),
    ),
)
```

**`Definition`**

```python
Definition(
    grain: str,
    identity: tuple[str, ...],
)
```

`Definition` states what one row is and what identifies it. `grain` is non-empty; `identity` is a non-empty ordered tuple of output names. A single-output identity is a one-element tuple.

| Field | Meaning |
| --- | --- |
| `grain` | What one row states, in relation words |
| `identity` | The ordered tuple of output names that identifies one row |

Every name in `identity` must be an output of the relation, and the check runs when the class is created. The identity is a language reference in the model, not a copied field. Every identity is a tuple, and its order is part of the statement.

A definition is not a meaning. It states the row, not the use: a purpose, a claim or a limitation belongs in `Meaning`.

**`Meaning`**

`Meaning` is the one meaning value a declaration attaches. It carries an optional `Purpose` owning its `Limitation` values and any number of contextless `Claim` values. The graph declaration requires a purpose; a `DerivedRelation` contract requires a purpose; a `SourceRelation` meaning and a `Struct` meaning MAY carry claims only; a binding meaning MUST carry a purpose. See [Meaning specification](/appendix/spec/meaning).

**`SourceRelation`**

```python
class SourceRelation[AssetT: Asset]:
    options: SourceRelationOptions
    # field members

    @classmethod
    def row_source(cls) -> RelationRowSource[Self]: ...
```

A `SourceRelation` is a typed shape, a row source provider, an optional contract and the name of the asset its rows come from. It is final and becomes a reached relation when a [binding](/appendix/reference/bindings) or [derived relation](/appendix/reference/derived-relations) reads it.

```python
from estate.assets import Estate

class SiteSourceRelation(SourceRelation[Estate]):
    options = SourceRelationOptions(
        contract=Contract(
            definition=Definition(grain="one row per site", identity=("site_code",)),
            meaning=Meaning(
                claims=(Claim("One row names one estate site."),),
            ),
        ),
    )
    site_id: Field[str] = field(
        definition=FieldDefinition(value="the site's stable identifier"),
    )
```

The asset parameter is part of the declaration. A concrete source relation without one is refused when the class is created. A source relation is record-agnostic: its contract, when declared, names the domain, not a node, edge, property or build key.

| Member | Returns | Use |
| --- | --- | --- |
| `options` | `SourceRelationOptions` | Identity, description, annotations and the optional contract |
| `row_source()` | `RelationRowSource[Self]` | Start the row-source algebra |

The name defaults to the class name with one `SourceRelation` suffix removed and converted to snake case, so `VisitSourceRelation` becomes `visit`. `description` defaults to the class's own docstring; `options.description` wins. Description is not inherited.

```python
from kg_build_system import (
    Claim, Contract, Definition, Field, FieldDefinition, Meaning,
    SourceRelation, SourceRelationOptions, field,
)

from estate.assets import Estate


class SiteSourceRelation(SourceRelation[Estate]):
    """One site in the estate."""

    options = SourceRelationOptions(
        name="sites",
        contract=Contract(
            definition=Definition(grain="one row per site", identity=("site_id",)),
            meaning=Meaning(claims=(Claim("One row names one estate site."),)),
        ),
    )
    site_id: Field[str] = field(
        definition=FieldDefinition(value="the site's stable identifier"),
    )
    name: Field[str] = field(
        definition=FieldDefinition(value="the site's display name"),
    )
    region: Field[str] = field(
        definition=FieldDefinition(value="the region the site belongs to"),
    )
```

`SiteSourceRelation.site_id` is a `Selection[Nullable[str]]` because source access is nullable; `SiteSourceRelation.row_source()` is the relation a binding reads. See [Row sources](/appendix/reference/row-sources) for the algebra and [Bindings](/appendix/reference/bindings) for fulfilment.

| Error | Trigger |
| --- | --- |
| `a final SourceRelation may not inherit from another final SourceRelation` | A `SourceRelation` subclass inherits another final `SourceRelation` |
| `X is a concrete SourceRelation without an asset; declare it as SourceRelation[Asset]` | A concrete source relation names no asset |
| `X must name an Asset subclass: SourceRelation[Asset]` | The parameter is not an `Asset` subclass |
| `SourceRelation.options must be a SourceRelationOptions value` | `options` is not a `SourceRelationOptions` |
| `a declared contract requires a Definition and a Meaning` | A `Contract` value is incomplete |
| `<Class> is a SourceRelation declaration: declare SourceRelationOptions, not template options` | `options = StructOptionsTemplate(...)` on a source relation |
| `source relation names must be non-empty` | `SourceRelationOptions(name="")` |

**`Struct`**

```python
class Struct:
    options: StructOptions
    # field members
```

A `Struct` is a nested-record shape. It is used as `Field[SomeStruct]`, never as a row source, group member or relation declaration. Its identity is the `(module, qualname)` pair, so two structs with the same name in different modules are distinct.

```python
from kg_build_system import Field, Struct, StructOptions, field


class ContactStruct(Struct):
    """A contact record inside a site row."""

    options = StructOptions(name="contact")
    email: Field[str] = field()
    phone: Field[str] = field()
```

A source struct member read yields `Selection[Nullable[T]]`; a nullable carrier also makes every member nullable. Reach members with `extract`; see [Expressions and selections](/appendix/reference/expressions#extract). A struct has no contract and no grain: it is a value shape, not a relation.

| Error | Trigger |
| --- | --- |
| `Struct.options must be a StructOptions value` | `options` is not a `StructOptions` |
| `struct names must be non-empty` | `StructOptions(name="")` |
| `<Class> is a Struct declaration: declare StructOptions, not template options` | `options = StructOptionsTemplate(...)` on a struct |

**`ComputedStruct`**

```python
class ComputedStruct:
    options: StructOptions
    # computed_field members
```

A `ComputedStruct` is a value-record declaration built from `computed_field` members. It is usable as `Field[SomeComputedStruct]` and through `extract`, but it has no `row_source()`, cannot be bound and cannot be a group member.

As a field type its member selections are **type witnesses**: they fix each member's logical type, are not evaluated, and do not add a row plan. The carrier record supplies the value. A present carrier leaves a present witness present; a nullable carrier makes the member nullable.

```python
from kg_build_system import (
    ComputedStruct, Field, SourceRelation, SourceRelationOptions, computed_field,
    field,
)

from estate.assets import Estate


class SiteSummaryStruct(ComputedStruct):
    site_id = computed_field(SiteSourceRelation.site_id.alter_rows().drop_null())
    region = computed_field(SiteSourceRelation.region.alter_rows().drop_null())


class SummarySourceRelation(SourceRelation[Estate]):
    options = SourceRelationOptions(
        contract=Contract(
            definition=Definition(grain="one row per site", identity=("site_id",)),
            meaning=Meaning(claims=(Claim("One summary row names one site."),)),
        ),
    )
    site_id: Field[str] = field(
        definition=FieldDefinition(value="the site's stable identifier"),
    )
    summary: Field[SiteSummaryStruct] = field(
        definition=FieldDefinition(value="the site's summary", unit=None),
    )
```

| Error | Trigger |
| --- | --- |
| `ComputedStruct.options must be a StructOptions value` | `options` is not a `StructOptions` |
| `struct names must be non-empty` | `StructOptions(name="")` |
| `<Class>.<attribute> must be declared with computed_field()` | A `field()` member is declared on a computed struct |
| `<Class> is a ComputedStruct declaration: declare StructOptions, not template options` | Template options are used as the host options |

**`DerivedRelation`**

```text
DerivedRelation(source: RowSource[S]) -> type[DerivedRelation]
```

`DerivedRelation(source)` returns a base pinned to one row source. Subclass it, give the class a contract whose meaning states a purpose, and declare at least one output with `computed_field`. A derived relation is a shape, a row source and a consumer contract; it is not a `SourceRelation` and names no asset of its own.

There is no unpinned derived relation. `DerivedRelation()` and `class R(DerivedRelation)` are refused when the class is created.

```python
from kg_build_system import (
    Claim, Contract, Definition, DerivedRelation, DerivedRelationOptions,
    FieldDefinition, Meaning, Purpose, computed_field,
)


class SiteDerivedRelation(DerivedRelation(SiteSourceRelation.row_source())):
    options = DerivedRelationOptions(
        name="site_label",
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
    )
    label = computed_field(
        SiteSourceRelation.name.alter_rows().drop_null().prepend("site::"),
        definition=FieldDefinition(value="the site's display label"),
    )
```

| Error | Trigger |
| --- | --- |
| `requires a row source` | `DerivedRelation()` is called without a source, or a class is declared without one |
| `derived relations must declare at least one computed_field` | The derived relation has no output |
| `a final DerivedRelation may not inherit from another final DerivedRelation` | A final derived relation inherits another final derived relation |
| `derived relation names must be non-empty` | `DerivedRelationOptions(name="")` |
| `a derived relation requires a Contract with a Definition and a Meaning` | `options.contract` is absent or incomplete |
| `a derived relation contract requires a purpose` | The contract's `Meaning` carries claims only |
| `<Class>.<attribute> must be declared with computed_field()` | `field()` is used for an output |

The pin, outputs, dependencies and the record-agnostic rule are on [Derived relations](/appendix/reference/derived-relations) and [Row sources](/appendix/reference/row-sources).

**`Stage`**

```text
Stage(source: RowSource[S]) -> type[Stage]
```

A `Stage` is a private sub-relation that an author writes to keep one step of a derived relation reviewable. It pins one row source and publishes outputs with `computed_field`, exactly like a derived relation, but it is not a declaration a consumer may depend on:

| Property | Stage | DerivedRelation |
| --- | --- | --- |
| Consumer relation | No | Yes |
| Stored in `data.derived_relations` | Yes, with `visibility="internal"` | Yes, with `visibility="public"` |
| Bindable | No; `StageRowSource` | Yes; `RelationRowSource` |
| Carries a `Meaning` | No | Yes, with a purpose |
| Carries a `Definition` | Yes | Yes |
| Read from outside its package | No | Yes |
| Visible in the viewer | No | Yes |

A stage lives in `_<stage>.py` beside the `relation.py` of its derived relation. A structure test refuses an import of a stage from another package, so a stage is private by construction, not by review. The stage remains in `data.derived_relations` only because its public parent's row plan scans it; it is not a consumer relation.

```python
# relation/derived/defect_relation/_stage_cause.py
from kg_build_system import (
    Definition, FieldDefinition, Stage, StageOptions, computed_field,
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
    )
    cause_id = computed_field(
        DefectSourceRelation.cause_id.alter_rows().drop_null(),
        definition=FieldDefinition(value="the cause's stable identifier"),
    )
```

The derived relation then pins the stage's row source and states the contract the consumer reads:

```python
# relation/derived/defect_relation/relation.py
from kg_build_system import (
    Claim, Contract, Definition, DerivedRelation, DerivedRelationOptions,
    FieldDefinition, Meaning, computed_field,
)

from ._stage_cause import DefectCauseStage


class DefectDerivedRelation(DerivedRelation(DefectCauseStage.row_source())):
    options = DerivedRelationOptions(
        name="defect",
        contract=Contract(
            definition=Definition(
                grain="one row per defect",
                identity=("defect_id",),
            ),
            meaning=Meaning(
                purpose=Purpose("Read the defects a survey reported."),
                claims=(Claim("One row names one defect."),),
            ),
        ),
    )
    defect_id = computed_field(
        DefectCauseStage.defect_id,
        definition=FieldDefinition(value="the defect's stable identifier"),
    )
```

A stage has no meaning and no contract: it is a definition and a row plan, not a promise to a consumer. Do not write a purpose, claim or limitation on a stage; state the relation's meaning on the `DerivedRelation` that reads it. A binding refuses a `StageRowSource`.

**`SourceRelationGroup`**

```python
class SourceRelationGroup:
    options: SourceRelationGroupOptions
    # member attributes, or options.members
```

A `SourceRelationGroup` is a final named catalog of final source relations and nested groups. It is not a shape and not a row source. Members may be class attributes or the `members` argument of `SourceRelationGroupOptions`.

```python
from kg_build_system import SourceRelationGroup, SourceRelationGroupOptions


class ReadingsSourceRelationGroup(SourceRelationGroup):
    """One relation per logger family."""

    options = SourceRelationGroupOptions(name="readings")
    temperature = TemperatureSourceRelation
    mechanical = MechanicalSourceRelationGroup
```

The group name defaults to the class name with one `SourceRelationGroup` suffix removed and converted to snake case. A group is a catalog, not a source declaration: each member relation names its own asset and contract. See [Asset specification](/appendix/spec/asset).

| Error | Trigger |
| --- | --- |
| `source relation groups must declare at least one member` | The group has no source relation or group member |
| `source relation groups may contain only final SourceRelation or SourceRelationGroup declarations` | A member is not a final source relation or group |
| `a final SourceRelationGroup may not inherit from another final SourceRelationGroup` | A group inherits another final group |
| `source relation groups may not contain a cycle` | A group contains itself, directly or through nested groups |
| `a source relation group may include a final source relation only once` | The same source relation is reached through two catalog paths |
| `a source relation group has duplicate catalog paths` | Two members resolve to the same catalog path |
| `SourceRelationGroup.options must be a SourceRelationGroupOptions value` | `options` is not a `SourceRelationGroupOptions` |
| `source relation group names must be non-empty` | `SourceRelationGroupOptions(name="")` |
| `<Class> is a SourceRelationGroup declaration: declare SourceRelationGroupOptions, not template options` | `options = StructOptionsTemplate(...)` on a group |

**`StructTemplate`**

```python
class StructTemplate:
    options: StructOptionsTemplate
    # field members
```

`StructTemplate` shares field slots and annotation flow with `SourceRelation`, `Struct` and `ComputedStruct`. It never becomes a declaration, has no name, contract or description and never enters the blueprint. Templates come first in the base list: `class SiteSourceRelation(ProvenancedTemplate, SourceRelation[Estate])`.

A template's options must be `StructOptionsTemplate`, which carries annotations only. A template may extend another template by naming it as its base. Mixing a template into `DerivedRelation`, `Stage` or `SourceRelationGroup` is refused. A `ComputedStruct` host accepts a template's annotations, but a source-backed template field fails there because a computed host requires `computed_field`.

```python
from kg_build_system import (
    Field, SourceRelation, SourceRelationOptions, StructOptionsTemplate,
    StructTemplate, field,
)


class ProvenancedTemplate(StructTemplate):
    options = StructOptionsTemplate()
    source_version: Field[str] = field()


class SiteSourceRelation(ProvenancedTemplate, SourceRelation[Estate]):
    options = SourceRelationOptions(...)
    site_id: Field[str] = field()
```

| Error | Trigger |
| --- | --- |
| `<Class> is a data template: its options must be StructOptionsTemplate, which carries no name or description — wrap it: ...` | A template uses `SourceRelationOptions` or `StructOptions` |
| `<Class> mixes StructTemplate into a non-record declaration: ...` | A template is mixed into `DerivedRelation`, `Stage` or `SourceRelationGroup` |
| `<Class>.<attribute> must be declared with computed_field()` | A source-backed template field reaches a `ComputedStruct` host |

**Options**

| Option value | Signature | Fields |
| --- | --- | --- |
| `SourceRelationOptions` | `SourceRelationOptions(name=None, description=None, annotations=(), contract=None)` | Identity, description, annotations and an optional contract |
| `StructOptions` | `StructOptions(name=None, description=None, annotations=(), meaning=None)` | Struct or computed-struct identity, description, annotations and optional meaning |
| `DerivedRelationOptions` | `DerivedRelationOptions(contract=..., name=None, description=None, annotations=())` | The required relation contract plus identity, description and annotations |
| `StageOptions` | `StageOptions(definition=..., name=None, description=None, annotations=())` | The required stage definition plus identity, description and annotations; no meaning |
| `SourceRelationGroupOptions` | `SourceRelationGroupOptions(members=(), name=None, description=None, annotations=())` | Group members plus identity, description and annotations; no contract |
| `StructOptionsTemplate` | `StructOptionsTemplate(annotations=())` | Template annotations only; no name or description |

Every option value is frozen. `name` must be non-empty when supplied. `description` defaults to the declaration's own docstring and is never inherited. `annotations` is a sequence of `Annotation` values; see [Data specification](/appendix/spec/data).

A derived relation option requires a contract; a source relation option may omit it. Neither takes a bare `meaning`: grain and identity are part of what a derived relation promises. A `Struct` is not a relation and keeps the optional `meaning` it attaches as a declaration.

**What to remember**

- A relation states a `Definition` (grain and identity) and, for a `DerivedRelation`, a `Meaning` with a purpose, bundled as `Contract`.
- `field(definition=...)` declares source backing; `computed_field(selection, definition=...)` declares selection backing. A `FieldDefinition` is optional and never repeats the name, type or source.
- A `FieldDefinition` states what the value, its unit and its absence mean. It never repeats the field name, the logical type or the source.
- `Field[T]` names a value type. Source `SourceRelation` and `Struct` reads are `Selection[Nullable[T]]`; derived-relation, stage and computed-struct reads follow their selection.
- `SourceRelation`, `SourceRelationGroup` and `DerivedRelation` are final. `Struct` and `ComputedStruct` are value records, not row sources. `Stage` is final and private to its package.
- `SourceRelation[Asset]` names the logical source of a relation; the asset and its optional layout carry location, format and credential reference.
- A `DerivedRelation` is always pinned to one row-source value; a `Stage` is a private step inside one derived relation and returns a non-bindable `StageRowSource`.
- A published relation is record-agnostic: its definition and meaning name the domain, never a node, edge, property or build key.

For the step that turns declarations into a plan, see [Compile](/appendix/reference/compile). For the data subject as a whole, start at [Data contracts](/appendix/subjects/data).
