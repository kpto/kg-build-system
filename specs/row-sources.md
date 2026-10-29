# Row sources

## Responsibility

Owns the authoring row-source algebra and its plan IR: the row value a projection or binding reads, and the operations that derive a new row set.

## Public interface

### Entry points

- `Table.row_source() -> RelationRowSource[Table]`: shape is the `Table` class; source is the table.
- `Projection.row_source() -> RelationRowSource[Any]`: shape is `Projection.shape`; source is the `Projection` class.
- `Table.where(predicate)` and `Projection.where(predicate)`: classmethod shorthands returning a `DerivedRowSource` with the declaration's fields.
- `RowSource[S]`: generic row-source base with `shape: type[S]`. `Table` and `Projection` satisfy it as class objects by subclassing; `RelationRowSource` and `DerivedRowSource` are values.
- `as_row_source(value) -> RowSource[Any]`: accepts only a row-source value. A class or other value raises `TypeError("rows must be a row source value; use Table.row_source() or Projection.row_source()")`.
- `shape_context(shape) -> S`: a symbolic instance passed to authoring callables (`where`, `join`, `group_by`, `order_by`, `bind`); it carries no row data.

### Operations

- `where(predicate: Callable[[S], BoolExpression]) -> DerivedRowSource[S]`
  - `predicate` must be callable and must return a `BoolExpression`; a bare expression raises `TypeError`.
  - Adds one filter; chaining accumulates filters.
  - Preserves the row shape's fields and types.
  - `row_source().where` keeps the original shape object; `Table.where` and `Projection.where` use a generated shape view of the declaration's fields.
- `union(other, *, all=True) -> DerivedRowSource[S]`
  - `other` must be a row-source value with the same shape signature: external field names and logical types.
  - Different shapes raise `TypeError("union row sources must have the same shape")`.
  - `all=True` keeps duplicates; `all=False` removes duplicate rows.
  - Preserves `self.shape`.
- `join(other, *, on, how="inner") -> DerivedRowSource[Any]`
  - `other` must be a row-source value.
  - `on` is callable and receives one shape instance per side. It returns `(left_key, right_key)` or one `equals` expression with two arguments. `equals` is available on text expressions only.
  - Keys must be scalar expressions with the same non-null base type; their nullability may differ. Array and struct keys are refused.
  - `how` is one of `inner`, `left`, `right`, `full`; anything else raises `ValueError`.
  - Produces the generated shape `{on, left, right}` described below.
- `group_by(*, by) -> DerivedRowSource[Any]`
  - `by` is callable and returns one value input (named `key`), a mapping of names to inputs, or a sequence of `(name, input)` pairs.
  - Key names must be public Python identifiers and unique; at least one key is required; keys must be scalar.
  - Produces the generated shape `{by, members}` described below.
  - Drops every row whose key tuple contains a null; no null key groups rows.
- `distinct() -> DerivedRowSource[S]`: removes duplicate rows; preserves shape.
- `order_by(*keys, ascending=True) -> DerivedRowSource[S]`
  - Requires at least one key; otherwise `ValueError`.
  - A key is an external column name, a callable receiving the shape, or a value expression.
  - A name not present in the shape raises `ValueError`; a non-expression raises `TypeError`.
  - One `ascending` flag applies to every key; preserves shape.

### Models

- `RelationRowSource[S]` (frozen dataclass): `source: type`, `shape: type[S]`, `filters: tuple[BoolExpression, ...] = ()`; `plan_ir` is `RowScanIR(declaration_source_name(source))`; `projection_base()` returns a projection base.
- `DerivedRowSource[S]` (frozen dataclass): `shape: type[S]`, `source: type`, `filters: tuple[BoolExpression, ...] = ()`, `plan_ir: RowSourcePlanIR | None = None`; `projection_base()` returns a projection base. `source` is the root declaration for diagnostics; `plan_ir` is the canonical plan.
- `declaration_source_name(source) -> str`: the logical relation name from `_table_name` or `_projection_name`; otherwise `TypeError("row sources must be a Table or Projection")`.
- `ShapeField(attribute, name, logical_type)`: one row-shape member, with Python attribute, external name and logical type.
- `shape_fields(shape) -> tuple[ShapeField, ...]` and `shape_source_name(shape) -> str`: read declared fields and access types, or generated row-shape fields; a class that is not a row shape with a logical source raises `TypeError`.
- `make_row_shape(source_name, fields, *, allow_empty=False)`, `record_shape(fields)`, `record_shape_type(fields)`, `union_shape_fields(left, right)`, `projection_attrs(shape)`.
  - `make_row_shape` requires at least one field unless `allow_empty`; attributes must be public Python identifiers; duplicate attributes are refused.
  - Generated row-shape class names and generated record identities are content-derived; equal members and types produce the same name and record identity in authoring and in a decoded blueprint.
- `row_source_plan_ir(value)`, `row_source_key(plan)`, `plan_shape_source_name(plan)`, `plan_inputs(plan)`, `plan_scan_sources(plan)`, `plan_expressions(plan)`, `plan_fields(plan, declarations)`, `retarget_expression_ir(expression, mapping)`.

### Generated shapes

- `join` produces exactly `{on, left, right}`:
  - `on` is the join key, typed from the common base key type. It is non-null for `inner`; for `left` it is nullable when the left key is nullable, for `right` when the right key is nullable, and for `full` when either is nullable.
  - `left` is a generated record mirroring the left input row. It is nullable for `right` and `full`, and non-null for `inner` and `left`.
  - `right` is a generated record mirroring the right input row. It is nullable for `left` and `full`, and non-null for `inner` and `right`.
  - `left` and `right` are records, not row sources; read their members with `extract`.
- `group_by` produces exactly `{by, members}`:
  - `by` is a generated record holding the named key expressions; key fields are non-null.
  - `members` is an array of generated records mirroring the input row; item order is unspecified; item nullability follows the input row.
- Both generated results are `DerivedRowSource[Any]` at edit time; their members are typed at runtime. Input-shaped `where`, `union`, `distinct` and `order_by` results keep the input shape.
- A generated row shape reads its fields from the plan's logical key: `row_source_key(plan)`. The generated record identity is a pure function of its members, so a decoded blueprint computes the same identity without the authoring class.

### Plan IR

- `RowSourcePlanIR = RowScanIR | RowFilterIR | RowUnionIR | RowJoinIR | RowGroupByIR | RowDistinctIR | RowOrderByIR`.
- `RowScanIR(source: str)`: reads one table or projection logical name. A scan carries no filters; its `filters` property is always empty.
- `RowFilterIR(input, predicate)`.
- `RowUnionIR(left, right, all: bool = True)`.
- `RowJoinIR(left, right, left_key, right_key, how: JoinHow = "inner")`.
- `RowGroupByIR(input, keys: tuple[tuple[str, ExpressionIR], ...])`.
- `RowDistinctIR(input)`.
- `RowOrderByIR(input, keys: tuple[RowOrderKeyIR, ...])`; `RowOrderKeyIR(expression, ascending: bool = True)`.
- `JoinHow = Literal["inner", "left", "right", "full"]`.
- Invariants: plans are frozen; scans name declared tables or projections; a filter predicate, group key and order key reference the input plan's logical shape key; join keys reference their own side's plan key; union operands have the same shape; join keys have the same scalar base type; group keys are non-empty and uniquely named; order keys are non-empty.
- `encode_row_source_plan(plan)` and `decode_row_source_plan(value)` use a canonical JSON object keyed by `kind` (`scan`, `filter`, `union`, `join`, `group_by`, `distinct`, `order_by`). Decoding refuses an unknown kind or join mode and returns an equal plan for every encoded plan.
- `row_source_key(plan)` is the scan source name for `RowScanIR`, otherwise `derived:<24 hex>` from the canonical plan encoding. The key is stable across a codec round-trip and identical for equal plans.
- `plan_fields(plan, declarations)` derives the row shape from the IR alone; a scan must name a known logical source, union operands must agree, and join keys must agree. `plan_inputs` returns direct child plans; `plan_scan_sources` returns every leaf scan; `plan_expressions` returns the filter predicate, join keys, group keys or order keys owned by one node.
- `plan_shape_source_name(plan)` returns the input's name for `filter`, `distinct` and `order_by`, the left input for `union`, and `row_source_key(plan)` otherwise.

## Boundaries

- `table.rows` may import `expressions` (authoring, `expressions.ir`, `expressions.mapping`), `types` (logical types, `types.ir`, `types.mapping`, `types.ir_codec`), and the local `table.fields`, `table.ir` and `table.ir_codec` interfaces.
- `table.rows` must not import `binding`, `topology`, `compile`, `relational`, `engines`, `workflow`, `modules`, `code_generation`, `cli` or `api`.
- `table.rows` must not import `table.models` at module load. `table.models` imports `table.rows`; the reverse edge is the lazy import inside `RelationRowSource.projection_base()` and `DerivedRowSource.projection_base()`.
- `binding`, `compile`, `engines`, `modules` and `table.models` may import `table.rows`; the dependency direction is into `table`.
- The plan IR is engine-neutral. No SQL, engine relation names, workflow artifact names or graph records appear in it.
- From this module, the authoring surface re-exports `RowSource`, `RelationRowSource` and `DerivedRowSource`; the plan helpers and generated-shape helpers are the internal interface for consuming subpackages.

## Current decisions

- A row source is a value. A declaration class is not accepted where a row source is required; call `.row_source()`.
- A row shape is the type of one row, never a schema instance or dictionary. Reading a member produces a typed selection.
- Shape-preserving operations are `where`, `union`, `distinct` and `order_by`: they keep the row shape and the grain, and `union` stacks same-shaped row sets. `join` combines two row sets; `group_by` produces one row per distinct non-null key tuple. Only `join` and `group_by` generate members.
- `union` compares shapes structurally: external names and logical types, not class identity.
- A null key never matches in any join mode. `group_by` drops rows whose key tuple contains a null before grouping.
- Outer-join nullability is a property of the generated shape: only the side that can be unmatched becomes nullable, and `on` becomes nullable only when its source key can be null on such a side.
- A filter, group or order expression is retargeted to its input plan's logical key; a join key is retargeted to its own side's plan key. The plan is stored once and consumers read the keyed relation; the same plan content yields the same key.
- `order_by` has one direction for all keys; order is only observable through a later ordering or a materialised relation.
- `group_by` has no aggregates and no guaranteed member order. `join` has no non-equi predicate or multi-key form.
- Row effects such as `drop_null` and `expand` remain expression-level; a presence filter is an internal operation, not an authoring row-source method. A row source has no separate predicate field; the `filters` tuple records authoring predicates for a `where` chain, and `plan_ir` is the canonical source.
