# expressions

## Responsibility

The `kg_build_system.expressions` package owns typed selections, bindable expression families, the immutable expression model and its compilation IR, and the row semantics those expressions carry into relational planning.

## Public interface

- Selection types:
  - `ValueSelection[T]` — a typed position in a row; `.logical_type`, `.expression`, `.alter_rows()`, `.drop_if(predicate)`.
  - `NullableSelection[T]` — owns null policy; `.default_to(value)`, `.drop_null()`, `.extract(selector)`.
  - `ArraySelection[T]` — a present array; `.transform_items`, `.drop_null_items`, `.sort`, `.unique`, `.concat`, `.at`, `.slice`, `.expand`.
  - `StructSelection[T]` — a present struct; `.extract(selector)`.
- Type aliases: `SelectionUnit`, `SelectionStructured`, `SelectionDataType`, `NullableDataType`, `ValueInput[T] = ValueSelection[T] | ValueExpression[T]`.
- Selection construction and normalization:
  - `as_expression(value: ValueInput[T]) -> ValueExpression[T]`
  - `select_expression(expression: ValueExpression[T]) -> ValueSelection[T]`
  - `select_member(name, logical_type, declaration) -> ValueSelection[Any]` for the temporary member returned by a struct selector.
- Row-effect handles:
  - `RowEffects[SSelection]` with `.selection` and `.drop_if(predicate)`.
  - `ArrayRowEffects[TItem]` adds `.expand()`.
  - `NullableRowEffects[TItem]` adds `.drop_null()` and `.expand()`.
- Bindable expression families:
  - `ValueExpression[T]` — `.model`, `.logical_type`, `.to_string()`.
  - `NullableExpression[TData, TNonNullExpr]` — no null policy and no typed operations; `.non_null_logical_type`.
  - `NumberExpression[TNumber]`, `IntExpression`, `FloatExpression` — `.add`, `.sub`.
  - `StrExpression` — `.prepend`, `.append`, `.replace`, `.before_separator`, `.after_separator`, `.equals`.
  - `BoolExpression` — `.not_`, `.and_`, `.or_`; `any_of(*predicates)`, `all_of(*predicates)`.
  - `ArrayExpression[TItem]` — `.transform_items`, `.drop_null_items`, `.sort`, `.distinct`, `.join`.
  - `StructExpression[TStruct]`; `CustomDataTypeExpression[TCustom]` — no operations of their own.
- Literal and wrapper functions:
  - `value_expression(value, *, logical_type: LogicalType | None = None) -> ValueExpression[Any]`
  - `literal(value, *, logical_type: LogicalType | None = None) -> LiteralExpression`
  - `wrap_expression(expression: ExpressionNode) -> ValueExpression[Any]`
- Domain expression model:
  - `ExpressionNode(logical_type, row_semantics)`.
  - `LiteralExpression(value)`, `FieldReferenceExpression(source, path, traversals)`, `OperationExpression(operator, arguments, parameters)`, `VariableExpression(name)`.
  - `Traversal(kind, path)` where `kind` is `"struct"` or `"array"`.
  - `OperationParameter(name, value)`.
  - `RowEffect(mode, scope)` and `RowSemantics(mode, scope, upstream)`; `PRESERVE_ROWS`.
  - `Expression = LiteralExpression | FieldReferenceExpression | OperationExpression | VariableExpression`.
- Expression algebra helpers:
  - `compose_row_semantics(*expressions, local=PRESERVE_ROWS) -> RowSemantics`.
  - `field_reference(*, source, path, logical_type, traversals=(), row_semantics=PRESERVE_ROWS)`.
  - `operation(operator, *arguments, logical_type, parameters=None, row_semantics=PRESERVE_ROWS)`.
  - `walk_expression(expression)`, `visit_expression(expression, visitor)`, `rewrite_expression(expression, transform)`, and the `ExpressionVisitor` protocol.
- Compilation IR in `expressions.ir`:
  - `ExpressionIRBase`, `LiteralExpressionIR`, `VariableExpressionIR`, `FieldReferenceExpressionIR`, `OperationExpressionIR`, `OperationParameterIR`; `ExpressionIR` is their union.
  - `walk_expression_ir(expression)`.
  - `expression_to_ir(expression) -> ExpressionIR`.
  - `encode_expression_ir` / `decode_expression_ir` for the IR; `encode_expression` / `decode_expression` for the domain model.
- Relational boundary:
  - `lower_product(outputs: Mapping[str, ExpressionIR | ExpressionNode], relations: Mapping[str, str], *, predicates: tuple[ExpressionIR, ...] = ()) -> RelationPlanIR`.
  - `RelationPlanIR(scans, expands, filters, outputs)`, `ScanIR(source, relation, alias)`, `ExpandIR(scope, expression, alias)`, `FilterIR(expression, mode)` where `mode` is `"present"` or `"true"`.
- Errors are `TypeError` or `ValueError`. Selection misuse names the required shape or the required row gate.

## Boundaries

- Allowed dependencies: `types` and the shared frozen-JSON kernel. The expression IR additionally depends on `types.ir`.
- Must not import `table`, `topology`, `binding`, `compile`, `workflow`, `relational`, `engines`, `modules`, `code_generation`, `api` or `cli`.
- Authoring wrappers and the expression IR are distinct surfaces. Consumers that compile or plan bind to `expressions.ir`; the mapping from wrappers to IR is one way, and an IR value never retains a wrapper or a `RowSemantics`.
- `table` and `binding` construct selections by reading declared fields; `relational` consumes expression IR and row semantics. `expressions` does not know about relations, declarations, graph components or SQL.
- Surfaces: `kg_build_system.expressions` is the author-facing selection surface; `expressions.interfaces` is the expression model, operations and codecs; `expressions.ir` is the expression IR.
- Row-source algebra belongs to `table`; it uses expression values to build a plan but is not part of this package's interface.

## Current decisions

### Selection and expression split

- **Selections navigate; expressions calculate.** A selection is a typed position in a row, owns structure and null policy, and exposes `.expression` to reach the bindable calculation. A `ValueExpression` is a calculation with no null policy of its own.
- **Access typing belongs to the declaration.** A source field yields `NullableSelection[T]`; a computed field yields the selection matching its expression's logical type. A nullable expression yields `NullableSelection`; a non-null array yields `ArraySelection`; a non-null struct yields `StructSelection`.
- **Nullable expressions are terminal.** `NullableExpression` exposes neither the typed operations of its non-null family nor a narrowing method. A nullable value must be narrowed at the selection with `alter_rows().drop_null()` or `default_to(...)` before a typed operation.
- **`as_expression` is the boundary.** It accepts a selection or an expression and returns the bindable expression. Expression methods accept a Python literal or a `ValueExpression`, never a selection; write `.expression` or `as_expression(...)` to combine a selection.

### Struct navigation with `extract`

- **`extract` reads one declared member.** `StructSelection.extract(selector)` and `NullableSelection[Struct].extract(selector)` pass a symbolic instance of the struct declaration to the selector. The selector must return a declared field selection from that declaration; another value is rejected.
- **Member selections are temporary.** Reading a struct member outside `extract` creates a member selection that refuses to become an expression with `a struct member selection is only valid inside extract`.
- **Nullability composes.** A nullable parent makes every extracted member nullable. A present parent leaves a computed member at its expression type; a source member remains nullable in its own right. Selecting an already-nullable member does not add a second nullable layer.
- **Nested extracts compose.** A chain of `extract` calls resolves to one field path when the parent is a field reference, and to a struct-field operation when the parent is an operation result. `extract` changes no row count and adds no null handling of its own.
- **Generated records select like declared structs.** The record shapes produced by `join` and `group_by` are `Struct` value records and are navigated with `extract`.

### Null policy

- **`default_to(value)` replaces a null and keeps the row.** It applies only to a nullable selection, returns the matching non-null selection, and requires a fallback of the member's exact logical value type. A wrong fallback is rejected when the binding or projection is declared.
- **`drop_null()` removes a null by removing the row.** It applies only to a nullable selection, produces a non-null scalar, present array or present struct, and is an explicit row effect.
- **`drop_if(predicate)` filters by this value.** The predicate receives the selection itself and must return a `BoolExpression`. The row survives when the predicate is true; a false or null result drops it. The selection's type and nullability do not change.
- **`where` is the row-source filter.** It receives the symbolic row shape, not one value, and keeps rows whose predicate is true.

### `alter_rows` and row effects

- **`alter_rows()` is the one-shot gate.** It returns `RowEffects` for a scalar selection, `ArrayRowEffects` for a present array, and `NullableRowEffects` for a nullable selection. Each handle method returns a selection, never another handle, so a second row effect requires a second `alter_rows()` call.
- The direct methods `ValueSelection.drop_if`, `NullableSelection.drop_null` and `ArraySelection.expand` also exist. `alter_rows()` is the surface that makes the row change visible and is the form the authoring API documents.
- **Available effects:**
  - `drop_if(predicate)` on every selection.
  - `drop_null()` on a nullable selection.
  - `expand()` on a present array or on a nullable array through its handle; an absent or empty array contributes no rows either way.
- **Effects are scoped to a product.** A projection or binding has one row plan. Any effect required by one of its expressions applies to that whole product and never to a sibling product.
- **`drop_null` is a presence filter.** It lowers to a `present` filter; `drop_if` and row-source `where` lower to held-true predicates. A null predicate drops the row.
- **`expand` is the only row-producing operation.** `drop_null` and `drop_if` remove rows; `default_to`, array operations and scalar operations preserve the row count.

### Array operations

- **A nullable array has no array operations.** Narrow it with `alter_rows().drop_null()` or `default_to([])` to obtain a present `ArraySelection`.
- **`expand()`** yields one row per item. A null or empty array yields zero rows. Item nullability is preserved: expanding `Array[T | None]` yields a nullable item selection. Two unrelated expansions multiply; identical expansions share one fan-out.
- **`transform_items(selector)`** applies one expression to every item without expanding rows. A struct item selector receives a `StructSelection`; a scalar item selector receives a `ValueExpression`. The result preserves item nullability. The selector may not contain a row effect.
- **`drop_null_items()`** removes null items and returns an array with non-null items. It preserves whether the array itself is present. It is the explicit conversion for an array that must become a graph property.
- **`sort()`** orders items ascending. **`unique()`** keeps one copy per item and is the selection spelling of the `distinct` array operator.
- **`concat(separator)`** joins non-null string items. It requires an `Array[str]`; an array whose items may be null is refused, and an empty array yields `""`.
- **`at(index)`** is 0-based. It returns a nullable item selection; an out-of-bounds index yields null. **`slice(start, end)`** is 0-based and end-exclusive and returns the same array type.
- **`ArrayExpression` mirrors the value operations.** It adds `transform_items`, `drop_null_items`, `sort`, `distinct` and `join`; `join` requires non-null string items. There is no `distinct` or `join` method on `ArraySelection`; the selection names are `unique` and `concat`.

### Scalar operations

- **`to_string()` is the key-material operation.** Every canonical scalar unit has one text form: bool, int, float, str, date, time, timestamp and uuid. A nullable scalar yields a nullable text expression. Arrays and structs are refused.
- **Text:** `prepend(value)`, `append(value)`, `replace(search, replacement)`, `before_separator(separator, occurrence=1, *, include_separator=False)`, `after_separator(...)`, and `equals(value)`.
  - `before_separator` returns the text before the nth occurrence (the whole string when absent).
  - `after_separator` returns the text after it, keeping later separators (the empty string when absent).
  - The separator at the cut is excluded by default; `include_separator=True` keeps it on the result side.
  - The separator must be non-empty and `occurrence` must be at least 1.
- **Numbers:** `add` and `sub` only, on `IntExpression` and `FloatExpression`. There is no multiplication, division or numeric comparison.
- **Booleans:** `not_`, `and_`, `or_`. `any_of()` is false and `all_of()` is true for an empty argument list. Combinations follow three-valued logic; a `where` or `drop_if` keeps only a true result.
- **Temporal, uuid, custom and struct values:** date, time, timestamp and uuid use the generic `ValueExpression` and expose only `to_string()`. `CustomDataTypeExpression` and `StructExpression` expose no operations; struct navigation is a selection concern, not an expression operation.
- **Literal coercion is narrow.** An operation accepts a Python value or a `ValueExpression` of its expected type. An integer literal is recorded as a float where a float is expected; no other implicit conversion exists.

### Literals

- `value_expression` infers the logical type from the exact Python class. `bool` and `int` are distinct; `Date`, `Time`, `Timestamp` and `Uuid` are their stdlib classes.
- A null literal, an empty array literal, and an all-null array literal require an explicit canonical `logical_type`. A struct or custom-type value cannot be embedded as a literal.
- Array literals must be homogeneous. A null item makes the item type nullable; mixed item types are refused.
- Text-canonical units are frozen as their canonical text: ISO text for date, time and timestamp, with `T` for timestamps, and lowercase hyphenated text for uuid.
- `literal` is the model constructor; `wrap_expression` returns the most specific family for a model. The generic `ValueExpression` is used for temporal and uuid units because they have no typed operations.

### Expression algebra

- **Nodes are immutable.** `ExpressionNode` carries a logical type and row semantics. `OperationExpression` stores its arguments and sorted, uniquely named parameters; the `with_arguments(expression, arguments)` function returns the same object when the arguments are unchanged.
- **Field references carry a path.** `FieldReferenceExpression` stores the logical source, the path within it, and optional `Traversal` segments. Every traversal path is a prefix of the field path. A traversal marks a structured or array-valued segment; it is an authoring and planning fact.
- **Operations compose argument effects.** Every operation's row semantics are the argument effects in order, followed by its own local effect. Identical `expand` effects with the same scope are shared; filtering effects remain ordered.
- **`RowEffect`** is `("expand", scope)` or `("filter", scope)`; an expand scope must be non-empty and a filter scope must be empty.
- **`RowSemantics`** is `"preserve"`, `"expand"` or `"filter"` plus an optional scope and upstream effects. Only expand may declare a scope; preserve may not carry upstream effects. `PRESERVE_ROWS` is the no-effect value, and `from_effects` rebuilds the same ordered form.
- **`expand` scope is stable.** A field-reference expansion scopes by `(source, *path)`. A struct member under an expansion extends that scope with the member name. Any other expansion uses a content-derived identity. Equal scopes share one expansion; nested scopes are planned parent-first; unrelated scopes multiply rows.
- **The compiled IR carries explicit row effects.** The IR preserves logical type, source, path, operator and parameters, and records expansion and presence filtering as operations. Authoring row-semantics objects are not stored in the IR; the planner derives the relation effects from the explicit operations.
- **The IR is immutable and codec-stable.** Domain expressions and IR nodes are frozen; `encode_expression_ir` and `decode_expression_ir` round-trip only IR values.

### Row planning boundary

- **One driving source per product.** `lower_product` collects the logical sources referenced by the outputs and predicates, requires one materialised relation for each, and rejects more than one source. Additional sources must already be present in the row source; there is no implicit cross product.
- **Plans are engine-neutral.** `RelationPlanIR` records scans, explicit expansions, presence or held-true filters, and named outputs. SQL lowering is outside this specification.
- **Effect identity.** Expansions and filters are deduplicated by their content identity, so equal effects share one plan step; unrelated expansions multiply rows. A filter is applied once per product, whatever the number of expressions that require it.
- **Plan identity.** Expansion scope and filter identity are content-derived, so two expressions that require the same effect share one plan step. A product's plan is independent of every other product.
