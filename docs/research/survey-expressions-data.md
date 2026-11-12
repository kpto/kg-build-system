# Survey: `expressions/**` and `data/**` (kg-build-system)

Scope: `kg_build_system/distribution/languages/expressions/**` and `kg_build_system/distribution/languages/data/**`, cross-checked against `docs/concepts/{expressions,data-contracts,projections,row-sources,types}.md` and `docs/reference/{expressions,declarations,projections,row-sources}.md`.

Method: read-only source survey, plus the layer's own tests (`tests/test_authoring_api.py`, `tests/typecheck/*`, `tests/distribution/test_data_semantics.py`, `tests/distribution/test_expression_operations.py`, `tests/distribution/test_blueprint_dto.py`, `tests/distribution/test_source_roundtrip.py`). No source file was modified or executed; behavior marked "code path indicates" is inferred from the code, not from a run.

Path convention below: all paths are relative to `/home/paul/Repos/kg-build-system`. "line" references are approximate ranges from the current tree.

---

## 1. File / package map

### 1.1 `expressions` package

| Path | Zone | Responsibility |
| --- | --- | --- |
| `.../expressions/__init__.py` | package facade | Exports `Selection`, `NullableSelection`, all four row-effect handles, `Pair`, `all_of`, `any_of`, `value_expression`. |
| `expressions/model/__init__.py` | model | Marker only. |
| `expressions/model/public/__init__.py` | model public | Re-exports the authoring classes; no logic. |
| `expressions/model/public/selection.py` | model public | The single authoring class `Selection[T]`, all value/navigation methods, `NullableSelection` alias. |
| `expressions/model/public/selections/effects.py` | model public | Gated one-shot row-effect handles: `RowEffects`, `NullableRowEffects`, `ArrayRowEffects`, `NullableArrayRowEffects`. |
| `expressions/model/public/selections/__init__.py` | model public | Re-export of selection/effects names. |
| `expressions/model/public/pair.py` | model public | `Pair[L, R]`, the value record produced by `zip`; type-level `left`/`right` members. |
| `expressions/model/public/values.py` | model public (internal-facing) | `ValueExpression[T]`, immutable compiler wrapper; explicitly "not part of the authoring facade". |
| `expressions/model/internal/__init__.py` | model internal | Re-exports expression nodes and DTOs. |
| `expressions/model/internal/model/__init__.py` | model internal | Re-exports frozen node classes and `SelectedMember`. |
| `expressions/model/internal/model/expression.py` | model internal | Frozen model: `ExpressionNode`, literal/field/lookup/operation/variable nodes, `Traversal`, `RowEffect`, `RowSemantics`, `Expression` alias. |
| `expressions/model/internal/model/selection.py` | model internal | `SelectedMember` metadata and `RowEffectHandle` one-shot guard. |
| `expressions/model/internal/dto/__init__.py` | model internal | Re-exports expression DTOs. |
| `expressions/model/internal/dto/blueprint_dto.py` | model internal | Expression blueprint DTOs: literal, variable, field reference, lookup, operation. |
| `expressions/service/__init__.py` | service | Marker only. |
| `expressions/service/public/__init__.py` | service public | Exports `value_expression`, `all_of`, `any_of`. |
| `expressions/service/public/expression.py` | service public | Authoring wrappers `value_expression()` and `literal()`; overloads infer scalar types. |
| `expressions/service/public/boolean.py` | service public | Authoring `all_of` / `any_of`; converts inputs to expressions, wraps results as selections. |
| `expressions/service/internal/__init__.py` | service internal | Composition point: operations, codec, construction, render, visitors, adapter. |
| `expressions/service/internal/adapters/kernel_language.py` | service internal adapter | `ExpressionsLanguage`: discovers operation specs, transcribes operation symbols, renders expression fragments. |
| `expressions/service/internal/build.py` | service internal | Thin delegation to `_private/build.py` (`field_reference`, `operation`, `lookup_expression`, `with_arguments`). |
| `expressions/service/internal/construction.py` | service internal | Thin delegation to `_private/factory.py` (`wrap_expression`, `value_expression`, `literal`). |
| `expressions/service/internal/selections.py` | service internal | Thin delegation to `_private/selections.py` (`select_expression`, `select_member`, `as_expression`). |
| `expressions/service/internal/boolean.py` | service internal | Thin delegation to `_private/boolean.py`. |
| `expressions/service/internal/functions.py` | service internal | Re-export of private helper functions (coercion, DTO, literals, semantics, symbols). |
| `expressions/service/internal/source.py` | service internal | Thin delegation to `_private/source.py` expression renderer. |
| `expressions/service/internal/visitors.py` | service internal | Visitor protocol and traversal delegation. |
| `expressions/service/internal/dto/codec.py` | service internal | Thin delegation to `_private/dto_codec.py`. |
| `expressions/service/internal/operations/__init__.py` | service internal | Re-exports `DEFAULT_OPERATIONS` and operation spec types. |
| `expressions/service/internal/operations/spec.py` | service internal | `ArgumentSpec`, `ParameterSpec`, `RowEffectSpec`, `OperationSpec`, `OperationRegistry`, arity/validation hooks. |
| `expressions/service/internal/operations/registry.py` | service internal | Composes the 25 built-in specs into `DEFAULT_OPERATIONS`; rejects duplicate names. |
| `expressions/service/internal/operations/{add,subtract,concat,append,equals,replace,to_string,before_separator,after_separator,array_at,array_slice,transform_items,drop_null_items,sort,distinct,join,coalesce,not_,and_,or_,struct_field,expand,drop_null,drop_if,zip}.py` | service internal | One `OperationSpec` per built-in operation; each declares arity, argument predicates, result type, parameters and row effect. |
| `expressions/service/_private/__init__.py` | service private | Marker/docstring for private mechanics. |
| `expressions/service/_private/apply.py` | service private | `apply_operation(name, ...)` looks up `DEFAULT_OPERATIONS` and applies the spec. |
| `expressions/service/_private/arrays.py` | service private | `transform_items` variable binding, `drop_null_items`, array-operation helper. |
| `expressions/service/_private/boolean.py` | service private | `all_of` / `any_of` left-fold over `and`/`or`; empty identities. |
| `expressions/service/_private/build.py` | service private | Canonical constructors for field refs, operations, lookups; row-semantics composition. |
| `expressions/service/_private/coercion.py` | service private | `expression_input(value, expected)` literal/expression normalization and exact type check. |
| `expressions/service/_private/dto.py` | service private | Authoring node -> `ExpressionDTO`; `field_reference_for`, `expression_references`, DTO walker. |
| `expressions/service/_private/dto_codec.py` | service private | Canonical JSON codec for expression DTOs. |
| `expressions/service/_private/factory.py` | service private | `wrap_expression` / `value_expression` wrappers over literal construction. |
| `expressions/service/_private/literals.py` | service private | Literal inference/validation/freezing; class-exact unit checks; canonical text for date/time/timestamp/uuid. |
| `expressions/service/_private/lookup.py` | service private | Authoring-time target resolution for `lookup`; builds `LookupExpression` with nullable array type. |
| `expressions/service/_private/numeric.py` | service private | Numeric binary helper (currently not used by `Selection.add/sub`, which call the spec directly). |
| `expressions/service/_private/operations.py` | service private | Spec application engine: arity, parameter defaults, coercion, type validation, result type, row semantics, scope resolution. |
| `expressions/service/_private/pair.py` | service private | Generated `Pair_<hash>` record classes and pair type identities. |
| `expressions/service/_private/predicates.py` | service private | Logical-type predicates used by operation specs (`is_unit`, `is_array`, `is_numeric`, etc.). |
| `expressions/service/_private/selections.py` | service private | Selection construction, `extract`, array/value algebra, text/number/boolean wiring, row-effect helpers. |
| `expressions/service/_private/semantics.py` | service private | `row_effects`, `row_semantics`, `compose_row_semantics`; expand-effect deduplication. |
| `expressions/service/_private/source.py` | service private | Expression DTO -> inline source text, using low-level `field_reference`/`operation`/`lookup_expression` constructors. |
| `expressions/service/_private/symbols.py` | service private | Operation references, `authoring_references`, operation symbol projection. |
| `expressions/service/_private/visitors.py` | service private | `visit_expression`, `walk_expression`, `rewrite_expression`. |

### 1.2 `data` package

| Path | Zone | Responsibility |
| --- | --- | --- |
| `.../data/__init__.py` | package facade | Exports declaration classes, options, `Field`, row-source values, `computed_field`, `field`, `projection_row_source`, `ShapeField`. |
| `data/model/__init__.py` | model | Marker only. |
| `data/model/public/__init__.py` | model public | Re-exports declarations, fields, row sources, shapes. |
| `data/model/public/declarations.py` | model public | `Table`, `Struct`, `ComputedStruct`, `Projection`, `ProjectionMeta`, `TableGroup`, `StructTemplate`, all option dataclasses, `is_concrete_table`, `is_table_group`. |
| `data/model/public/fields.py` | model public | `Field[T]` descriptor, `FieldMetadata`, `DeclaredValue` bound, `FieldDescriptor` alias, read overloads. |
| `data/model/public/row_sources.py` | model public | `RowSource[S]`, `RowSourceProvider`, `RelationRowSource`, `DerivedRowSource`, `JoinHow`. |
| `data/model/public/shapes.py` | model public | `ShapeField(attribute, name, logical_type)` for generated/declared row shapes. |
| `data/model/internal/__init__.py` | model internal | Re-exports DTOs and frozen specs. |
| `data/model/internal/model/__init__.py` | model internal | Re-exports `DeclarationSpec`, `FieldSpec`. |
| `data/model/internal/model/declarations.py` | model internal | Frozen `DeclarationSpec` (kind, name, description, annotations, fields, final, row_source, members, asset, semantics). |
| `data/model/internal/model/fields.py` | model internal | Frozen `FieldSpec` (attribute, external name, descriptor, logical type, access type, description, annotations, nested declaration, semantics). |
| `data/model/internal/dto/__init__.py` | model internal | Re-exports data DTOs. |
| `data/model/internal/dto/blueprint_dto.py` | model internal | `ColumnDTO`, `StructDTO`, `RelationDTO`, all row-plan DTOs, `ProjectionDTO`, `DataPartDTO`. |
| `data/service/__init__.py` | service | Marker only. |
| `data/service/public/__init__.py` | service public | Exports `field`, `computed_field`, `projection_row_source`, `shape_context`. |
| `data/service/public/fields.py` | service public | Authoring `field()` / `computed_field()` wrappers. |
| `data/service/public/rows.py` | service public | Public `shape_context`, `projection_row_source`, `relation_plan_dto`, and derive-* wrappers (only two names re-exported by the package). |
| `data/service/internal/__init__.py` | service internal | Composition point: transcription, codec, render, row planning, adapter. |
| `data/service/internal/adapters/kernel_language.py` | service internal adapter | `DataLanguage`: declaration discovery, keys, symbols, references, rendering. |
| `data/service/internal/codec.py` | service internal | Thin delegation to private document codec. |
| `data/service/internal/declarations.py` | service internal | `projection_row_source` delegation; `relation_plan_dto` builds a scan DTO. |
| `data/service/internal/fields.py` | service internal | Thin delegation to private field constructors. |
| `data/service/internal/rows.py` | service internal | Thin delegation to private row-value algebra and plan helpers. |
| `data/service/internal/source.py` | service internal | Thin delegation to private data renderer. |
| `data/service/internal/transcription.py` | service internal | Thin delegation to private transcription/validation. |
| `data/service/_private/__init__.py` | service private | Marker/docstring. |
| `data/service/_private/codec.py` | service private | Canonical document codec for `DataPartDTO` and all row-plan DTOs. |
| `data/service/_private/declarations.py` | service private | Class-creation mechanics, declaration specs, projection pinning, `_derive` for `Table.where`/`Projection.where`, table-group preparation. |
| `data/service/_private/descriptors.py` | service private | `Field` descriptor resolution, backing validation, access-type/nullability rules, `field_get`, `declared_fields`. |
| `data/service/_private/docstrings.py` | service private | Recovers an attribute docstring from the declaring class source with `inspect` + `ast`. |
| `data/service/_private/groups.py` | service private | Table-group flattening, catalog paths, cycle/duplicate validation. |
| `data/service/_private/naming.py` | service private | Class/member name inference: `snake_case`, `member_name`, `declaration_name`. |
| `data/service/_private/rows.py` | service private | Row-value algebra: plans, shape derivation, retargeting, join/union/group/unnest/order/distinct. |
| `data/service/_private/shapes.py` | service private | Generated row shapes, record mirrors, shape views, field/source lookup, shape comparison. |
| `data/service/_private/source.py` | service private | `DataPartDTO` -> authoring class source; plans -> method chains; expressions -> inline fragments. |
| `data/service/_private/symbols.py` | service private | Data declarations/fields -> linked symbols; keys, refs, field/struct qualification. |
| `data/service/_private/transcription.py` | service private | Declaration graph collection, `DataPartDTO` transcription, `validate_data`. |

---

## 2. Public authoring surface

### 2.1 Data declarations

| Name | Signature | Semantics |
| --- | --- | --- |
| `Table[AssetT: Asset]` | `class Table(RowSourceProvider, Shape, RowSource["Table[AssetT]"])`; `options: ClassVar[TableOptions]`; `row_source() -> RelationRowSource[Self]`; `where(predicate) -> DerivedRowSource[Self]` | A final logical relation read from exactly one logical `Asset`. The asset is named through the generic parameter; a concrete table without one is refused. `Table.shape = Table` (the class is its own shape). |
| `Struct` | `class Struct(StructDeclaration)`; `options: ClassVar[StructOptions]` | Nested-record declaration composed of source-backed `field()` members. Never a row source. |
| `ComputedStruct` | `class ComputedStruct(StructDeclaration)`; `options: ClassVar[StructOptions]` | Value-record declaration whose members are `computed_field(selection)` type witnesses. Never a row source; usable as `Field[T]`. |
| `Projection` | `class Projection(RowSourceProvider, Shape, RowSource["Projection"], metaclass=ProjectionMeta)`; `row_source() -> RelationRowSource[Any]`; `where(predicate) -> DerivedRowSource[Self]` | Final named relation composed from typed expressions. Always pinned to a row-source value at class creation. `Projection.shape` is a generated shape view, not the projection class. |
| `TableGroup` | `class TableGroup`; `options: ClassVar[TableGroupOptions]` | Final named catalog of final tables and nested groups. Not a shape and not a row source; carries no asset. |
| `StructTemplate` | `class StructTemplate`; `options: ClassVar[StructOptionsTemplate]` | Mixin sharing fields and annotations with `Table`, `Struct`, `ComputedStruct`; never becomes a declaration and never enters the blueprint. |
| `ProjectionMeta` | `__call__(cls, source: Any \| None = None) -> type[Projection]` | Implements `Projection(source)`: returns a dynamic pinned base; `None` is rejected. |

### 2.2 Options classes

| Class | Signature | Notes |
| --- | --- | --- |
| `TableOptions` | `TableOptions(name=None, description=None, annotations=(), semantics=None)` | Non-empty name if supplied; annotations normalized to tuple; `semantics` must be a declaration-semantics fragment, not `GraphSemantics` (checked by `require_declaration_semantics`). |
| `StructOptions` | `StructOptions(name=None, description=None, annotations=(), semantics=None)` | Same rules; used by both `Struct` and `ComputedStruct`. |
| `ProjectionOptions` | `ProjectionOptions(name=None, description=None, annotations=(), semantics=None)` | Same rules. |
| `TableGroupOptions` | `TableGroupOptions(members=(), name=None, description=None, annotations=())` | No `semantics` field. `members` is merged with class-attribute members. |
| `StructOptionsTemplate` | `StructOptionsTemplate(annotations=())` | Annotations only; no name/description/semantics; rejected on non-template hosts. |

### 2.3 Field constructors and descriptor

| Name | Signature | Semantics |
| --- | --- | --- |
| `field` | `field[T: DeclaredValue](*, name=None, description=None, annotations=(), semantics=None) -> Field[T]` | Source-backed member of a `Table` or source `Struct`. Empty explicit name rejected. |
| `computed_field` | `computed_field[T: DeclaredValue](value: Selection[T], *, name=None, description=None, annotations=(), semantics=None) -> Field[T]` | Expression-backed member of a `Projection` or `ComputedStruct`. `value` must be a `Selection`; it is normalized with `as_expression(value)`. |
| `Field[T: DeclaredValue]` | `Field(expression=None, metadata=FieldMetadata(), *, generated_logical_type=None)`; `expression`, `metadata` properties; `access_type(owner)`; `__get__` overloads | Descriptor and declaration carrier. `T` bounded by canonical scalar/`Date`/`Time`/`Timestamp`/`Uuid`/`CustomDataType`/`Struct`/`Array[Any]`/`Nullable[Any]`. |
| `FieldMetadata` | `FieldMetadata(name=None, description=None, annotations=(), attribute="", semantics=None)` | Frozen field facts; validates semantics at construction. |
| `DeclaredValue` | type alias: `bool \| int \| float \| str \| Date \| Time \| Timestamp \| Uuid \| CustomDataType \| Struct \| Array[Any] \| Nullable[Any]` | The closed value vocabulary; keeps the concrete subtype, does not promote to the bound. |

`Field.__get__` overloads are keyed on owner shape, not on a nullable annotation:
`type[Table] | type[Struct] -> Selection[Nullable[T]]`; `type[Projection] | type[ComputedStruct] -> Selection[T]`; the same split applies to instances.

### 2.4 Row-source values and operations

| Name | Signature | Semantics |
| --- | --- | --- |
| `RowSourceProvider` | `row_source() -> RowSource[Any]` classmethod | Declaration-level protocol; `Table` and `Projection` implement it. |
| `RowSource[S]` | `shape: type[S]`; `where`, `unnest`, `union`, `join`, `group_by`, `distinct`, `order_by` | A value: a shape plus a plan. `RowSource` itself is generic, not a dataclass/ABC. |
| `RelationRowSource[S]` | `RelationRowSource(source: type[Any], shape: type[S], filters: tuple[Selection[bool], ...] = ())`; `plan_dto -> RowScanDTO` property | Reads one named table or projection relation. `plan_dto` always returns a scan and **ignores** `filters`. |
| `DerivedRowSource[S]` | `DerivedRowSource(shape: type[S], source: type[Any], filters=(), plan_dto: RowSourcePlanDTO \| None = None)` | Result of `where`, `union`, `join`, `group_by`, `distinct`, `order_by`, `unnest`. |
| `JoinHow` | `Literal["inner", "left", "right", "full"]` | Join mode. |
| `ShapeField` | `ShapeField(attribute: str, name: str, logical_type: Any)` | One row-shape member in attribute/external form. Public in `data.model.public`, but not re-exported by the top-level `kg_build_system` facade. |

Method signatures:

| Method | Signature | Semantics |
| --- | --- | --- |
| `where` | `where(predicate: Callable[[S], Selection[bool]]) -> DerivedRowSource[S]` | Keeps rows whose predicate is true; null predicate does not keep the row. Shape preserved. |
| `unnest` | `unnest[I](selector: Callable[[S], Selection[Array[I]]]) -> DerivedRowSource[S]`; nullable-array overload | Expands one array member to one row per item; other members preserved; selected member narrowed to item type; null/empty array produces no rows. |
| `union` | `union(other: Any, *, all: bool = True) -> DerivedRowSource[S]` | Stacks same-shaped sources; `all=False` deduplicates. |
| `join` | `join(other: Any, *, on: Callable[[Any, Any], tuple[Any, Any]], how: JoinHow = "inner") -> DerivedRowSource[Any]` | Equi-join on one key expression per side; result shape `{on, left, right}`. |
| `group_by` | `group_by(*, by: Callable[[S], Any]) -> DerivedRowSource[Any]` | Groups by named scalar keys; result shape `{by, members}`. Null-key rows are dropped by the plan semantics. |
| `distinct` | `distinct() -> DerivedRowSource[S]` | Drops duplicate rows; shape preserved. |
| `order_by` | `order_by(*keys: Any, ascending: bool = True) -> DerivedRowSource[S]` | Orders by column names, selections or callables; one direction for every key; shape preserved. |

### 2.5 Selection and free constructors

| Name | Signature | Semantics |
| --- | --- | --- |
| `Selection[T]` | `__init__(node: ExpressionNode \| None = None, *, member: SelectedMember \| None = None)` | Exactly one of `node`/`member` must be supplied. This is the only authoring value type. |
| `NullableSelection[T]` | `type NullableSelection[T] = Selection[Nullable[T]]` | Alias, not a distinct class. |
| `logical_type` | `Selection[T].logical_type -> LogicalType` | Node type or selected-member type; the only structural accessor exposed. |
| `Pair[L, R]` | `class Pair(Struct)`; type-checking `left: Selection[L]`, `right: Selection[R]` | Value record produced by `zip`; not a row source and not an anonymous tuple. Runtime instances are generated `Pair_<hash>` subclasses with `left`/`right` descriptors. |
| `value_expression` | `value_expression(value: Any, *, logical_type: LogicalType \| None = None) -> Selection[Any]`; overloads for `bool`, `int`, `float`, `str` | Builds a typed literal selection; infers unambiguous scalar/array types; explicit type required for null/empty/all-null arrays. |
| `literal` | `literal(value: Any, *, logical_type: LogicalType \| None = None) -> LiteralExpression` | Public only from `expressions.service.public.expression`, not from the package facade; builds canonical literal data. |
| `all_of` | `all_of(*predicates: Selection[bool]) -> Selection[bool]` | Logical conjunction, folded left; empty identity is `True`. |
| `any_of` | `any_of(*predicates: Selection[bool]) -> Selection[bool]` | Logical disjunction, folded left; empty identity is `False`. |

`Selection` deliberately has no Python operators (`+`, `==`, etc.), no `.expression`/`.value`/`.model` accessor, and no direct `drop_null`/`expand`/`drop_if` methods. Tests enforce these absences (`tests/test_authoring_api.py:157-168`, `tests/typecheck/authoring_negative.py`).

---

## 3. The nullability model

### 3.1 What a field declares

A field declaration names a value type, never top-level absence. `Field[str | None]` and `Field[Nullable[str]]` are rejected at class creation; the error is `field type must be T, not T | None; source access is already nullable` (`data/service/_private/descriptors.py:142-160`). Item nullability remains in the value type: `Field[Array[Nullable[str]]]` is legal. Nested struct types also remain value types; only the read adds source presence.

### 3.2 Source reads vs computed reads

| Owner | Declaration | Read result | Mechanism |
| --- | --- | --- | --- |
| Source `Table` | `Field[T]` | `Selection[Nullable[T]]` | `FieldSpec.access_type = NullableType(logical_type)`; read is a `FieldReferenceExpression` whose `logical_type` is the access type. |
| Source `Struct` | `Field[T]` | `Selection[Nullable[T]]`, always | Read is a `SelectedMember` selection with the nullable access type; valid only under `extract`. |
| `Projection` output | `computed_field(value)` | Exactly `value.logical_type` | Read is a `FieldReferenceExpression` to the projection relation, with the computed field's access type. |
| `ComputedStruct` member | `computed_field(value)` | Witness type `value.logical_type` directly; composed with carrier by `extract` | Read is a `SelectedMember` selection; valid only under `extract`. |

`extract` composes presence: if the carrier is `Selection[Nullable[S]]`, a non-null member becomes `Selection[Nullable[T]]`; a source struct member is already nullable, so the nullable carrier does not add a second wrapper. A present carrier still yields nullable source members; a present `ComputedStruct` witness stays present under a present carrier (`tests/test_authoring_api.py:77-90`; `docs/reference/expressions.md` "extract").

### 3.3 Where absence is carried

| Location | What it carries | Notes |
| --- | --- | --- |
| `FieldSpec.logical_type` | Declared value type | Includes array-item/nested-value nullability, not source-row presence. |
| `FieldSpec.access_type` | Read type | Source/view: `Nullable[logical_type]`; computed: `logical_type`. |
| `SelectedMember.logical_type` | Access type of one struct-proxy member | Used by `extract`; no expression node exists until extraction. |
| `ExpressionNode.logical_type` | Access type of the expression | Every node, including field references and operations, carries its result type. |
| `FieldReferenceDTO.logical_type` | Access type of a field read | This is where source absence survives into the blueprint. |
| `ColumnDTO.logical_type` | Declared value type | For source columns it is **not** nullable; for projection outputs it is the output's selection type; for computed-struct members it is the witness type. |
| `ShapeField.logical_type` | Shape member type | Declared shapes use `FieldSpec.access_type` (`data/service/_private/shapes.py:205-219`); plan-derived shapes use `ColumnDTO.logical_type` (`data/service/_private/rows.py:124-204`). |

Consequences:

- For a table relation, the column DTO says `str`, while a field reference to it says `Nullable[str]`. Absence is a property of the read, not of the stored column.
- `lookup` always returns `Selection[Nullable[Array[target]]]`, even when the key is present (`data/service/_private/lookup.py:88-115`).
- `at` always returns a nullable item, even for a present array (`array_at_result`, `expressions/service/_private/operations.py:240-245`).
- `zip` returns `Array[Pair[L, R]]`; the outer array is nullable iff either input is nullable; `Pair.left/right` types are the array item types, so they may themselves be nullable.
- `drop_null()` narrows a nullable value to present and removes the row; `default_to(value)` returns present and keeps the row; `drop_if(predicate)` preserves the selection type; `expand()` on a nullable array removes the row for a null/empty array and returns the item selection (item may be nullable).
- A nullable selection exposes no present-only family methods in the type surface (`Selection[str].prepend`, etc.), but the runtime implementation is more permissive (see §9).

---

## 4. Grain and row-source model

### 4.1 How a table provides rows

`Table[Asset]` is a final declaration and a `RowSourceProvider`. `Table.row_source()` returns `RelationRowSource(cls, cls)`; the shape is the table class itself. `prepare_table_declaration` sets `cls.shape = cls` after recording the `DeclarationSpec` (`data/service/_private/declarations.py:181-203`). Field reads on a table are `FieldReferenceExpression(source=<table graph name>, path=(<external field name>,), logical_type=<nullable access type>, traversals=...)`.

A `TableGroup` contributes no rows. It is a catalog; each member table names its own asset. `group_tables(group)` flattens nested groups into `(table, catalog_path)` pairs; the path starts with the outermost group name and includes nested group names (`data/service/_private/groups.py:53-74`). Table groups are not `Shape`s and not `RowSource`s.

### 4.2 How a projection provides rows

`Projection(source)` is implemented by `ProjectionMeta.__call__`, which delegates to `prepare_projection_type(source)` and returns a dynamic `PinnedProjectionBase` carrying `_kg_row_source` and `_projection_base=True` (`data/model/public/declarations.py:233-241`; `data/service/_private/declarations.py:134-142, 362-371`). A user subclasses that base; `prepare_projection_declaration` finds the nearest `_kg_row_source` in the MRO, records it in `DeclarationSpec.row_source`, and sets `cls.shape = shape_view(cls)` (`data/service/_private/declarations.py:241-285`). `Projection.row_source()` returns `RelationRowSource(cls, cls.shape)`; a projection is therefore a named relation that other plans can scan by name.

`Projection.shape` is a generated row shape, not the projection class: `make_row_shape` creates `RowSourceShape_<hash>` with `_kg_shape_view=True`, `_kg_row_source_name=<projection name>`, and expression-backed `Field` descriptors (`data/service/_private/shapes.py:151-183`). Reading a projection output (`SiteProjection.site_id`) returns a field reference to the projection relation, not the original computed selection.

Pinning rules: `Projection(source)` requires a row-source **value**; passing a `Table`/`Projection` class is rejected by `as_row_source` (`data/service/_private/rows.py:49-58`). A final projection may not inherit another final projection; a pinned base is not final and may be subclassed. A final projection must declare at least one `computed_field`. The pin does not copy fields.

### 4.3 How structs and computed structs participate

`Struct` is a shape only: it has no `row_source()` and cannot be bound. `ComputedStruct` is a value-record shape whose members are type witnesses; it is never evaluated as a row plan. Both can be used as `Field[T]` types. `extract` resolves the declared struct class from the `StructType` identity and builds a symbolic proxy; `ComputedStruct` members read as `SelectedMember`s, source struct members read as nullable `SelectedMember`s.

### 4.4 Row-source algebra

| Operation | Input | Output value | Output shape | Key constraints |
| --- | --- | --- | --- | --- |
| `where` | `RowSource[S]`, predicate | `DerivedRowSource[S]` | Preserved | Predicate must be callable and return `Selection[bool]`; evaluated with a shape proxy. |
| `unnest` | `RowSource[S]`, selector | `DerivedRowSource[S]` | Preserved except selected array member narrowed to item type | Selector must return an array expression; the selected field must be one member of the input shape; null/empty array yields no rows. |
| `union` | two row sources | `DerivedRowSource[S]` | Left shape | Member external names and full logical types must match exactly; no cast/rename/reorder; `all` controls dedup. |
| `join` | two row sources, `on`, `how` | `DerivedRowSource[Any]` | Generated `{on, left, right}` | Keys must be scalar and share a base logical type; arrays/structs refused; `how` in the four modes; `on` may return a key pair or one `equals` expression. |
| `group_by` | `RowSource[S]`, `by` | `DerivedRowSource[Any]` | Generated `{by, members}` | At least one key; key names public unique identifiers; keys scalar; keys projected to non-null base types; members are record mirrors of the input row. |
| `distinct` | `RowSource[S]` | `DerivedRowSource[S]` | Preserved | None. |
| `order_by` | `RowSource[S]`, keys | `DerivedRowSource[S]` | Preserved | At least one key; key is column name, selection or callable; one `ascending` value for all keys. |

### 4.5 Join and group shapes

Join shape fields are `on`, `left`, `right` (`data/service/_private/rows.py:339-390`):

| Member | Type | Presence |
| --- | --- | --- |
| `on` | Shared key base type | Present; nullable for an outer mode whose surviving side's key is nullable. |
| `left` | `record_shape_type(shape_fields(left))` | Present for `inner`/`left`; nullable for `right`/`full`. |
| `right` | `record_shape_type(shape_fields(right))` | Present for `inner`/`right`; nullable for `left`/`full`. |

`left`/`right` are generated record mirrors (struct-like; read through `extract`). `on` is the key value. A null key never matches in any mode (semantic rule; engine emits equality). The `equals` form requires present text on both sides; defaulting makes null keys compare equal, unlike the pair form.

Group shape fields are `by`, `members` (`data/service/_private/rows.py:393-447`):

| Member | Type | Presence |
| --- | --- | --- |
| `by` | Generated record of named key fields (base scalar types) | Every key member present. |
| `members` | `Array[record mirror of input row]` | Present array; order unspecified; no aggregates. |

### 4.6 Plan identity and retargeting

`row_source_key(plan)` returns the relation name for a `RowScanDTO`, otherwise `"derived:" + sha256(canonical plan document)[:24]` (`data/service/_private/rows.py:67-74`). `plan_shape_source_name(plan)` unwraps filter/distinct/order-by and follows the left side of a union; join/group/unnest use the plan key (`77-83`). `retarget_expression_dto` rewrites `FieldReferenceDTO.field` from one source key to another, preserving field name and nested path, and recurses through lookup keys and operation arguments (`207-240`). Every derive operation retargets authored expressions from the authoring shape source to the plan key so a derived plan's expressions point at the correct source.

`row_source_plan_dto(value)` returns `RowScanDTO` for a `RelationRowSource`, the stored `plan_dto` for a derived source, and otherwise rebuilds a scan plus accumulated filters (`565-589`). In practice every derive sets `plan_dto`; the `filters` fallback is only for hand-built values.

### 4.7 Plan DTO model

| DTO | Fields | Meaning |
| --- | --- | --- |
| `RowScanDTO` | `relation: RelationRef` | Read a named table or projection relation. |
| `RowFilterDTO` | `input`, `predicate: ExpressionDTO` | Keep rows satisfying predicate. |
| `RowUnionDTO` | `left`, `right`, `all: bool` | Stack two same-shaped plans. |
| `RowJoinDTO` | `left`, `right`, `left_key`, `right_key`, `how` | Equi-join two plans. |
| `RowGroupByDTO` | `input`, `keys: tuple[(name, ExpressionDTO)]` | Group by named keys; members collected. |
| `RowDistinctDTO` | `input` | Deduplicate rows. |
| `RowOrderByDTO` | `input`, `keys: tuple[(ExpressionDTO, ascending)]` | Order rows. |
| `RowUnnestDTO` | `input`, `field: str`, `expression: ExpressionDTO` | Expand one array column; `field` is external name, `expression` is that array in the input plan. |

The plan DTO carries no row semantics; row effects are operations inside expressions and are re-derived by the core planner from operation names (`distribution/modules/core/service/_private/planning/emission.py`). The plan DTO also carries no shape; shapes are derived later from declarations and the plan (`plan_fields`).

---

## 5. Operation surface

### 5.1 `Selection` value and navigation methods

| Method | Receiver / arguments | Result | Constraints and runtime behavior |
| --- | --- | --- | --- |
| `logical_type` | property | `LogicalType` | Node type or selected-member type. |
| `alter_rows` | no args | One of the four effect handles | Selected from the actual `logical_type`: nullable array -> `NullableArrayRowEffects`, nullable non-array -> `NullableRowEffects`, array -> `ArrayRowEffects`, otherwise `RowEffects`. |
| `extract` | `selector: Callable[[S], Selection[U]]` | `Selection[U]` / `Selection[Nullable[U]]` | Receiver must be a struct selection after unwrapping one nullable; selector receives a symbolic declared-struct instance; must return a field selection from that declaration. Composes carrier presence; uses `struct_field` when the parent is not a plain field reference. |
| `at` | `index: int \| Selection[int]` | `Selection[Nullable[U]]` | Receiver must be array (runtime unwraps outer nullable). 0-based; out-of-bounds gives null. |
| `slice` | `start`, `end`: `int \| Selection[int]` | Same array type | Receiver array; 0-based, end-exclusive; no bounds/ordering check at authoring. |
| `lookup` | `relation: type[S] \| RelationRef`, `key: Selection[Any] \| None = None`, `*, target_key: str \| Selection[Any] \| None = None` | `Selection[Nullable[Array[S]]]` | Reads target records whose key equals the current row's key; null key never matches; no `how`; `target_key` defaults to the field name of a direct field key. Result type is always nullable array. |
| `zip` | `other: Selection[Array[R]]` | `Selection[Array[Pair[L, R]]]` with nullable composition | Both receivers must be arrays; pairs by position; equal length required at execution; absent input makes result absent. |
| `unique` | no args | Same array type | Array receiver; emits `distinct` operation. |
| `sort` | no args | Same array type | Array receiver; ascending sort. |
| `concat` | `separator: str` | `Selection[str]` (nullable if input nullable at runtime) | Receiver must be array of non-null strings; empty array yields `""` per docs/engine; emits `join`. |
| `transform_items` | `selector: Callable[[Selection[I]], Selection[U]]` | `Selection[Array[U]]` | Array receiver; selector receives a typed item selection; body may not contain row effects; preserves outer array nullability and item nullability composition. |
| `drop_null_items` | no args | `Selection[Array[I]]` | Receiver must be `Array[Nullable[I]]` in the type surface; runtime accepts a nullable outer array and preserves outer presence. A non-null-item array is returned unchanged. |
| `prepend` / `append` | `value: str \| Selection[str]` | `Selection[str]` | Present text receiver in the type surface; runtime accepts nullable text and returns nullable text. Both emit the `concat` operation (not the registered `append` spec). |
| `replace` | `search: str`, `replacement: str` | `Selection[str]` | Present text receiver; replaces every occurrence. |
| `equals` | `value: str \| Selection[str]` | `Selection[bool]` | Present text receiver; the only comparison operation; emits `equals`; runtime result nullable if either input is nullable. |
| `before_separator` / `after_separator` | `separator: str`, `occurrence: int = 1`, `*, include_separator: bool = False` | `Selection[str]` | Present text receiver; occurrence is 1-based and must be >= 1; separator empty is not rejected at authoring; missing occurrence returns whole string/empty per docs. |
| `add` / `sub` | `other: int \| Selection[int]` or `float \| Selection[float]` | Same numeric type | Present numeric receiver in the type surface; runtime validates both arguments have the exact same logical type. |
| `not_` | no args | `Selection[bool]` | Present bool receiver in the type surface; runtime accepts nullable bool and returns nullable bool. |
| `and_` / `or_` | `other: bool \| Selection[bool]` | `Selection[bool]` | Present bool receiver in the type surface; runtime accepts nullable bool and returns nullable bool. |
| `to_string` | no args | `Selection[str]` | Receiver must unwrap to a `UnitType` scalar; runtime accepts nullable unit and returns nullable text; arrays/structs/custom types refused. |
| `default_to` | `value: U \| Selection[U]` | `Selection[U]` | Receiver must be nullable; fallback must have the receiver's non-null value type; emits `coalesce`; keeps the row. |

### 5.2 Row-effect handles

| Handle | Available effects | Signatures | Result / row behavior |
| --- | --- | --- | --- |
| `RowEffects[S]` | `drop_if` | `drop_if(predicate: Callable[[S], Selection[bool]]) -> S` | Keeps rows whose predicate is true; type does not refine. |
| `NullableRowEffects[N]` | `drop_null`, `drop_if` | `drop_null() -> Selection[N]`; `drop_if(predicate: Callable[[Selection[Nullable[N]]], Selection[bool]]) -> Selection[Nullable[N]]` | `drop_null` removes null rows and returns present; `drop_if` preserves presence. |
| `ArrayRowEffects[I]` | `expand`, `drop_if` | `expand() -> Selection[I]`; `drop_if(predicate: Callable[[Selection[Array[I]]], Selection[bool]]) -> Selection[Array[I]]` | `expand` emits one row per item; `drop_if` preserves the array type. |
| `NullableArrayRowEffects[I]` | `drop_null`, `expand`, `drop_if` | inherits `NullableRowEffects[Array[I]]`, overrides `expand` | Null/empty array produces no rows; `drop_if` preserves nullable-array type. |

Each handle is one-shot: `RowEffectHandle.consume()` raises `TypeError("row-effect handle already consumed; call alter_rows() again")` on reuse (`expressions/model/internal/model/selection.py:26-41`). Effects are not methods on `Selection` itself; `alter_rows` creates a fresh handle each time.

### 5.3 Built-in operation specs

| Spec | Arity | Arguments | Result | Row effect / notes |
| --- | --- | --- | --- | --- |
| `add` | 2 | numeric, numeric | type of arg 1 | Both arguments must have one numeric type. |
| `subtract` | 2 | numeric, numeric | type of arg 1 | Same rule. |
| `concat` | 2..N | `str` values | `str`, nullable if any input nullable | Text concatenation. |
| `append` | 2..N | `str` values | same as `concat` | Registered but not used by the authoring `append` method (which emits `concat`). |
| `equals` | 2 | `str`, `str` | `bool`, nullable if any input nullable | Text-only equality. |
| `replace` | 3 | `str`, `str`, `str` | `str`, nullable by input | Replace all. |
| `to_string` | 1 | canonical scalar | `str`, nullable by input | Rejects non-`UnitType`. |
| `before_separator` | 2 | `str`, separator `str`; params `occurrence>=1`, `include_separator` bool | `str`, nullable by input | No empty-separator validation at authoring. |
| `after_separator` | 2 | same | same | Same. |
| `array_at` | 2 | array, `int` | `Nullable[item]` (item unchanged if already nullable) | 0-based. |
| `array_slice` | 3 | array, `int`, `int` | type of array | 0-based, end-exclusive. |
| `transform_items` | 2 | array, item expression; param `item="item"` | `Array[body]`, outer nullable by input | Body may not contain row effects. |
| `drop_null_items` | 1 | array | array with item non-null; outer presence preserved | Returns unchanged if items are already non-null. |
| `sort` | 1 | array | same array type | Ascending. |
| `distinct` | 1 | array | same array type | Array-level dedup. |
| `join` | 2 | array of non-null `str`, separator `str` | `str`, nullable by array input | This is `Selection.concat`. |
| `coalesce` | 2..N | values of one non-null type | non-null type of arg 1 | Fallback chain; arguments must share value type. |
| `not` | 1 | `bool` | `bool`, nullable by input | Boolean negation. |
| `and` | 2 | `bool`, `bool` | `bool`, nullable by input | Logical and. |
| `or` | 2 | `bool`, `bool` | `bool`, nullable by input | Logical or. |
| `struct_field` | 1 | struct; param `name` | explicit result type at application | Member read used when `extract` has no plain field-reference parent. |
| `expand` | 1 | array | item type | Row effect `expand`; scope required. |
| `drop_null` | 1 | any | non-nullable arg type | Row effect `filter`; no scope. |
| `drop_if` | 2 | value, `bool` predicate | type of arg 1 | Row effect `filter`; predicate at index 1. |
| `zip` | 2 | array, array | `Array[Pair[left item, right item]]`, outer nullable by inputs | Equal length required at execution. |

Spec-level validation is in `expressions/service/_private/operations.py`: arity (`28-41`), parameter defaults/required/accepts (`77-101`), argument predicate checks (`104-123`), result resolution (`126-135`), and row-effect resolution (`138-166`). `OperationSpec.__post_init__` rejects non-positive arity, inverted bounds and duplicate/empty parameter names (`service/internal/operations/spec.py:109-124`).

---

## 6. Transcription: declarations to DTOs and source text

### 6.1 Class-creation facts

For every data class, `prepare_*_declaration` resolves fields once and stores a frozen `DeclarationSpec` on `_kg_declaration_spec` (`data/service/_private/declarations.py:71-104`). Each `FieldSpec` records external name, descriptor, declared logical type, access type, description, annotations, nested declaration and semantics (`data/model/internal/model/fields.py:16-29`). External names default from the attribute via `snake_case` with one trailing underscore stripped (`data/service/_private/naming.py:7-22`); descriptions default to the string literal directly below the assignment, recovered from source with `inspect`+`ast` (`data/service/_private/docstrings.py`). Description resolution is class creation time only; if source is unavailable, no attribute documentation is resolved.

### 6.2 Data DTO transcription

`transcribe_data(declarations)` walks reachable classes (`data/service/_private/transcription.py:201-249`):

- A final `table` becomes `RelationDTO`; a final `projection` becomes `ProjectionDTO`; `struct` and `computed_struct` both become `StructDTO`; table groups are walked for members but do not become DTOs.
- `collect_declarations` follows field nested declarations, `row_source.source`, and table-group members (`36-69`).
- Column name/type/ref are built by `_column`: `ColumnDTO(name, type_to_dto(item.logical_type), ref=FieldRef("data", Key((f"{owner}.{name}",))), description, annotations, expression, semantics)` (`100-115`).
- `StructDTO`/`RelationDTO` columns use `expression=None`; `RelationDTO` also carries `AssetRef`; `ProjectionDTO` columns use `expression=expression_dto(...)` and the projection carries `row_source: RowSourcePlanDTO` (`118-168`).
- Structs/relations/projections are sorted by graph name in the resulting `DataPartDTO` (`227-249`).
- `validate_data` enforces unique relation names, unique projection names, cross-namespace relation/projection uniqueness, unique column names per declaration, a non-null asset on every relation, and that every projection scan source is a known relation/projection (`252-280`).

Notable DTO properties:

- A source column's logical type is the declared value type, so the DTO does not record source absence on the column; expression field reads do.
- `ColumnDTO.ref` is always a `FieldRef`; `_decode_column` rejects a non-`FieldRef`.
- `ProjectionDTO.row_source` is a plan DTO, not a row-source value; output expressions are stored per column.
- There is no `TableGroupDTO` and no computed-struct marker; both are lost in the data DTO.
- `DataPartDTO` carries no symbol ids (`tests/distribution/test_blueprint_dto.py`). Declaration identity is carried by typed refs (`FieldRef`, `RelationRef`, `AssetRef`) and by `StructTypeDTO` identity for nested records, not by an owner object.

### 6.3 Expression DTO transcription

`expression_dto(node)` maps every authoring node to a DTO (`expressions/service/_private/dto.py:45-72`):

| Authoring node | DTO | Payload |
| --- | --- | --- |
| `LiteralExpression` | `LiteralExpressionDTO` | `value: FrozenJson`, `logical_type`. |
| `VariableExpression` | `VariableExpressionDTO` | `name`, `logical_type`; used for `transform_items` item. |
| `FieldReferenceExpression` | `FieldReferenceDTO` | top-level `FieldRef("data", Key((f"{source}.{path[0]}",)))`, remaining nested `path`, `logical_type`. |
| `LookupExpression` | `LookupExpressionDTO` | target `RelationRef`, `target_field`, key expression, nullable-array `logical_type`. |
| `OperationExpression` | `OperationExpressionDTO` | `OperationRef("expressions", Key((operator,)))`, argument tuple, named parameters, `logical_type`. |

Authoring-only facts are omitted from the DTO: `RowSemantics`, `Traversal` metadata, and the distinction between a field read and a selected member. The DTO's own docstring says it "carries no authoring row semantics; row effects are operations in the expression tree" (`expressions/model/internal/dto/blueprint_dto.py:1-7`). The canonical document codec uses `kind` tags `literal`, `variable`, `field`, `lookup`, `operation`; operation parameters are sorted by name (`expressions/service/_private/dto_codec.py`).

`expression_references(dto)` walks the DTO tree and emits field/operation/lookup references; field refs whose relation starts with `derived:` are skipped (`expressions/service/_private/dto.py:91-118`). `authoring_references(node)` does the same on the authoring tree, skipping field refs whose source starts with `derived:` and only emitting operation refs for names present in `DEFAULT_OPERATIONS` (`expressions/service/_private/symbols.py:51-75`).

### 6.4 Symbol projection

`DataLanguage` discovers one declaration per reachable data class and one per field (`data/service/internal/adapters/kernel_language.py`). Keys:

- A table/projection/struct uses its graph name as one key segment; a struct whose graph name is duplicated or collides with a relation/projection takes `(name, module.qualname)` (`data/service/_private/symbols.py:96-129`).
- A field key joins the owner key segments and the external column name with a dot inside one key segment, e.g. `Key(("sites.site_name",))` (`139-152`).
- A field symbol is its own declaration; it references the expression leaves and any nested struct declaration (`173-204`).
- A relation references its fields and asset; a projection references its fields, every scan source, every plan expression and every output expression (`214-248`).
- `value_identity` maps authoring values/DTO fragments to `data` `SymbolRef`s (`270-288`).

`ExpressionsLanguage` discovers one declaration per built-in `OperationSpec` and one `operation` symbol per spec; an expression tree is not a symbol (`expressions/service/internal/adapters/kernel_language.py`). `ExpressionsLanguage.transcribe_fragment` converts an authoring node to an `ExpressionDTO`; `DataLanguage` has no analogous fragment method.

### 6.5 Source rendering

Data rendering (`data/service/_private/source.py`):

- `render_data(data, context=None, *, class_names=None) -> SourceFragment` renders structs, relations and projections in that order, separated by three newlines, with a trailing newline.
- Structs render as `class X(Struct):` with `StructOptions`; relations as `class X(Table[Asset]):` with `TableOptions`; projections as `class X(Projection(<plan>)):` with `ProjectionOptions`.
- Source fields render `attr: Field[T] = field(...)`; projection outputs render `attr = computed_field(<expression>, ...)`; `name=`, `description=`, `annotations=` and `semantics=` are emitted when present.
- Row plans render as method chains: `relation.row_source()`, `.where(lambda row: <expr>)`, `.union(<plan>, all=True)`, `.join(<plan>, on=lambda left, right: (<l>, <r>), how='inner')`, `.group_by(by=lambda row: {'k': <expr>})`, `.distinct()`, `.order_by(<exprs>, ascending=True)`, `.unnest(lambda row: <expr>)`.
- Expressions render inline through `render_expression_source`: literals as `value_expression(value, logical_type=...)`, field reads as `field_reference(source=..., path=..., logical_type=...)`, lookups as `lookup_expression(ref_from_document(...), key=..., target_field=..., logical_type=...)`, and operations as `operation('op', args, param=..., logical_type=...)`. These are low-level constructors imported from `expressions.service.internal`, not fluent `Selection` methods.
- Attribute names use `distribution.service.internal.rendering.member_name`, which sanitizes invalid identifiers and Python keywords; declarations use `data._private.naming.member_name`, which only strips a trailing underscore. The two functions can disagree (see §9).
- `DataLanguage.render` wraps a single `StructDTO`/`RelationDTO`/`ProjectionDTO` in a `DataPartDTO` and delegates; `data_to_fragment` and `render` are aliases.
- Table groups and computed structs are not rendered because the DTO has no representation for them.

Expression rendering (`expressions/service/_private/source.py`) emits imports for `value_expression`, the three low-level constructors, `ref_from_document`, canonical type names, and `CustomType`/`StructType`. It does not emit `Selection` method chains, row-effect handles, or `alter_rows()`.

### 6.6 What is private

- The compiler tree: `ExpressionNode` and all node classes; `ValueExpression` (documented as "not part of the authoring facade"); `SelectedMember`; `RowEffectHandle`.
- `DeclarationSpec`, `FieldSpec`, all DTOs and document codecs; `_private` service modules and all `_kg_*`/`_data_*` class attributes.
- Operation specs and `DEFAULT_OPERATIONS`; the built-in operation modules.
- Generated shape classes (`RowSourceShape_<hash>`, `RowSourceRecord_<hash>`) and generated `Pair_<hash>` classes; they are dynamically registered in their modules and are not user-declared names.
- `ShapeField` is model-public for the planners but not exported by the top-level `kg_build_system` facade; `RowSourceProvider`, `ProjectionMeta`, `is_concrete_table` and `is_table_group` are available from `data.model.public`/`data`, not all from top-level.

---

## 7. Invariants enforced by code and tests

| Invariant | Enforcement | Tests / docs |
| --- | --- | --- |
| A **source** field annotation is exactly `Field[T]` with one argument; no top-level nullable annotation. | `data/service/_private/descriptors.py:142-160` (`_field_annotation`). | `tests/test_authoring_api.py:120-123`; `tests/typecheck/authoring_negative.py:76-79`. |
| A field type cannot be a `Table` or `Projection`; it must be a value record. | `descriptors.py:205-213`. | `docs/reference/declarations.md` "field()". |
| Backing constructor must match owner: source host uses `field()`, computed host uses `computed_field()`. | `descriptors.py:163-175`. | `tests/test_authoring_api.py:125-136`. |
| Two fields in one declaration cannot share an external name. | `descriptors.py:217-225`. | `docs/concepts/data-contracts.md` "Limits". |
| One `Field` instance cannot be assigned to two declarations. | `descriptors.py:257-262`. | `docs/reference/declarations.md`. |
| Source reads are nullable; computed reads carry the declared selection type. | `descriptors.py:214-216, 303-358`. | `tests/test_authoring_api.py:64-75, 114-118`. |
| A final `Table`/`Projection`/`TableGroup` may not inherit another final declaration of the same kind. | `declarations.py:185-186, 246-251, 292-295`. | `tests/test_authoring_api.py:125-130`; docs. |
| A concrete `Table` must name an `Asset` subclass through `Table[Asset]`. | `declarations.py:157-178`. | `docs/reference/declarations.md`. |
| `Projection(source)` requires a row-source value and at least one `computed_field`. | `declarations.py:276-282, 362-371`. | `tests/test_authoring_api.py:125-130`. |
| Table groups contain only final tables/groups, are non-empty, acyclic, and have unique tables/catalog paths. | `declarations.py:309-320`; `groups.py:53-74`. | `docs/reference/declarations.md` "TableGroup". |
| `StructTemplate` options are annotations-only and templates cannot mix into `Projection`/`TableGroup`. | `declarations.py:38-56, 342-359`. | `docs/reference/declarations.md` "StructTemplate". |
| Option names are non-empty; option semantics have the declaration fragment type. | `declarations.py:66-121`; `require_declaration_semantics`. | `tests/distribution/test_data_semantics.py:94-106`. |
| A row-effect handle is one-shot. | `model/internal/model/selection.py:26-41`. | `tests/test_authoring_api.py:108-112`. |
| Row effects are available only through `alter_rows` and only for compatible selections. | `selection.py:74-110`; `effects.py`; `_private/selections.py:383-415`. | `tests/test_authoring_api.py:92-106`; `tests/typecheck/authoring_negative.py`. |
| Expression nodes enforce non-empty field paths/sources, valid traversal kinds/prefixes, required variable names, unique/sorted operation parameters, named lookup targets. | `expressions/model/internal/model/expression.py:18-160`. | No direct unit test found; construction sites rely on it. |
| Operation specs enforce arity, parameter names/defaults/accepts, argument predicates and result-type resolution. | `expressions/service/_private/operations.py:28-166`; `service/internal/operations/spec.py:109-124`. | `tests/distribution/test_expression_operations.py`. |
| Duplicate operation names cannot silently shadow one another. | `operations/registry.py`; `OperationRegistry.__post_init__`. | — |
| Row semantics: expand requires a non-empty scope; filter may not have one; preserve may not have upstream effects; identical expand effects are deduplicated. | `expression.py:18-57`; `_private/semantics.py:11-39`. | — |
| Row-source operations accept only row-source values, not declaration classes. | `data/service/_private/rows.py:49-58`. | `tests/test_authoring_api.py:154-155`; docs. |
| Union operands must have identical member external names and full logical types. | `rows.py:325-336`; `shapes.py:257-263`. | `tests/distribution/test_expression_operations.py`; docs. |
| Join keys are scalar and share a base logical type; `how` is one of four values; arrays/structs refused. | `rows.py:290-322, 339-390`. | `tests/distribution/test_expression_operations.py`; docs. |
| Group keys are non-empty, public unique identifiers and scalar; key fields are projected to base types. | `rows.py:393-447`. | docs/reference/row-sources.md. |
| Unnest requires an array expression whose selected field is a member of the input shape. | `rows.py:450-504`; `plan_fields` at `190-204`. | `tests/distribution/test_expression_operations.py:248-299`. |
| `order_by` requires at least one key and a known column for string keys. | `rows.py:517-562`. | No test found for non-string keys (see §9). |
| `default_to` requires a nullable receiver and exact fallback type; `coalesce` requires one shared value type. | `_private/selections.py:366-376`; `operations.py:267-273`. | `docs/reference/expressions.md` "default_to". |
| `transform_items` selectors may not contain row effects. | `_private/arrays.py:39-40`; `operations.py:326-331`. | `docs/reference/expressions.md`. |
| Literal values are class-exact for their unit; null/empty/all-null arrays need an explicit logical type; struct/custom literals are refused. | `_private/literals.py:31-92`. | `docs/reference/expressions.md` "Literals". |
| Data DTO names/refs: relation/projection names unique, columns unique, every relation has an asset, projection scans known sources. | `transcription.py:252-280`. | `tests/distribution/test_data_semantics.py`; `test_source_roundtrip.py`. |
| DTOs carry no symbol ids. | DTO definitions; `tests/distribution/test_blueprint_dto.py`. | — |
| Language packages obey the public/internal/private boundary; facades import only public surfaces; no cross-package private imports. | `tests/test_architecture.py`. | — |
| Source round-trips preserve the blueprint document for the covered fixtures. | `tests/distribution/test_source_roundtrip.py`; `tests/distribution/test_expression_operations.py:302-362`. | Fixtures do not cover `where`, non-string `order_by`, computed structs or table groups. |

---

## 8. Where docs and code disagree

| Topic | Doc claim | Code / evidence | Assessment |
| --- | --- | --- | --- |
| `.expression` accessor | `docs/reference/expressions.md:7-9` says there is no `.expression`, `.value` or `.model`; `tests/test_authoring_api.py:157-160` enforces their absence on selections. | Several API docstrings still show `.expression.equals(...)`: `data/model/public/declarations.py:165`, `267`; `data/model/public/row_sources.py:72, 138`. | Docs and tests agree; the code **docstrings** are stale. `Field.expression` exists on the descriptor (not on a `Selection`) as a private implementation accessor. |
| `semantics=` parameter | `docs/reference/declarations.md` signatures for `field()`/`computed_field()` list only `name`, `description`, `annotations` (lines 32-38, 96-102); the options table lists semantics only on options. | Both constructors include `semantics: Semantics \| None = None` (`data/service/public/fields.py:22-66`). | Docs lag code; `tests/distribution/test_data_semantics.py` exercises `semantics=` on fields. |
| Computed field annotation requirement | `docs/reference/declarations.md` error table says `<Class>.<attribute> must have a Field[T] annotation` for a computed output. | `resolve_field_specs` only calls `_field_annotation` for source fields; for a computed field it uses an annotation only if it is already `Field[...]` (`descriptors.py:191-200`). A computed field with a non-`Field` annotation is silently accepted. | Invariant is weaker than documented. |
| Error text for nullable source annotation | Docs say `<Class>.<attribute> is a source field and must be declared with field(), not T \| None` (`docs/reference/declarations.md:90`). | Code raises `field type must be T, not T | None; source access is already nullable` (`descriptors.py:155-159`). | Same behavior, different message. |
| Nullable selection family operations | Docs say a nullable selection exposes no `prepend`/`add`/`equals`/`concat` family operation (`docs/reference/expressions.md:283-284, 408-411`; `docs/concepts/expressions.md:229-233`). Typecheck negative enforces this. | Runtime `array_operation`/`array_concat`/`text_concat`/`text_equals`/`boolean_*` accept nullable inputs by unwrapping the outer `NullableType`; e.g. `_array_base` uses `_base` (`_private/selections.py:177-181, 240-248, 272-307, 345-358`). | Static surface is narrower than runtime. |
| Empty separator | Docs list `separator must be non-empty` for `before_separator`/`after_separator` (`docs/reference/expressions.md:321-324`). | The specs accept any `str` separator; only `occurrence >= 1` is checked (`operations/before_separator.py`, `operations/after_separator.py`; `positive_integer`). | No authoring-time empty-separator check; an engine may still reject it. |
| `order_by` key error | Docs say `order_by keys must be expressions or column names` (`docs/reference/row-sources.md:290`). | Code says `order_by keys must be selections or column names` (`_private/rows.py:551`). | Message mismatch; see also the non-string key bug in §9. |
| `unnest` selector | Docs say the selector must read one **direct** array field (`docs/reference/row-sources.md:106-108, 131`). | `_selected_field` accepts a `FieldReferenceExpression` or an `OperationExpression` that contains exactly one distinct field name (`_private/rows.py:450-460`); value-preserving operations such as `unique()` or `drop_null()` pass. | Code is looser than docs; row effects in the selector are not recorded in `RowUnnestDTO`. |
| Group-key error text | Docs list `generated shape member '_name' must be a public Python identifier` for a key starting with `_` (`docs/reference/row-sources.md:255-257`). | `derive_group_by` rejects names starting with `_` earlier with `group_by key names must be Python identifiers` (`_private/rows.py:421-424`). | The generated-shape message is likely unreachable for group keys. |
| `Pair` members | Docs say `Pair` has present `left` and `right` members (`docs/reference/expressions.md:263-270`). | `pair_type` uses the array item types directly; if an array item is `Nullable[T]`, `left`/`right` are nullable (`_private/pair.py:57-92`; `zip_result`). | "Present" is only true for non-null item arrays. |
| Example imports | `data/model/public/shapes.py:9` shows `from kg_build_system import ShapeField, make_row_shape`. | `ShapeField` is not in the top-level `kg_build_system` export table; `make_row_shape` is not exported from a public package facade. | Stale example; `ShapeField` is available from `data.model.public`/`data`. |
| Example `projection_base()` | `data/model/public/row_sources.py:16` shows `class ActiveSiteLabels(active.projection_base())`. | `DerivedRowSource` has no `projection_base`; tests assert `Table`/`Projection` have no `projection_base` (`tests/test_authoring_api.py:161-162`). | Stale docstring in public code. |
| `Projection.where` result wording | Docstring says the predicate must return a `BoolExpression` (`declarations.py:262-270`). | There is no `BoolExpression` in the current surface; the runtime check requires `Selection`. | Stale terminology. |

---

## 9. Surprising or ambiguous points

1. **Runtime is more permissive than the static surface.** `Selection.concat`, `unique`, `sort`, `at`, `slice`, `prepend`, `equals`, `not_`, `and_`, `or_`, `to_string` are typed for present inputs, but the private helpers unwrap one `NullableType` and accept nullable receivers. For example `Source.tags.concat(",")` is a type error in `tests/typecheck/authoring_negative.py` yet `hasattr(Source.tags, "concat")` is asserted in `tests/test_authoring_api.py:168`, and `_array_base`/`_base` would accept it. Numeric `add`/`sub` are the exception: `validate_numeric_operation` requires both arguments to have the exact same logical type, so `Nullable[int].add(1)` fails at runtime while `Nullable[str].prepend("x")` succeeds. Unclear whether the broader runtime is intentional to support generated source or an omission.

2. **`order_by` with a selection or callable appears to always fail.** `derive_order_by` assigns `expression = as_expression(...)`, and `as_expression` always returns a `ValueExpression` (`expressions/service/_private/selections.py:78-89`); the next check is `if not isinstance(expression, Selection): raise TypeError(...)` (`data/service/_private/rows.py:531-551`). Therefore only string column names reach the append branch. This contradicts the public signature and docs. No test covers non-string keys.

3. **Filtered row-source source round-trip appears broken.** `render_data` renders a `RowFilterDTO` as `.where(lambda row: <rendered expression>)` (`data/service/_private/source.py:139-142`). The expression renderer emits low-level `operation(...)`/`field_reference(...)`, which return `OperationExpression`/`FieldReferenceExpression`, not `Selection` (`expressions/service/_private/source.py:53-90`; `expressions/service/_private/build.py:36-61`). `derive_where` then evaluates the predicate and requires `isinstance(result, Selection)` (`data/service/_private/rows.py:249-259`). Any filter plan recreated from generated source would raise. The existing round-trip fixtures use no `where` (`tests/distribution/test_source_roundtrip.py`; `tests/distribution/test_expression_operations.py:302-362`). Marked "code path indicates"; worth a dedicated test.

4. **Computed structs and table groups are not represented in the data DTO.** `transcribe_data` maps `computed_struct` to `StructDTO` with `expression=None` for its members (`transcription.py:118-126, 220-221`), and `_walk` walks table-group members but never emits a group DTO (`36-60, 201-225`). `render_data` can only emit `Struct`, `Table` and `Projection` classes, so a blueprint cannot reconstruct a `ComputedStruct` or `TableGroup`. For a computed struct with a nullable witness, rendering as a source `Struct` would emit `Field[T | None]`, which the source-field rule rejects. Whether this is intentional (groups are generation-only; computed structs are witnesses) or a lossy path is unclear.

5. **The data DTO and the field symbol disagree for computed-struct members.** The containing `StructDTO` column has `expression=None`; the field symbol built by `_field_declaration_symbol` passes `expression=True` when the descriptor has an expression, so its `ColumnDTO` carries the expression (`data/service/_private/symbols.py:173-186`; `transcription.py:118-126`). A consumer reading the declaration symbol and one reading the owner DTO see different columns for the same computed-struct member.

6. **`Pair` types are process-local.** `pair_type` builds a `Pair_<sha256[:24]>` class and registers it in `_PAIR_CLASSES` and in the `pair` module (`expressions/service/_private/pair.py:36-92`). `extract` resolves a pair type by checking the pair module and `pair_declaration(qualname)` first (`_private/selections.py:92-108`). A document decoded in a fresh process that names a pair type cannot resolve it unless `pair_type` has already regenerated the identical class. Tests only round-trip in the same process. Unclear how a persisted blueprint is expected to reconstitute pair shapes.

7. **`lookup` ignores row semantics on the key.** `lookup_value` builds `LookupExpression` without composing the key's `row_semantics` (`_private/lookup.py:105-115`), whereas `build.lookup_expression` does compose it (`_private/build.py:64-78`). The authoring path therefore drops row effects carried by a key expression. Since a key is normally a scalar in the current row this may be deliberate, but it differs from every operation constructor.

8. **`unnest` accepts more than a direct field and can silently drop row effects.** `_selected_field` accepts operation expressions with one distinct field name (`rows.py:450-460`); `derive_unnest` stores only `field` and `expression` in `RowUnnestDTO` (`463-504`), not the operation's row semantics. A selector such as `site.tags.alter_rows().drop_null()` or `.unique()` passes and its filter/dedup is not represented in the plan DTO (the expression still names the operation, so the engine may re-derive some of it). Docs say direct field only.

9. **`filters` on row sources is largely vestigial.** `RelationRowSource.plan_dto` returns a bare `RowScanDTO` and never applies `filters` (`row_sources.py:188-201`). `DerivedRowSource` stores both `filters` and `plan_dto`; every derive sets `plan_dto`, so `row_source_plan_dto`'s filter-rebuild branch (`_private/rows.py:574-588`) is only reachable for hand-built values. A manually constructed row source with filters silently loses them at plan time.

10. **Row semantics and traversals are authoring-only metadata.** `ExpressionNode` carries `row_semantics` and field reads carry `traversals`, but the expression DTO carries neither; the planner re-derives effects from operation names (`distribution/modules/core/service/_private/planning/emission.py`). Traversals have no consumer outside construction/validation in these two packages. This is consistent with "DTO carries identity, not authoring metadata" but means a DTO round-trip cannot reproduce those fields.

11. **`Table.where`/`Projection.where` produce a shape-view shape, not the declaration shape.** `_derive` calls `shape_view(declaration)` and passes it as the result shape (`data/service/_private/declarations.py:110-124`). The returned `DerivedRowSource[Self]` annotation is therefore stricter than the runtime shape. These classmethods are not documented in the row-source pages, which document `row_source().where(...)` instead.

12. **`DataLanguage` keeps discovery state on the instance/class.** `_name_counts` is a class attribute initialized to `{}` and set during `discover_declarations` (`data/service/internal/adapters/kernel_language.py`, near `class DataLanguage`). `compute_key`, `get_identity` and `get_references` read it. Two concurrent compilations sharing a `DataLanguage` instance could see one another's counts; a fresh instance per blueprint is the safe path.

13. **Two `member_name` implementations disagree.** `data._private.naming.member_name` strips one trailing underscore and snake-cases but does not sanitize keywords or invalid identifiers. `distribution.service.internal.rendering.member_name` sanitizes non-alphanumerics, leading digits and Python keywords. Class creation uses the former; data source rendering uses the latter (`data/service/_private/source.py:10, 77`). The concrete hazard is a field whose **external** name is `options`: the docs instruct the author to write the attribute `options_` (`docs/concepts/data-contracts.md` "Limits"), so class creation records external `options`; the renderer then derives the attribute from the external name via `rendering.member_name("options")`, yielding `options`, which collides with the class-level options metadata and fails re-import. The renderer cannot recover the authoring underscore. Keyword/identifier sanitization differs in the same way for other external names. This is a concrete source-generation hazard.

14. **`render_data` collapses per-key order directions.** `RowOrderByDTO.keys` stores `(expression, ascending)` per key and the codec preserves each bool, but the source renderer emits `ascending=plan.keys[0][1]` for the whole chain (`data/service/_private/source.py:166-172`). The authoring API only exposes one `ascending` argument, so this only matters for hand-built or decoded DTOs with mixed directions.

15. **`_projection` has an apparently dead `RowUnnestDTO` omission.** Its `isinstance(row_source, (RowScanDTO, ..., RowOrderByDTO))` tuple omits `RowUnnestDTO` (`transcription.py:153-160`); if a plan DTO were passed as `row_source`, it would fall through to `row_source_plan_dto`, which requires a `RowSource` value and would raise. In current authoring `spec.row_source` is always a value, so the path is likely unreachable. Marked unclear/legacy.

16. **`TableGroupOptions.members` duplicates are deduplicated before the duplicate-table check.** `entries = tuple(dict.fromkeys((*options.members, *declared.values())))` (`declarations.py:318`) means the same table listed twice in `options.members` does not trigger `a table group may include a final table only once`; that error only fires when two different catalog paths flatten to the same table (`groups.py:68-74`).

17. **`validate_data` is narrower than authoring validation.** It does not check struct name uniqueness, projection output expression presence, union shape equality, join key type consistency, group key names, or unnest field membership. Those are enforced at authoring time (`derive_*`) or by `plan_fields`, not by the DTO validator. A decoded/hand-built DTO can pass `validate_data` and still fail later in planning/emission.

18. **Date/time/timestamp/uuid literals look non-round-trippable through source.** `literal()` stores text-canonical units as canonical **text** (`_private/literals.py:75-85`), and the expression renderer emits `value_expression(<repr of text>, logical_type=DATE/TIME/TIMESTAMP/UUID)`. On re-import, `literal()` validates a `DATE` value by exact Python class (`Date`), not by canonical text (`_private/literals.py:54-72`), so the rendered string would be rejected. Same concern for array literals of those units. Tests do not cover temporal literals in source round-trip. Marked "code path indicates".

19. **The authoring surface doubles as a type-level and a runtime surface, but not consistently.** `Selection` methods use PEP 695 overloads for gating; runtime dispatch often uses `_base`/`non_nullable`, and operation specs use predicates that accept nullable bases. The result is a three-way possibility for any given call: type checker accepts, runtime accepts; type checker rejects, runtime accepts (`prepend` on nullable text); type checker accepts, runtime rejects (`add` on nullable int). This is the single most important thing for KB writers to state explicitly.

20. **`Field.expression` is a public-looking descriptor property that exposes private machinery.** It returns the `ValueExpression` (or `None` for source fields) and is used internally by transcription and symbols (`data/model/public/fields.py:111-114`; `transcription.py:109-112`). The authoring docs correctly say a `Selection` has no `.expression`, but the descriptor does; a KB article should distinguish "field descriptor internals" from "selection authoring".
