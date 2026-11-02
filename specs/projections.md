# Projections

## Responsibility

The `table` package owns the named projection declaration: its row-source pin or derived plan, its computed output fields, and the output references other declarations read.

## Public API

### Declaration

- `Projection` is a `Shape` and a `RowSource["Projection"]`, with metaclass `ProjectionMeta`.
- `Projection(source)` returns a dynamic pinned base carrying the source's row plan and no inherited outputs. The argument must be a row-source value; `Projection(None)` raises `TypeError`.
- `class P(Projection)` with `projection_field(...)` outputs is the compatibility form. It is unpinned and derives its row plan from its output expressions. See `../DESIGN_ISSUES.md` item 3.
- A final projection must declare at least one effective output; no output raises `TypeError("projections must declare at least one computed_field")`.
- `field()` in a projection is rejected; outputs are expression-backed. Use `computed_field()` or the compatibility `projection_field()`.
- A final `Projection` may not inherit another final `Projection`. Reuse is through `projection_base()` or a new pin.
- `ProjectionOptions(name=None, description=None, annotations=())`: `name` defaults to the class name with one trailing `Projection` removed and snake-cased; `description` defaults to the class docstring; annotations are portable metadata.
- A projection's logical name must be unique among tables and projections.
- `Projection.shape` is a generated `Shape` view carrying the projection's fields. `Projection.row_source()` uses `cls.shape`.

### Outputs

- `computed_field(value, *, name=None, description=None, annotations=()) -> Field[T]` declares one output.
- `projection_field(value, *, name=None, description=None, annotations=()) -> Field[T]` is the compatibility spelling of `computed_field`; backing and resolved type are identical.
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
- `Table.projection_base()`, `Projection.projection_base()` and the `projection_base()` methods on `RelationRowSource` and `DerivedRowSource` delegate to this factory.
- An inherited field has the source shape member's type and nullability. It remains readable after a subclass declares fields of its own.
- A base does not enter the blueprint and is not a final projection. Only a named subclass with a final declaration spec enters the IR.
- Fields supplied by a base and fields declared in a subclass are merged by Python MRO; a duplicate external name is rejected at class creation with `TypeError`.
- `shape_view(source) -> type[Shape]` returns the generated shape used for a projection's `shape`.
- `pinned_base(row_source) -> type[Projection]` returns a fieldless pinned base; the author declares every output.

## Internal interface

`table.interfaces` exposes `Projection`, `ProjectionMeta`, `ProjectionOptions`, `projection_base`, `projection_row_source`, `ProjectionFieldIR`, `ProjectionIR` and the projection codec through `encode_data_part`/`decode_data_part`.

Invariants:

- A projection declaration carries a frozen declaration spec with `kind="projection"`, a logical name, fields, annotations and an optional row-source pin.
- `projection_row_source(declaration)` returns the pinned plan when present; otherwise it derives the one logical source read by the outputs. A projection reading no source or several unrelated sources has no single driving relation and returns `None`.
- A final projection's IR must carry a non-null row-source plan.
- Inheritance from a project base merges fields; a final projection is terminal.

## IR

- `ProjectionIR(symbol_id, name, fields, description=None, annotations=(), row_source=None)` in `table.ir`.
- `ProjectionFieldIR(name, expression, description=None, annotations=())`; `expression` is an `ExpressionIR`, never an authoring selection.
- The IR stores one row-source plan per projection in `row_source`. A final projection requires a non-null plan; `encode_data_part` and `decode_data_part` raise `ValueError("projections require a row source")` if it is absent.
- Field references in projection expressions use logical source names: a table name, a projection name or a generated row-source key. Projection outputs are referenced by the projection's logical name.
- Projection dependencies are not stored as a list. They are derived from field-reference sources and from scans in the row plan during data-language validation.
- Encoding is deterministic and round-trips; decoding validates the whole data part.

## Boundaries

- Surfaces: `Projection` is author-facing through `kg_build_system.table`; `table.interfaces` exposes projection declarations and helpers; `table.ir` carries `ProjectionIR`.
- Allowed dependencies: `types.interfaces`, `annotations.interfaces`, `expressions.interfaces`, `_support.interfaces`, `_frozen_json`, `kernel` and the local declaration and row-source modules.
- `table` never imports `binding`, `topology`, `relational`, `compile`, `engines`, `workflow`, `modules`, `code_generation`, `cli` or `api`.
- `compile` reads projection IR; `modules.core` orders and lowers projections; the dependency direction is `compile -> table` and `modules -> table`.

## Current decisions

- **A final projection has a row plan, pinned or derived.** The preferred form pins a row source. The compatibility form is unpinned and derives a scan from its output expressions. Both lower to the same `ProjectionIR`.
- **All outputs in one projection share one row plan.** An expansion or filter written in any output expression belongs to the whole projection.
- **Outputs are computed only.** A projection has no source columns of its own; `field()` is a declaration error.
- **Reading a projection field is a reference to the named relation**, not a re-evaluation. Projection chaining shares the upstream relation instead of duplicating its plan.
- **A projection is the named grain contract.** Consumers depend on its logical name and output fields, not on the source plan behind them.
- **A projection has at most one driving source.** All field references must resolve to one logical relation. Two unrelated relations fail relational planning with `a relational product requires one driving source`. A derived row source produced by `join` already carries both inputs and is one driving source.
- **Projection dependencies are transitive and acyclic.** A cycle that includes a projection fails data validation with `projection dependency cycle includes ...`.
- **A projection's logical name lives in the same namespace as table names.** Duplicate names fail validation. The symbol ID is the stable Python identity; the logical name is the reference and display name.
- **Inherited fields are normal outputs of the subclass.** They are emitted in its `ProjectionIR` and can be read as `Subclass.field`. A declared field shadows an inherited field by Python attribute.
- **A projection base is a declaration aid, not a model object.** It carries a pin and fields but no IR until subclassed.
- **An unused projection is not part of the blueprint.** Only projections reachable from binding expressions or row-source plans are resolved.
