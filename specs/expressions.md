# Expressions

## Responsibility

The `expressions` package owns typed selections, bindable expression families, the immutable expression model, operation specifications, row semantics and the expression codecs.

## Public API

Names are defined in `expressions.public`; `kg_build_system.expressions` exposes only that package.

- Selection types:
  - `ValueSelection[T]`: a typed position in a row. It exposes `.model`, `.logical_type`, `.expression`, `.where_present()`, `.default_to(value)`, `.drop_if(predicate)` and `.alter_rows()`.
  - `NullableSelection[T]`: owns explicit null policy. It exposes `.default_to(value)`, `.where_present()`, `.drop_null()`, `.pick(selector)`, `.extract(selector)`, `.expand()`, the nullable array operations and `.alter_rows()`.
  - `ArraySelection[T]`: a present array. It exposes `.transform_items`, `.drop_null_items`, `.sort`, `.distinct`, `.unique`, `.join`, `.concat`, `.at`, `.slice`, `.expand` and `.alter_rows()`.
  - `StructSelection[T]`: a present struct. It exposes `.extract(selector)` and the compatibility alias `.pick(selector)`.
- Type aliases: `SelectionUnit`, `SelectionStructured`, `SelectionDataType`, `NullableDataType`; `ValueInput[T] = ValueSelection[T] | ValueExpression[T]`.
- Selection construction and normalization:
  - `as_expression(value: ValueInput[T]) -> ValueExpression[T]`
  - `select_expression(expression: ValueExpression[T]) -> ValueSelection[T]`
  - `select_member(name, logical_type, declaration) -> ValueSelection[Any]` for a temporary struct member.
- Row-effect handles:
  - `RowEffects[SSelection]` with `.selection`, `.drop_null()` and `.drop_if(predicate)`.
  - `ArrayRowEffects[TItem]` adds `.expand()`.
  - `NullableRowEffects[TItem]` adds `.drop_null()` and `.expand()`.
- Bindable expression families:
  - `ValueExpression[T]` with `.model`, `.expression`, `.logical_type` and `.to_string()`.
  - `NullableExpression[TData, TNonNullExpr]` with `.non_null_logical_type` and the compatibility text helpers `.append`, `.prepend`, `.replace`, `.equals`, `.before_separator`, `.after_separator`; their results stay nullable.
  - `NumberExpression[TNumber]`, `IntExpression` and `FloatExpression` with `.add` and `.sub`.
  - `StrExpression` with `.prepend`, `.append`, `.replace`, `.before_separator`, `.after_separator` and `.equals`.
  - `BoolExpression` with `.not_`, `.and_`, `.or_`; `any_of(*predicates)` and `all_of(*predicates)`.
  - `ArrayExpression[TItem]` with `.transform_items`, `.drop_null_items`, `.sort`, `.distinct` and `.join`.
  - `StructExpression[TStruct]` and `CustomDataTypeExpression[TCustom]` expose no operations of their own.
- Literal and wrapper functions:
  - `value_expression(value, *, logical_type: LogicalType | None = None) -> ValueExpression[Any]`
  - `literal(value, *, logical_type: LogicalType | None = None) -> LiteralExpression`
  - `wrap_expression(expression: ExpressionNode) -> ValueExpression[Any]`
- Compatibility spellings `where_present()`, `pick(...)`, `drop_null_items()`, `expand()`, `unique()` and `concat(...)` are current. `where_present()` narrows a nullable selection; `pick` aliases `extract`; see `../DESIGN_ISSUES.md` item 5.

## Internal interface

`expressions.internal` exposes:

- Domain model: `ExpressionNode`, `LiteralExpression`, `FieldReferenceExpression`, `OperationExpression`, `VariableExpression`, `Expression`, `Traversal`, `OperationParameter`, `RowEffect`, `RowSemantics`, `PRESERVE_ROWS`.
- Semantics and algebra: `compose_row_semantics`, `row_effects`, `row_semantics`, `field_reference`, `operation`, `with_arguments`.
- Visitors: `ExpressionVisitor`, `visit_expression`, `walk_expression`, `rewrite_expression`.
- Operation interface: `ArgumentSpec`, `ParameterSpec`, `RowEffectSpec`, `OperationSpec`, `OperationRegistry`, `DEFAULT_OPERATIONS`.
- Selection interface: `ValueSelection`, `NullableSelection`, `ArraySelection`, `StructSelection`, `ValueInput`, `as_expression`, `select_expression`, `select_member`.
- Typed families, literal construction, `value_expression`, `wrap_expression`, `expression_input`.
- Codecs and mapping: `encode_expression`/`decode_expression` for the domain model, `encode_expression_ir`/`decode_expression_ir` for IR, `expression_to_ir`.

Invariants:

- `ExpressionNode` is frozen and carries `logical_type` and `row_semantics`.
- `FieldReferenceExpression.source` is the logical relation key; `path` is non-empty; each `Traversal.path` is a prefix of the field path.
- `OperationExpression.operator` is non-empty; parameter names are unique and sorted; arguments are canonical expression nodes.
- `VariableExpression.name` is non-empty.
- `RowSemantics` modes are `preserve`, `expand` and `filter`. Only `expand` may carry a scope, and its scope must be non-empty. A non-expand mode may not carry a scope. Preserve may not carry upstream effects.
- `OperationSpec` states name, arity (fixed or range), argument specs, parameter specs, result type, row effect, optional last-argument repetition and optional argument validation.
- `OperationRegistry` is immutable and keyed by operation name; `register` returns a new registry.

## IR

`expressions.internal.ir` owns the expression IR.

- `ExpressionIRBase(logical_type)`.
- `LiteralExpressionIR(value)`.
- `VariableExpressionIR(name)`.
- `FieldReferenceExpressionIR(source, path)`.
- `OperationParameterIR(name, value)`.
- `OperationExpressionIR(operator, arguments, parameters=())`.
- `ExpressionIR = LiteralExpressionIR | VariableExpressionIR | FieldReferenceExpressionIR | OperationExpressionIR`.
- `walk_expression_ir(expression)` yields a deterministic pre-order traversal.
- `expression_to_ir` lowers the domain model. IR stores the operator name, arguments, parameters and logical type; it stores no concrete operation and no authoring `RowSemantics`. Field traversals are authoring facts and are not stored in the expression IR.
- `encode_expression_ir`/`decode_expression_ir` use a canonical object keyed by `kind`: `literal`, `variable`, `field`, `operation`. Decoding refuses an unknown kind, a missing logical type and an invalid path.
- `encode_expression`/`decode_expression` round-trip the domain model, including row effects and field traversals.

## Boundaries

- Allowed dependencies: `types.internal`, `types.internal.ir` and `_frozen_json`.
- Must not import `table`, `topology`, `binding`, `relational`, `compile`, `engines`, `workflow`, `modules`, `code_generation`, `api` or `cli`.
- `table` and `binding` construct selections by reading declared fields; `relational` consumes expression IR and derives relation effects; `engines` lowers expression IR to SQL. Those consumers never import an expression implementation module.
- Surfaces: `kg_build_system.expressions` exposes only `expressions.public`; `expressions.public` is the author-facing selection and expression surface; `expressions.internal` is the model, operations and codecs; `expressions.internal.ir` is the expression IR; mechanisms are in `expressions._private`.
- Row-source algebra belongs to `table`; relation planning belongs to `relational`.

## Current decisions

### Selection and expression split

- **Selections navigate; expressions calculate.** A selection is a typed position in a row and exposes `.expression` to reach the bindable calculation. A `ValueExpression` is a calculation and owns no null policy.
- **Access typing belongs to the declaration.** A source field yields the selection matching its declared type; a computed field yields the selection matching its expression type. A nullable value yields `NullableSelection`; a present array yields `ArraySelection`; a present struct yields `StructSelection`.
- **`as_expression` is the boundary.** It accepts a selection or an expression. Expression methods accept a Python literal or a `ValueExpression`, never a selection; write `.expression` or `as_expression(...)` to combine one.
- **Present selections have compatibility no-ops.** `ValueSelection.where_present()` and `ValueSelection.default_to(value)` return the present selection unchanged.

### Struct navigation

- **`extract` reads one declared member.** `StructSelection.extract(selector)` and `NullableSelection[Struct].extract(selector)` pass a symbolic instance of the struct declaration to the selector. The selector must return a declared field selection from that declaration.
- **`pick` is the compatibility spelling** of `extract`; both are current.
- **Member selections are temporary.** Reading a struct member outside `extract` creates a member selection that refuses to become an expression with `a struct member selection is only valid inside extract`.
- **Nullability composes.** A nullable parent makes every extracted member nullable. A present parent leaves a computed member at its expression type; a source member keeps its declared nullability. Selecting an already-nullable member does not add a second nullable layer.
- **Nested extracts compose.** A chain over a field reference resolves to one field path; a chain over an operation result lowers to a `struct_field` operation. `extract` changes no row count.
- **Generated records select like declared structs.** The record shapes produced by `join` and `group_by` are `Struct` value records navigated with `extract`.

### Null policy

- **`default_to(value)` replaces a null and keeps the row.** It applies to a nullable selection, returns the matching present selection and requires a fallback of the member's logical value type.
- **`drop_null()` removes a null by removing the row.** It applies to a nullable selection and produces a present scalar, array or struct. `where_present()` is the compatibility spelling.
- **`drop_if(predicate)` filters by this value.** The predicate receives the selection and must return a `BoolExpression`. The row survives when the predicate is true; a false or null result drops it. The selection type and nullability do not change.
- **`where` is the row-source filter.** It receives a symbolic row shape, not one value, and keeps rows whose predicate is true.

### `alter_rows` and row effects

- **`alter_rows()` is the one-shot gate.** It returns `RowEffects`, `ArrayRowEffects` or `NullableRowEffects`. Each handle method returns a selection, never another handle, so a second row effect requires a second `alter_rows()` call.
- The direct methods `ValueSelection.drop_if`, `NullableSelection.drop_null`/`where_present` and `ArraySelection.expand` also exist. `alter_rows()` makes the row change explicit.
- **Available effects:** `drop_if(predicate)` on every selection; `drop_null()` on a nullable selection; `expand()` on a present or nullable array.
- **Effects are scoped to a product.** A projection or binding has one row plan. An effect required by any of its expressions applies to the whole product, never to a sibling product.
- **`drop_null` is a presence filter.** It lowers to a `present` filter; `drop_if` and row-source `where` lower to held-true predicates. A null predicate drops the row.
- **`expand` is the only row-producing operation.** It yields one row per item; a null or empty array yields none. Item nullability is preserved. Identical expansion scopes share one fan-out; unrelated expansions multiply rows.

### Array operations

- **`transform_items(selector)`** applies one expression to every item without expanding rows. A struct item selector receives a `StructSelection`; a scalar item selector receives a `ValueExpression`. Item nullability is preserved and the selector may not contain a row effect.
- **`drop_null_items()`** removes null items and preserves whether the array itself is present. It is the explicit conversion for an array that must become a graph property.
- **`sort()`** orders items ascending. **`distinct()`** keeps one copy per item; **`unique()`** is the selection spelling of `distinct`.
- **`join(separator)`** concatenates non-null string items; **`concat(separator)`** is the selection spelling of `join`. An array with nullable items is refused.
- **`at(index)`** is 0-based and returns a nullable item selection; an out-of-bounds index yields null. **`slice(start, end)`** is 0-based and end-exclusive and returns the same array type.
- `ArrayExpression` mirrors the value operations: `transform_items`, `drop_null_items`, `sort`, `distinct` and `join`. There is no row effect on `ArrayExpression`.

### Scalar operations

- **`to_string()` is the key-material operation.** Every canonical scalar unit has one text form: bool, int, float, str, date, time, timestamp and uuid. A nullable scalar yields a nullable text expression. Arrays, structs and custom scalars are refused.
- **Text:** `prepend`, `append`, `replace`, `before_separator`, `after_separator` and `equals`.
  - `before_separator` returns the text before the nth occurrence (the whole string when absent).
  - `after_separator` returns the text after it, keeping later separators (the empty string when absent).
  - The separator at the cut is excluded by default; `include_separator=True` keeps it on the result side.
  - The separator must be non-empty and `occurrence` must be at least 1.
- **Numbers:** `add` and `sub` only, on `IntExpression` and `FloatExpression`. There is no multiplication, division or numeric comparison.
- **Booleans:** `not_`, `and_`, `or_`. `any_of()` is false and `all_of()` is true for an empty argument list. `where` and `drop_if` keep only a true result.
- **Nullable text compatibility:** `NullableExpression` exposes `append`, `prepend`, `replace`, `equals`, `before_separator` and `after_separator`; every result remains nullable. It exposes no typed numeric or array operations.
- **Temporal, uuid, custom and struct values:** date, time, timestamp and uuid use the generic `ValueExpression` and expose only `to_string()`. `CustomDataTypeExpression` and `StructExpression` expose no operations; struct navigation is a selection concern.
- **Literal coercion is narrow.** An operation accepts a Python value or a `ValueExpression` of its expected type. An integer literal is recorded as a float where a float is expected; no other implicit conversion exists.

### Literals and expression algebra

- `value_expression` infers the logical type from the exact Python class. `bool` and `int` are distinct; `Date`, `Time`, `Timestamp` and `Uuid` are their stdlib classes.
- A null literal, an empty array literal and an all-null array literal require an explicit canonical `logical_type`. A struct or custom-type value cannot be embedded as a literal.
- Array literals must be homogeneous. A null item makes the item type nullable; mixed item types are refused.
- Text-canonical units are frozen as canonical text: ISO text for date, time and timestamp, with `T` for timestamps, and lowercase hyphenated text for uuid.
- Nodes are immutable. `OperationExpression` stores sorted, uniquely named parameters. `with_arguments` returns the same object when the arguments are unchanged.
- Every operation's row semantics are the argument effects in order, followed by its own local effect. Identical `expand` effects with the same scope are shared; filtering effects remain ordered.
- `RowEffect` is `("expand", scope)` or `("filter", scope)`; an expand scope must be non-empty and a filter scope must be empty. `row_semantics(effects)` rebuilds the one `RowSemantics` those effects denote.
- Expansion scope is stable. A field-reference expansion scopes by `(source, *path)`. A struct member under an expansion extends that scope with the member name. Any other expansion uses a content-derived identity.

### Operations and planning boundary

- **One file per operation.** Each operation has one `expressions/internal/operations/<name>.py` module with one `OperationSpec`; the default registry composes those specs and rejects duplicate names. Adding a built-in operation is one spec file plus one registry entry, not a dispatcher branch.
- `OperationSpec.apply` validates arity, parameters and argument types, resolves the result type, composes row semantics and returns the matching authoring expression family.
- **One driving source per product.** `relational.lower_product` collects the logical sources referenced by outputs and predicates, requires one materialised relation for each and rejects more than one. Additional sources must already be present in the row source; there is no implicit cross product.
- **Plans are engine-neutral.** `RelationPlanIR` records scans, explicit expansions, presence or held-true filters and named outputs. SQL lowering is an engine concern.
- **Effects are explicit in IR.** Expansion and filtering are operations in the expression tree; the planner derives relation effects from those operations. Equal effects share one plan step; unrelated expansions multiply rows.
- `lower_product`, `RelationPlanIR`, `expansion_scope` and the plan lowerer protocols belong to `relational`, not `expressions`.
