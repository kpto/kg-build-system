# Table Layer Alignment to the Node/Edge Hierarchy Model — Deferred Spec

Status: design discussed, agreed in direction, **deferred** (not scheduled with
`feat/node-edge-polymorphism`). Companion to `NODE_EDGE_HIERARCHY_SPEC.md`;
folds into `KG_BUILD_SYSTEM_SPEC.md` when implemented. File/line references are
as of the design discussion.

## 1. Agreed vocabulary and model

- A **struct** is a data type composed of named values. This covers both a
  table's row shape and a struct column's shape — a table *is* a struct at the
  shape level.
- A struct declaration is **not a reuse mechanism**. Reuse of shared shape
  concerns (fields + annotations across declarations) is the template tier's
  exclusive job.
- A struct is **composable** (referenced as `Field[CityStruct]`) — that is its
  purpose — but not **inheritable**. Composition is value reuse; inheritance is
  identity reuse; only templates carry identity-free shape down a lineage.
- The engine already models this correctly: relational planning treats a table
  scan as a struct-typed record and struct access as traversals. The conflicts
  below are all at the authoring-guard boundary, never below it.

## 2. Current implementation conflicts

### C1 — `Struct` has no finality guard

`Table`, `Projection`, and `TableGroup` each reject an IR-visible ancestor
(`table/models.py:148, 220, 256`). `Struct` (`table/models.py:197`) has no
guard: `class Child(ParentStruct)` silently merges fields through
`declared_fields`' MRO walk. Inheritance-based struct reuse is open by
omission and is the only struct reuse mechanism currently reachable.

### C2 — no template mechanism exists for structs

`TableTemplate` is table-only; its hook rejects a `Struct` host with a
misleading message. "Use a template for reusability" is unsatisfiable for
struct types today.

### C3 — a `Table` class is accepted as a struct value type

`Table` derives from the `types.Struct` marker (`table/models.py:140`) and
normalization is a plain `issubclass(annotation, Struct)` check
(`types/normalization.py:54`). `Field[OrdersTable]` normalizes to a
`StructType`, and the blueprint struct closure resolves it by module/qualname
and reads `_fields` (`compile/compiler.py:249-262`). A source-bound table can
therefore be reused as a column type, double-registering its identity as both a
`StructIR` and a `TableIR`. That is shape-reuse-by-identity — exactly what the
model routes to templates.

### C4 — vocabulary

`Struct`'s docstring advertises it as "A reusable nested-record declaration".
Per §1, *reusable* must mean *composable*; as written it invites C1's usage.

### C5 — annotation flow is base-walk, not template-once (pre-existing)

`_inherited_annotations` (`table/models.py:115`) walks `cls.__bases__` and
merges each base's *effective* set. Diamonds double-count template annotations,
and an inherited IR-visible base's annotations flow into children. The
hierarchy spec's contract — template options in C3 order, each template exactly
once, then own `options.annotations` — fixes both.

## 3. Agreed decisions

1. **One template kind, one root.** `StructTemplate` serves both `Struct` and
   `Table` hosts (name confirmed pending; `RecordTemplate` is the neutral
   alternative). The topology `NodeTemplate`/`EdgeTemplate` kind pairing does
   **not** port to the data domain: table preparation and struct preparation
   differ only in terminality and source bindability, never in what a template
   contributes (fields + annotations).
2. **Options tiers follow the hierarchy spec §3.**
   `StructOptionsTemplate` is annotations-only; templates carry no identity
   syntax. Tier guards are bidirectional with redirects: template given real
   options, concrete given template options, un-wrapped sequence, and a
   `StructTemplate` mixed into a non-record kind (`Projection`/`TableGroup`)
   all raise at class creation.
3. **`TableTemplate` / `TableTemplateOptions` are withdrawn** in the same
   breaking batch as `GraphComponent` / `TableTemplateOptions`. Struct hosts
   gain mixins additively; table authors rename.
4. **Struct finality guard** (fixes C1): a declaration whose lineage contains
   another IR-visible `Struct` raises with a redirect to templates.
5. **Tables are not value types** (fixes C3). Preferred resolution: stop
   `Table` inheriting the `types.Struct` value-type marker and give it its own
   root, keeping the engine's existing explicit table branch
   (`table/fields.py` already checks `_table_owner` first). Fallback if that
   typing refactor is deferred: reject raw `Table` subclasses in
   `Field._logical_type` before normalization. "Tables are records" stays an
   engine fact; "tables are not value types" becomes an authoring identity
   rule.
6. **Annotation flow** (fixes C5): only template contributions flow — C3 order,
   each template exactly once, collected wherever it enters the lineage; every
   IR-visible class's own options stay on its own IR entry. Name and
   description remain own-only (already true). Label uniqueness is enforced
   against the effective set at class creation.
7. **Internal domain root + wording.** One internal data-domain root (mirroring
   `_TopologyDeclarationBase`; roots do not generalize across domains),
   framework-lineage MRO rule, and the "final" → "concrete" wording migration.

## 4. Deliberately not imported from the hierarchy spec

| Mechanism | Reason |
|---|---|
| `AbstractTable` / `AbstractStruct` category tier | No IR consumer. Tables are leaf contracts bound to one physical source; structs are value definitions. Nothing descends, nothing queries children of a category. State as a non-goal so nobody "aligns" it later. |
| Covariant/invariant endpoint parameters | Tables and structs never appear as type arguments to other declarations; nothing for variance to check. |
| `Endpoint` tokens / binding overloads | Identity-per-component is a graph concept; `bind_source` binds the concrete table directly. |
| `Projection` / `TableGroup` templates | Terminal bases with no sharing need today; add only when a consumer exists. |
| Schema-by-reference tables (a table referencing a struct schema instead of inlining fields) | Separate, larger IR change; stage deliberately, do not smuggle in via this alignment. |

## 5. What already agrees (no work needed)

- Relational planning/lowering: table-as-struct-record, struct access as
  traversals.
- `declared_fields` MRO merge with shadowing works for template lineage today
  (`EntityTable(EntityTableTemplate, Table)` in `tests/test_data_declarations.py`).
- The cooperative finalization pattern in `TableTemplate`
  (`table/models.py:172-175`) generalizes to a `Struct` host unchanged.
- `Field.__set_name__`'s multi-class guard does not block template sharing.
- Description/name own-only resolution is already correct, and the table layer
  never stamps `dataclass()`, so the hierarchy spec §6 `__doc__` pitfall does
  not apply (keep it that way; worth a comment).

## 6. Delivery notes

- Breaking (pre-1.0), same batch as the hierarchy withdrawal:
  `TableTemplate` → `StructTemplate`, `TableTemplateOptions` withdrawn →
  `StructOptionsTemplate` (annotations-only).
- No IR schema change beyond the hierarchy spec's own v3 bump; templates never
  entered the IR and nothing here adds an IR entry. Effective-annotation
  semantics change (C3-once) shifts fingerprints for affected blueprints only.
- Nothing in the repository depends on the conflicts: no generated contract,
  test, reference-project module, or demo subclasses a user-declared `Struct`.
  Guards are non-breaking today — add regression tests asserting that before
  anything depends on them (mirror the existing `ChildTable`/`ChildProjection`/
  `ChildGroup` guard tests; add a `Field[SomeTable]` rejection test).
- Runtime unit tests only. Unlike topology, nothing here lives in
  type-argument position, so no checker-side misuse matrix is needed.
