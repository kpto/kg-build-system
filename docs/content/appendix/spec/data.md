---
title: Data specification
summary: A source relation names its asset; a published relation states a contract; every field declares a type and a field definition.
section: spec
perspective: spec
subject: data
spec: SPEC-002
order: 20
status: normative
verified: 2026-11-15
sources:
  - kg_build_system/distribution/languages/data/model/public/declarations.py
  - kg_build_system/distribution/languages/data/model/public/fields.py
  - kg_build_system/distribution/languages/data/model/public/row_sources.py
  - kg_build_system/distribution/languages/topology/model/public/values.py
  - docs/content/book/part-2/03-source-and-rows.md
evidence:
  - tests/test_authoring_api.py
  - tests/typecheck/authoring.py
  - tests/typecheck/authoring_negative.py
  - tests/distribution/test_data_meaning.py
  - docs/content/appendix/reference/declarations.md
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Data contracts and types</span><a href="/appendix/subjects/data">Overview</a><a href="/book/part-2/03-source-and-rows">Guide</a><a href="/appendix/spec/data" class="active">Spec</a><a href="/appendix/reference/api">API</a><a href="/appendix/philosophy/meaning-first">Philosophy</a><a href="/appendix/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

## Requirement

- **R1.** A concrete source relation MUST be declared `SourceRelation[AssetT]` for an `Asset` subclass; a source relation without a logical asset or one that inherits another final `SourceRelation` MUST be refused.
- **R2.** A `Field[T]` MUST declare a value type and MUST NOT declare `T | None`; `Field[str | None]` MUST be a static type error.
- **R3.** A source `SourceRelation` or `Struct` field read MUST yield `Selection[Nullable[T]]`; the owner MUST supply absence and the annotation MUST NOT.
- **R4.** A `DerivedRelation` output declared with `computed_field(selection)` MUST read as the selection's type; a `ComputedStruct` member MUST use that selection as its witness and compose presence with its carrier.
- **R5.** A nested record MUST be declared `Struct` or `ComputedStruct`; a `SourceRelation` or `DerivedRelation` MUST NOT be a `Field` value type, and a relation MUST be read through `row_source()`.
- **R6.** `Field[Array[Nullable[T]]]` MUST be legal and MUST keep item nullability; `Field[Nullable[T]]` MUST be refused as a nullable owner.
- **R7.** A graph property MUST be a `GraphScalar` or a flat `Array[GraphScalar]` of non-null scalars; a struct, a nested array or `Array[Nullable[T]]` MUST NOT be a property value.
- **R8.** `SourceRelationGroup` MUST be a catalog of final source relations or nested groups, MUST contain at least one member, and MUST NOT produce rows or act as a row source.
- **R9.** `StructTemplate.options` MUST be a `StructOptionsTemplate`, which carries annotations only; the template MUST mix only into `SourceRelation`, `Struct` or `ComputedStruct`, and it MUST NOT become a declaration or enter the blueprint.
- **R10.** `SourceRelation`, `DerivedRelation` and `SourceRelationGroup` MUST be terminal; a final declaration MUST NOT inherit another final declaration of the same kind.
- **R11.** A `SourceRelation` MUST be the source-backed declaration, with `field(...)` members; a `DerivedRelation` MUST be the published derived declaration, with `computed_field(...)` outputs. A `Stage` MUST be a private computed relation with no public contract.
- **R12.** A `DerivedRelation` MUST carry a `Contract`: a `Definition` stating grain and identity, and a `Meaning` carrying a domain purpose, claims and limitations. A `SourceRelation` MAY declare a contract; when a binding reads it directly, it SHOULD declare one, and its absence is a review finding. A generated source relation is not hand-edited to add one; its contract is a review finding against the generation request. A relation purpose MUST NOT be written under the graph's root purpose.
- **R13.** A field definition MUST sit on the field it describes, through `field(...)` or `computed_field(...)`, and MUST NOT be listed on the relation contract. A `FieldDefinition` carries only `value`, `unit` and `null_meaning`; name, logical type, source and provenance MUST be derived, never restated.
- **R14.** A `Stage` MUST be private: it MUST carry a `Definition`, MUST NOT carry a contract `Meaning`, MUST be recorded with internal visibility, and MUST NOT be readable by a binding. `StageOptions` MUST have no meaning member.
- **R15.** A published relation MUST be record-agnostic: it MUST NOT name a graph record's properties, build key, endpoint tokens or component class. A relation that names a record MUST be a private `Stage`, or the decision MUST move to topology and the binding.
- **R16.** A `Definition` MUST state grain as authored text and identity as output names; every identity name MUST be a declared output of the relation.

## Evidence

| Evidence | Proves |
| --- | --- |
| `tests/test_authoring_api.py` | Source and computed read types, `Field[str \| None]` refusal, `extract` presence and row-effect shape. |
| `tests/typecheck/authoring.py` | Static reads for `SourceRelation`, `Struct`, `DerivedRelation` and `ComputedStruct`, including `Array[Nullable[str]]`. |
| `tests/typecheck/authoring_negative.py` | A nullable field annotation is a static type error and removed names are absent. |
| `tests/distribution/test_data_meaning.py` | A source relation, derived relation and field carry their meaning value into the DTO and rendered source. |
| `docs/content/appendix/reference/declarations.md` | Finality, group catalog rules, template rules and their refusal messages. |

The contract, field-definition and stage rows are normative before their release tests; they are reviewed by reading the interface in [The relation contract](/appendix/developer/relation-contract), not by a green run.

## API

| Name | Meaning |
| --- | --- |
| `SourceRelation[AssetT]` | Final source-backed row shape read from one logical asset. |
| `Field[T]` | Declares one member's value type, never its absence. |
| `field()` | Constructor for a source-backed member; it may carry a `FieldDefinition`. |
| `Struct` | Nested record used as a field type. |
| `ComputedStruct` | Value record whose members are computed witnesses. |
| `computed_field(selection)` | Constructor for a computed member or derived output; it may carry a `FieldDefinition`. |
| `DerivedRelation` | Published named relation pinned to one row source; it requires a contract. |
| `Stage` | Private computed relation with a definition and internal visibility. |
| `SourceRelationGroup` | Named catalog of final source relations and nested groups. |
| `StructTemplate` | Annotations-and-fields mixin that never becomes a declaration. |
| `SourceRelationOptions` / `DerivedRelationOptions` / `StageOptions` | Name, annotations, and the contract or definition; a source relation states `contract=Omitted` when it publishes no contract. |
| `Contract` | A published relation's `Definition` plus `Meaning`. |
| `Definition` | Grain as authored text and identity as output names. |
| `FieldDefinition` | One field's value, unit and null meaning. |

The facade groups and defining modules are listed in [API surface](/appendix/reference/api).

## Limits

- `SourceRelation` and `DerivedRelation` are not field value types; a relation is read through `row_source()`.
- `Any`, `list[T]`, `dict[K, V]`, tuples and unions of two real types are not logical types.
- A `Struct` or custom scalar must be a top-level importable class.
- Generated source always renders `Field[T]`; observed nullability is provenance, never an optional annotation.
- A computed field annotation is not a second schema; it follows its selection.
- A source relation group is a catalog, not a union, and each member relation names its own asset.
- `Array[Nullable[T]]` must have its null items removed with `drop_null_items()` before a graph property uses it.
- The data language validates shape; the grain belongs to the row source.
- A `FieldDefinition` describes one value; it does not change the read type, which stays owned by the source or the selection.
- A `Stage` is recorded with internal visibility under `derived_relations`; it is plan lineage, not a published relation, and no consumer may reference it.
- A source relation's contract is optional; a derived relation's contract is required. A binding that reads a source relation directly requires that relation's contract.
- A relation contract's identity is the relation's; a record key belongs to the binding.
- A relation stores no owner and no consumer list. Ownership is read from the plan, and provenance from the bindings that read it.

## Rationale

Data declarations keep the row contract separate from the mapping, so every value has one type and one owner for absence. A single `Field[T]` spelling prevents a second nullable schema from drifting from the source, while `computed_field` makes every derived value traceable to a selection. A published relation is also a contract: its grain, identity, purpose and limits are readable without the pipeline that computes it, and its record-agnostic shape is what lets a binding be a fulfilment rather than a copy.

## Next

[Data subject](/appendix/subjects/data) — the hub for this subject.
