# declarations

## Responsibility

The `kg_build_system.table` package owns the logical row and record declarations an author writes and the row-source values those declarations expose.

## Public interface

- `Field[T]` is the one member descriptor. It carries:
  - `expression: ValueExpression[T] | None` — the implementation of a computed field; `None` for a source field.
  - `metadata: FieldMetadata(name, description, annotations, attribute)`.
  - `access_type(owner) -> LogicalType` — the type one read yields.
- Constructors:
  - `field[T](*, name: str | None = None, description: str | None = None, annotations: Sequence[Annotation] = ()) -> Field[T]`
  - `computed_field[T](value: ValueInput[T], *, name=None, description=None, annotations=()) -> Field[T]`
- `declared_fields(owner: type) -> dict[str, Field[Any]]` returns the resolved member set of a declaration.
- Declaration bases and options:
  - `Table` with `TableOptions(name=None, description=None, annotations=())`.
  - `Struct` with `StructOptions(name=None, description=None, annotations=())`.
  - `ComputedStruct` with `StructOptions`.
  - `Projection` with `ProjectionOptions(name=None, description=None, annotations=())`.
  - `TableGroup` with `TableGroupOptions(members=(), name=None, description=None, annotations=())`.
  - `StructTemplate` with `StructOptionsTemplate(annotations=())`.
- `Table` and `Projection` are both `Shape` and `RowSource`:
  - `Table.row_source() -> RelationRowSource[Table]`
  - `Table.where(predicate: Callable[[Table], BoolExpression]) -> DerivedRowSource[Table]`
  - `Table.projection_base() -> type`
  - `Projection.row_source() -> RelationRowSource[Any]`
  - `Projection.where(...) -> DerivedRowSource[Projection]`
  - `Projection.projection_base() -> type`
- `Projection(source)` is a pinned base: it carries the source's row plan and no inherited outputs. A named subclass declares the outputs.
- `projection_base()` on a table, a projection, or a row-source value returns a base carrying the source's row plan and inherited output fields.
- `Struct`, `ComputedStruct`, `Table` and `Projection` expose their resolved members as a shape; `TableGroup` is neither a shape nor a row source.
- Source binding:
  - `InputFormat` is `CSV`, `JSON` or `PARQUET`.
  - `DataSourceConfig(location, format=InputFormat.CSV, layout=None, credentials=None, version=None)`; `location` must be non-empty.
  - `bind_source(*, target: type, config: DataSourceConfig, options: SourceBindingOptions = SourceBindingOptions()) -> BoundSource`.
  - `BoundSource = BoundTable | BoundTableGroup`; `BoundTable(table, config, annotations=())`; `BoundTableGroup(group, config, annotations=())`.
  - `resolve_bound_source(source: BoundSource) -> tuple[BoundTable, ...]` expands a group binding into per-table bindings.
- Row-source values:
  - `RelationRowSource(source, shape, filters=())` reads one named table or projection.
  - `DerivedRowSource(shape, source, filters=(), plan_ir=None)` is produced by filtering or the row-source algebra.
  - `RowSource.where`, `union`, `join`, `group_by`, `distinct`, `order_by` and `projection_base` are the value operations.
- Compilation IR in `table.ir`:
  - `FieldIR(name, logical_type, description=None, annotations=())`.
  - `StructIR(symbol_id, name, fields, description=None, annotations=())`.
  - `TableIR(symbol_id, name, fields, description=None, annotations=())`.
  - `ProjectionFieldIR(name, expression, description=None, annotations=())`.
  - `ProjectionIR(symbol_id, name, fields, description=None, annotations=(), row_source=...)`.
  - `SourceIR(symbol_id, table, location, format, credential_reference=None, version=None, annotations=())`.
  - Row-plan nodes: `RowScanIR`, `RowFilterIR`, `RowUnionIR`, `RowJoinIR`, `RowGroupByIR`, `RowDistinctIR`, `RowOrderByIR` and `RowOrderKeyIR`; `JoinHow = "inner" | "left" | "right" | "full"`.
  - `encode_row_source_plan` and `decode_row_source_plan` serialise only plan IR.
- Declaration-time errors are `TypeError` or `ValueError`, raised while the class or source binding is created.

## Boundaries

- Surfaces: `kg_build_system.table` is the author-facing declaration surface; `table.interfaces` exposes the declaration and row-source values other subpackages may consume; `table.ir` is the declaration IR.
- Allowed dependencies: `types.interfaces`, `annotations.interfaces`, `expressions.interfaces`, and the `_support` kernel.
- A declaration carries no engine, runtime, workflow or binding state.
- `binding`, `compile`, `engines` and `modules` import `table.interfaces`; they never import a table implementation module.
## Current decisions

### Fields and backing

- **One descriptor, two constructors.** `field()` declares source backing: a table column or a source struct member. `computed_field(expression)` declares expression backing: a projection output or a computed struct member. There is no scalar field, struct field or collection field subclass.
- **Backing is chosen by the owner.** A `Table` or source `Struct` rejects a computed field and requires `field()`. A `Projection` or `ComputedStruct` rejects a declared field and requires `computed_field()`. A pinned projection base is not final and validates its final subclass.
- **The annotation and the expression are different facts.** A source field requires a `Field[T]` annotation. A computed field is typed by its expression; it may omit the annotation. A computed expression is stored as a `ValueExpression` at declaration time.
- **Source declarations name the value.** `field()` strips a top-level `NullableType` from the annotation. `Field[str | None]` and `Field[str]` are the same source value type; array item nullability (`Array[str | None]`) remains part of the value.
- **Source access is always nullable.** Reading a source field yields `NullableSelection[T]`, including arrays and structs. Reading a computed field yields the selection matching the expression's type: non-null for a non-null expression, nullable for a nullable expression.
- **A projection field is an output reference.** Reading `Projection.field` returns a reference to the projection's materialised output, not the calculation that produced it. A `ComputedStruct` used as a field type is a type witness: its member types come from the declared expressions, but member reads are reads on the carrier field, not evaluations of those expressions. This is what lets projections compose without duplicating row plans.
- **One field instance, one declaration.** A `Field` instance may not be assigned to two declarations. Inheritance shares the descriptor without re-running `__set_name__`.

### Names, options, descriptions and annotations

- **Declaration names.** `options.name` wins. Otherwise the class name loses one matching suffix and becomes snake case:
  - `Table` removes `Table`; `Struct` removes `Struct`; `ComputedStruct` removes `ComputedStruct`.
  - `Projection` removes `Projection`; `TableGroup` removes `TableGroup`.
  - An explicit name is used exactly as written. A class name that becomes empty after suffix removal is an error.
- **Member names.** An external member name is `name=` when supplied, otherwise the attribute converted to snake case. One trailing underscore is the escape for a reserved attribute: `options_` has the external name `options`. Two members of one declaration may not share an external name.
- **Descriptions are own-only.** A declaration's description is `options.description` or its own class docstring; an inherited description does not flow. A member's description is an explicit `description=` or a documentation string written directly below the declaration; the explicit value wins. The documentation string belongs to the declaring class and is resolved at class creation. If module source cannot be read, the member simply has no documentation string.
- **Options are class metadata.** They are never fields, graph properties or constructor arguments. A declaration's own options must match its tier: `TableOptions` for `Table`, `StructOptions` for `Struct` and `ComputedStruct`, `ProjectionOptions` for `Projection`, `TableGroupOptions` for `TableGroup`. The wrong tier and a raw annotation sequence are rejected at class creation.
- **Annotations are portable metadata.** `Field` and every declaration option carry `Annotation` values. Annotations are frozen, have a stable namespace and ID, and are stored as data; the declaration class itself is never stored in the IR.

### Declaration kinds and finality

- **`Table` is a final source relation.** It is both the typed shape expressions read and the row source a binding consumes. It may inherit templates and non-final mixins; fields merge by normal Python shadowing, and a non-field class attribute removes an inherited slot. A final table may not inherit another final table.
- **`Struct` is a value record.** It is a nested record referenced as `Field[T]` or `Array[T]`, composable but not a row source. It cannot be source-bound, placed in a table group, or passed as `rows=`. A struct's identity is `(module, qualname)`.
- **`ComputedStruct` is an expression-built value record.** Its members are `computed_field()` expressions and each member type comes from its expression, including nullability. It is usable as `Field[T]` and navigated with `extract`, but it is not a table or row source, cannot be source-bound, cannot be a table-group member, and has no public factory that assembles a value from member expressions. It enters the blueprint as a `StructIR`; there is no separate computed-struct IR.
- **`Projection` is a final named relation.** It is a `Shape` and a `RowSource`. A projection must be pinned to a row source at class creation; a direct `class P(Projection)` is rejected. A final projection must declare at least one `computed_field`, and may not inherit another final projection.
- **`TableGroup` is a final catalog.** It is not a shape and not a row source. It contains final `Table` declarations and nested `TableGroup` declarations, supplied as class attributes or through `TableGroupOptions.members`. It may not inherit another final group.
- **`Struct` and `ComputedStruct` are not finality-guarded.** A value-record subclass merges inherited `Field` slots by normal Python shadowing. Shared shape concerns belong to the `StructTemplate` tier; subclassing a value record is not the template API.
- **Templates never enter the blueprint.** A `StructTemplate` is an inert mixin carrying `Field` slots and annotations; it has no name, description, declaration kind or IR entry. It may be mixed into a `Table`, `Struct` or `ComputedStruct` host; mixing it into a `Projection` or `TableGroup` is rejected. The host's backing rule still applies to every inherited slot.

### Templates, options and annotation flow

- **The template tier has annotations-only options.** `StructOptionsTemplate` carries only `annotations`. A template given real `TableOptions`/`StructOptions`, or an unwrapped sequence, is rejected with a redirect to `StructOptionsTemplate`.
- **The host owns identity.** A table, struct or computed struct host uses its real options; template options on a host are rejected. A template may extend another template by naming it as a base.
- **Annotation flow.** Effective declaration annotations are the template contributions in reverse MRO order, each template exactly once, followed by the host's own `options.annotations`. A template entering through several branches contributes once. An IR-visible declaration keeps its own annotations on its own entry; they do not flow to children.
- **Templates share fields, not identity.** A template's `Field` descriptors are inherited by the host; the resulting declaration has one resolved field set and one logical identity.

### Projections and projection bases

- **Pin, then declare.** `Projection(source)` returns an intermediate base pinned to the source plan and carrying no inherited fields. The named subclass supplies the outputs.
- **`projection_base()` carries fields.** The base returned by `projection_base()` carries the source plan and the source's fields as computed outputs, typed by source access (so source-derived outputs are nullable). A declared field with the same attribute shadows the inherited one; duplicate external names are rejected.
- **One row source per projection.** The pin records the source relation and filters. A projection output may reference another projection; that reference is to the named relation, not an embedded plan. Projection dependencies must be acyclic.
- **Projection outputs are final.** The output set is fixed at class creation. A projection cannot add fields by subclassing a final projection; use `projection_base()` or pin a new source.
- **Logical source names.** Table names, projection names, and the combined set of table and projection names are unique. A projection name colliding with a table name is a compile error.

### Table groups and physical sources

- **Group members are final declarations.** A group's members are class attributes whose values are final `Table` or `TableGroup` declarations, plus `TableGroupOptions.members`. Groups must be non-empty. Invalid member kinds, cycles, duplicate table inclusion and duplicate catalog paths are rejected.
- **Catalog paths are stable.** Flattening a group yields each concrete table with its path: group names in nesting order, then the table name. A group source expands to one source binding per table with the same config and annotations.
- **Group layout.** A group source requires `DataSourceConfig.layout`, which may interpolate only `{group_path}` and `{table_name}`. The resolved location is the group's location joined with the layout result. A group is never a row source; bindings still target a concrete table.
- **Source binding.** `bind_source` accepts a final `Table` or `TableGroup` and returns a `BoundTable` or `BoundTableGroup`. A table has exactly one physical source in the blueprint. Credentials are references, never resolved values; `version` is carried as source metadata.
- **Source validation.** A source must name a declared table; source-bound table names are unique. A group binding's per-table expansion is validated as ordinary table sources.

### Row sources

- `Table.row_source()` and `Projection.row_source()` provide the relation a binding or projection reads; the class-level `where` shorthand returns a filtered derived source.
- The algebra (`where`, `union`, `join`, `group_by`, `distinct`, `order_by`), generated shapes and plan IR are owned by `row-sources.md`.

### IR and validation

- **The IR contains facts, not classes.** Every field, table, struct, projection, source and row-plan node is frozen data. No declaration, descriptor, expression wrapper or connection appears in it.
- **Field types in the IR.** A source `FieldIR` carries the declared value type, after top-level nullable stripping; access nullability is an authoring rule, not stored in the field. A computed field carries its expression's type. A `ComputedStruct` is represented by `StructIR`.
- **Only final declarations enter.** Templates, pinned projection bases and declarations not reached from a binding, projection, row source or struct closure do not enter the blueprint.
- **Deterministic order.** Field order follows resolved declaration order. The blueprint preserves declaration order within each declaration and uses content identity for derived row sources.
- **Validation.** Compilation rejects duplicate field names within a declaration, duplicate table or projection names, duplicate table-plus-projection source names, duplicate source bindings, unknown source tables, projection dependency cycles, and a row-source shape that is structurally incompatible with its declared relations.
