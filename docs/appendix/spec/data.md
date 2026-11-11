---
title: Data specification
summary: A table MUST name its asset; every field MUST declare a value type, and the owner MUST supply presence.
section: spec
perspective: spec
subject: data
spec: SPEC-002
order: 20
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/distribution/languages/data/model/public/declarations.py
  - kg_build_system/distribution/languages/data/model/public/fields.py
  - kg_build_system/distribution/languages/data/model/public/row_sources.py
  - kg_build_system/distribution/languages/topology/model/public/values.py
  - docs/book/part-2/01-source-and-rows.md
evidence:
  - tests/test_authoring_api.py
  - tests/typecheck/authoring.py
  - tests/typecheck/authoring_negative.py
  - docs/appendix/reference/declarations.md
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Data contracts and types</span><a href="/appendix/subjects/data">Overview</a><a href="/book/part-2/01-source-and-rows">Guide</a><a href="/appendix/spec/data" class="active">Spec</a><a href="/appendix/reference/api">API</a><a href="/appendix/philosophy/meaning-first">Philosophy</a><a href="/appendix/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

## Requirement

- **R1.** A concrete table MUST be declared `Table[AssetT]` for an `Asset` subclass; a table without a logical asset or one that inherits another final `Table` MUST be refused.
- **R2.** A `Field[T]` MUST declare a value type and MUST NOT declare `T | None`; `Field[str | None]` MUST be a static type error.
- **R3.** A source `Table` or `Struct` field read MUST yield `Selection[Nullable[T]]`; the owner MUST supply absence and the annotation MUST NOT.
- **R4.** A `Projection` output declared with `computed_field(selection)` MUST read as the selection's type; a `ComputedStruct` member MUST use that selection as its witness and compose presence with its carrier.
- **R5.** A nested record MUST be declared `Struct` or `ComputedStruct`; a `Table` or `Projection` MUST NOT be a `Field` value type, and a relation MUST be read through `row_source()`.
- **R6.** `Field[Array[Nullable[T]]]` MUST be legal and MUST keep item nullability; `Field[Nullable[T]]` MUST be refused as a nullable owner.
- **R7.** A graph property MUST be a `GraphScalar` or a flat `Array[GraphScalar]` of non-null scalars; a struct, a nested array or `Array[Nullable[T]]` MUST NOT be a property value.
- **R8.** `TableGroup` MUST be a catalog of final tables or nested groups, MUST contain at least one member, and MUST NOT produce rows or act as a row source.
- **R9.** `StructTemplate.options` MUST be a `StructOptionsTemplate`, which carries annotations only; the template MUST mix only into `Table`, `Struct` or `ComputedStruct`, and it MUST NOT become a declaration or enter the blueprint.
- **R10.** `Table`, `Projection` and `TableGroup` MUST be terminal; a final declaration MUST NOT inherit another final declaration of the same kind.

## Evidence

| Evidence | Proves |
| --- | --- |
| `tests/test_authoring_api.py` | Source and computed read types, `Field[str \| None]` refusal, `extract` presence and row-effect shape. |
| `tests/typecheck/authoring.py` | Static reads for `Table`, `Struct`, `Projection` and `ComputedStruct`, including `Array[Nullable[str]]`. |
| `tests/typecheck/authoring_negative.py` | A nullable field annotation is a static type error and removed names are absent. |
| `docs/appendix/reference/declarations.md` | Finality, `TableGroup` catalog rules, `StructTemplate` rules and their refusal messages. |

## API

| Name | Meaning |
| --- | --- |
| `Table[AssetT]` | Final row shape read from one logical asset. |
| `Field[T]` | Declares one member's value type, never its absence. |
| `field()` | Constructor for a source-backed member. |
| `Struct` | Nested record used as a field type. |
| `ComputedStruct` | Value record whose members are computed witnesses. |
| `computed_field(selection)` | Constructor for a computed member or projection output. |
| `Projection` | Final named relation pinned to one row source. |
| `TableGroup` | Named catalog of final tables and nested groups. |
| `StructTemplate` | Annotations-and-fields mixin that never becomes a declaration. |

The facade groups and defining modules are listed in [API surface](/appendix/reference/api).

## Limits

- `Table` and `Projection` are not field value types; a relation is read through `row_source()`.
- `Any`, `list[T]`, `dict[K, V]`, tuples and unions of two real types are not logical types.
- A `Struct` or custom scalar must be a top-level importable class.
- Generated source always renders `Field[T]`; observed nullability is provenance, never an optional annotation.
- A computed field annotation is not a second schema; it follows its selection.
- A table group is a catalog, not a union, and each member table names its own asset.
- `Array[Nullable[T]]` must have its null items removed with `drop_null_items()` before a graph property uses it.
- The data language validates shape; the grain belongs to the row source.

## Rationale

Data declarations keep the row contract separate from the mapping, so every value has one type and one owner for absence. A single `Field[T]` spelling prevents a second nullable schema from drifting from the source, while `computed_field` makes every derived value traceable to a selection. The page applies [one purpose, read downward](/appendix/philosophy/semantic-hierarchy): data states how this implementation supplies a record, under the design rather than replacing it.

## Next

[Data subject](/appendix/subjects/data) — the hub for this subject.
