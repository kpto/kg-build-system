---
title: The relation contract
summary: The authoring and DTO interface for a relation's definition, meaning and field definitions, and the rule that separates a published relation from a stage.
section: developer
perspective: developer
order: 46
status: normative
verified: 2026-11-15
sources:
  - kg_build_system/distribution/languages/data/model/public/declarations.py
  - kg_build_system/distribution/languages/data/model/public/fields.py
  - kg_build_system/distribution/languages/data/model/internal/dto/blueprint_dto.py
  - kg_build_system/distribution/languages/meaning/model/public/units.py
  - kg_build_system/distribution/languages/binding/service/public/builders.py
---

## Interface

A relation is a **contract**: a definition of what one row is and a meaning of
what the relation is for. The data language owns the authoring types and the
DTOs; the meaning language owns the value both axes share; the binding language
decides which row sources it accepts.

| Name | Zone | Contract |
| --- | --- | --- |
| `SourceRelation[AssetT]` | `data/model/public/declarations.py` | An asset-backed relation. Outputs are `field(...)`. |
| `DerivedRelation(source)` | same | A computed relation pinned to one row source. Outputs are `computed_field(...)`. |
| `Stage(source)` | same | A private computed relation. Outputs are `computed_field(...)`. No meaning member. |
| `SourceRelationOptions`, `DerivedRelationOptions`, `StageOptions` | same | Name, annotations and the contract or definition. A derived relation requires `contract`; a source relation states `contract=Omitted` when it has none; a stage requires `definition`. |
| `SourceRelationGroup`, `SourceRelationGroupOptions` | same | A catalogue of source relations. |
| `Contract(definition, meaning)` | `data/model/public/contract.py` | The relation's promise: `Definition` + `Meaning`. |
| `Definition(grain, identity)` | same | Grain as authored text; identity as output names. |
| `FieldDefinition(value, unit, null_meaning)` | `data/model/public/fields.py` | One field's value meaning, scale and null meaning. |
| `Meaning`, `Purpose`, `Claim`, `Limitation` | `meaning/model/public/units.py` | The shared value on both axes. |

## Authoring

```python
from kg_build_system import (
    Claim, Contract, Definition, DerivedRelation, DerivedRelationOptions,
    FieldDefinition, Limitation, Meaning, Omitted, Purpose, SourceRelation,
    SourceRelationOptions, Stage, StageOptions, computed_field, field,
)


class Target(SourceRelation[OpenTargets]):
    options = SourceRelationOptions(
        name="target",
        contract=Contract(
            definition=Definition(
                grain="one row per target in the release",
                identity=("target_id",),
            ),
            meaning=Meaning(
                claims=(Claim("The release's canonical target record."),),
            ),
        ),
    )

    target_id: Field[str] = field(
        definition=FieldDefinition(value="Ensembl gene accession."),
        meaning=Omitted,
    )
    symbol: Field[str] = field(
        definition=FieldDefinition(
            value="HGNC approved symbol.",
            null_meaning="The release carries no symbol for the gene.",
        ),
        meaning=Omitted,
    )


class TargetStage(Stage(raw_rows)):
    options = StageOptions(
        name="target_stage",
        definition=Definition(
            grain="one row per source assertion",
            identity=("source_row_id",),
        ),
    )

    source_row_id = computed_field(raw_rows.shape.row_id, meaning=Omitted)


class TargetAnnotation(DerivedRelation(TargetStage.row_source())):
    options = DerivedRelationOptions(
        name="target_annotation",
        contract=Contract(
            definition=Definition(
                grain="one row per annotated target",
                identity=("target_id",),
            ),
            meaning=Meaning(
                purpose=Purpose(
                    "Read the release's target annotations.",
                    limitations=(
                        Limitation("An annotation is not a disease association."),
                    ),
                ),
                claims=(Claim("One row is one target and its released annotation."),),
            ),
        ),
    )

    target_id = computed_field(TargetStage.target_id, meaning=Omitted)
```

## Rules

- **A contract has both halves.** `Contract` refuses a missing `definition` or a
  missing `meaning`. It refuses a `Meaning` with neither a purpose nor a claim,
  because `Meaning` already refuses that.
- **A derived relation requires a contract, and that contract states a
  purpose.** A derived relation is a contract offered to consumers. If no
  expected use can be stated, the relation is private: declare a `Stage`.
- **A source relation's contract is optional.** The asset and its field
  definitions already state what the source contains; a generated source
  relation must remain reproducible from its contract options. When a source
  relation is read directly by a binding, declare its contract so the binding has
  a grain and identity to check against; a source relation read by a binding
  that declares none is a review finding.
- **A declared contract is complete.** Whenever a source relation declares a
  `contract`, it has both halves like any other contract; an incomplete contract
  is refused, not partially accepted.
- **A stage has no contract.** `StageOptions` has no `meaning` member. Passing
  one is a type error, not a review finding.
- **A field definition belongs to the field.** `field(...)` and
  `computed_field(...)` accept `definition=`. The relation contract never lists
  field definitions; `Definition.identity` names outputs and does not copy them.
- **A field definition carries only what cannot be derived.** `value`, `unit` and
  `null_meaning`. Name, type, source and provenance are read from the
  declaration and the plan.
- **Identity names real outputs.** Every name in `Definition.identity` must be an
  output of the relation. Validation runs at class creation and refuses an
  unknown name.
- **A row source has a role.** `DerivedRelation.row_source()` and
  `SourceRelation.row_source()` return `RelationRowSource`, which is bindable.
  `Stage.row_source()` returns `StageRowSource`, which is not.
- **A binding reads only a published relation.** `node_binding` and
  `edge_binding` accept `RelationRowSource` or a derived value; a
  `StageRowSource` is refused at construction and by the type checker.
- **A relation is record-agnostic.** A published relation MUST NOT name a graph
  record's properties, build key, endpoint tokens or component class. A relation
  that does is a record-shaped stage; keep it private or move the decision to the
  graph side and the binding.

## DTO shape

The blueprint stores the contract as two fields; there is no `ContractDTO`.

| DTO | Fields added by this interface |
| --- | --- |
| `SourceRelationDTO` | `definition: DefinitionDTO`, `meaning: MeaningDTO \| None` |
| `DerivedRelationDTO` | `definition: DefinitionDTO`, `meaning: MeaningDTO \| None`, `visibility: "public" \| "internal"` |
| `ColumnDTO` | `definition: FieldDefinitionDTO \| None` |

- A stage is a `DerivedRelationDTO` with `visibility="internal"` and
  `meaning=None`. It remains in `data.derived_relations` because the public
  relation's row plan scans it.
- `DataPartDTO` carries `source_relations` and `derived_relations`; neither key
  is named `relations` or `projections`.
- A binding DTO stores a `RelationRef` to a published relation. The interpreter
  refuses a reference to a `DerivedRelationDTO` whose visibility is `internal`.

## Ownership

A stage has no owner field. The plan owns the relation: a stage's nearest public
parents are the derived relations whose row source scans it, and the stage's
`visibility` says it is not a consumer relation. A stage with no public parent is
unreachable and is reported as dead, the same way an unread source relation is.

## Next

[Data and expressions](/appendix/developer/data-and-expressions) — how the
contract DTOs cross the blueprint and planning boundary.
