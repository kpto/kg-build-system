# Projections

## Responsibility

Owns the named, pinned relation declaration: its row-source pin, its computed output fields and the output references other declarations read.

## Public interface

### Declaration

- `Projection` is a `Shape` and a `RowSource["Projection"]`, with metaclass `ProjectionMeta`.
- `Projection(source.row_source())` is the required pin. `ProjectionMeta.__call__(cls, source)` returns a dynamic pinned base; it does not construct an instance.
- The pin is a row-source value: `Table.row_source()`, `Projection.row_source()` or a derived row source. A declaration class is not a row source.
- `class P(Projection)` without a pinned base raises `TypeError("P must be pinned to a row source: Projection(source.row_source())")`.
- A final projection must have at least one effective output declared with `computed_field`; no effective output raises `TypeError("projections must declare at least one computed_field")`.
- `field()` in a projection is rejected; outputs are expression-backed.
- A final `Projection` may not inherit from another final `Projection`. Reuse is through `projection_base()` or a new pin.
- `ProjectionOptions(name=None, description=None, annotations=())`: `name` defaults to the class name with one trailing `Projection` removed and snake-cased; `description` defaults to the class docstring; annotations are portable metadata.
- A projection's logical name must be unique among tables and projections.
- `Projection.shape` is a generated `Shape` view carrying the projection's fields. The `Projection` class itself is the row-source declaration; `Projection.row_source()` uses `cls.shape`.

### Outputs

- `computed_field(value, *, name=None, description=None, annotations=()) -> Field[T]` declares one output.
  - `value` is a value selection or expression; a literal must be wrapped in `value_expression`.
  - The output's logical type is the expression's type, including nullability.
  - `name` is the external field name and defaults to the Python attribute in snake case; two outputs may not share an external name.
  - `description` and `annotations` are carried to the IR.
- Reading `P.output` returns a selection that references the projection output by logical name, not the expression that computes it. Its type is the declared output type.
- A projection may consume another projection's output. The reference is to the named relation, so the producing expression and row plan are not embedded again.
- A projection's own fields are declared in its class; a projection base contributes inherited fields. An explicit field with the same Python attribute shadows the inherited field.

### Row source

- `Projection.row_source() -> RelationRowSource[Any]`: `source` is the projection class; `shape` is `Projection.shape`; `plan_ir` is a scan of the projection's logical name.
- `Projection.where(predicate) -> DerivedRowSource[Self]`: shape-preserving shorthand for `Projection.row_source().where(predicate)`.
- `Projection.projection_base() -> type[Projection]`: a base over the projection's own row source, carrying inherited fields.

### Projection bases

- `projection_base(row_source) -> type[Projection]` returns a dynamic, non-final base with:
  - `_kg_row_source = row_source`;
  - `_projection_base = True`;
  - an inherited computed-field descriptor for every member of `row_source.shape`;
  - a name derived from the root source declaration.
- `Table.projection_base()`, `Projection.projection_base()` and the `projection_base()` methods on `RelationRowSource` and `DerivedRowSource` all delegate to this factory.
- An inherited field has the source shape member's type and nullability. It remains readable after a subclass declares fields of its own.
- A base does not enter the blueprint and is not a final projection. Only a named subclass with `_data_declaration_kind == "projection"` enters the IR.
- Fields supplied by a base and fields declared in a subclass are merged by Python MRO; a duplicate external name is rejected at class creation with `TypeError`.
- `shape_view(source) -> type[Shape]` returns the generated shape used for a projection's `shape`.
- `pinned_base(row_source) -> type[Projection]` returns a fieldless pinned base; the author declares every output.

### IR and codec

- `ProjectionIR(symbol_id, name, fields, description=None, annotations=(), row_source=None)` in `table.ir`.
- `ProjectionFieldIR(name, expression, description=None, annotations=())`; `expression` is an `ExpressionIR`, never an authoring selection.
- The IR stores one row-source plan per projection in `row_source`. A final projection requires a non-null plan; the blueprint codec raises `ValueError("projections require a row source")` if it is absent.
- Field references in projection expressions use logical source names: a table name, a projection name or a generated row-source key. Projection outputs are referenced by the projection's logical name.
- `compile.codec` encodes a projection with its symbol ID, name, fields, description, annotations and `row_source`; decoding reconstructs `ProjectionIR` and validates the whole blueprint. Encoding is deterministic and round-trips.
- Projection dependencies are not stored as a list. They are derived from field-reference sources and from scans in the pinned plan during compilation.
- A final projection's IR carries a non-null row-source plan; the codec refuses a missing plan. Blueprint validation requires unique projection and output names and known expression sources.

## Boundaries

- Projection declarations live in `table.models` and `table.fields`, supported by `table.rows`.
- `table.models` may import `types`, `annotations`, `_support.naming`, `expressions` and the local `table.rows` and `table.fields` interfaces.
- `table.models` must not import `binding`, `topology`, `compile`, `relational`, `engines`, `workflow`, `modules`, `code_generation`, `cli` or `api`.
- `table.ir` may import only `annotations.ir`, `expressions.ir` and `types.ir`; it carries no authoring or engine objects.
- `compile.codec` and `compile.validation` may import `table.ir` and projection declarations; the dependency direction is `compile -> table`, never `table -> compile`.
- `table.models` imports `table.rows` at module load; `table.rows` reaches `table.models` only inside `projection_base()` to preserve one load direction.
- A projection's row source is a `table.rows` value. Projection code does not import a lowerer, relational planner or workflow module.
- Only final projections are discoverable for the blueprint; bases and pinned bases do not enter the IR.

## Current decisions

- Every final projection is pinned. The pin records the row source and its plan; it does not copy fields or output expressions.
- All outputs in one projection share one row plan. An expansion or filter written in any output expression belongs to the whole projection.
- Outputs are computed only. A projection has no source columns of its own; `field()` is a declaration error.
- Reading a projection field is a reference to the named relation, not a re-evaluation. Projection chaining therefore shares the upstream relation instead of duplicating its plan.
- A projection is the named grain contract: consumers depend on its logical name and output fields, not on the source plan behind them.
- A projection has at most one driving source: all field references must resolve to one logical relation. Two unrelated relations in one projection fail relational planning with `a relational product requires one driving source`. A derived row source produced by `join` already carries both inputs and is one driving source.
- Projection dependencies are transitive and must be acyclic. A cycle that includes a projection fails blueprint validation with `projection dependency cycle includes ...`.
- A projection's logical name lives in the same namespace as table names; duplicate names fail validation. The symbol ID is the stable Python identity; the logical name is the reference and display name.
- Inherited fields are normal outputs of the subclass: they are emitted in its `ProjectionIR` and can be read as `Subclass.field`. A declared field shadows an inherited field by Python attribute.
- A projection base is a declaration aid, not a model object: it carries a pin and fields but no IR until subclassed.
- An unused projection is not part of the blueprint; only projections reachable from binding expressions or row-source plans are resolved.
