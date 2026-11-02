# Declarations

## Responsibility

The `table` package owns the logical row and record declarations an author writes, the field model, table groups and physical source bindings.

## Public API

Names are defined in `table.public`; `kg_build_system.table` exposes only that package.

- `Field[T]` is the one member descriptor. It carries:
  - `expression: ValueExpression[T] | None` — the computed expression; `None` for a source-backed field;
  - `metadata: FieldMetadata(name, description, annotations, attribute)`;
  - `access_type(owner) -> LogicalType` — the type one read yields.
- Constructors:
  - `field[T](*, name=None, description=None, annotations=()) -> Field[T]` declares source backing.
  - `computed_field[T](value: ValueInput[T], *, name=None, description=None, annotations=()) -> Field[T]` declares expression backing.
  - `projection_field[T](value, *, name=None, description=None, annotations=()) -> Field[T]` is the compatibility spelling of `computed_field`; see `../DESIGN_ISSUES.md` item 3.
- Declaration bases and options:
  - `Table` with `TableOptions(name=None, description=None, annotations=())`.
  - `Struct` with `StructOptions(name=None, description=None, annotations=())`.
  - `ComputedStruct` with `StructOptions`.
  - `Projection` with `ProjectionOptions`; its pinning and output rules are in [projections](projections.md).
  - `TableGroup` with `TableGroupOptions(members=(), name=None, description=None, annotations=())`.
  - `StructTemplate` with `StructOptionsTemplate(annotations=())`.
- `Table` and `Projection` are shapes and row sources:
  - `Table.row_source() -> RelationRowSource[Table]`
  - `Table.where(predicate: Callable[[Table], BoolExpression]) -> DerivedRowSource[Table]`
  - `Table.projection_base() -> type`
  - `Projection.row_source() -> RelationRowSource[Any]`
  - `Projection.where(...) -> DerivedRowSource[Projection]`
  - `Projection.projection_base() -> type`
- `projection_base(row_source) -> type[Projection]`, `shape_view(source) -> type[Shape]`.
- Source binding:
  - `InputFormat` is `CSV`, `JSON` or `PARQUET`.
  - `DataSourceConfig(location, format=InputFormat.CSV, layout=None, credentials=None, version=None)`; `location` must be non-empty.
  - `bind_source(*, target: type, config: DataSourceConfig, options: SourceBindingOptions = SourceBindingOptions()) -> BoundSource`.
  - `BoundSource = BoundTable | BoundTableGroup`; `BoundTable(table, config, annotations=())`; `BoundTableGroup(group, config, annotations=())`.
  - `resolve_bound_source(source) -> tuple[BoundTable, ...]` expands a group binding into per-table bindings.

## Internal interface

`table.internal` exposes the framework-internal declaration and source interface:

- Metadata and helpers: `DeclarationSpec`, `FieldSpec`, `FieldMetadata`, `AuthoringDataType`, `declared_fields`, `resolve_field_specs`, `projection_base`, `projection_row_source`, `is_concrete_table`, `is_table_group`, `struct_type_key`.
- Source helpers: `group_tables`, `resolve_bound_source`; the authoring source values `DataSourceConfig`, `InputFormat`, `SourceBindingOptions`, `BoundSource`, `BoundTable`, `BoundTableGroup` and `bind_source` are defined in `table.public`.
- Row-source helpers and plan IR, re-exported from [row-sources](row-sources.md).
- The `data` language: `TableLanguage` in `table.internal.adapters.kernel_language`.
- The data IR codec: `encode_data_part`, `decode_data_part`, `encode_row_source_plan`, `decode_row_source_plan`.
- `struct_type_key(struct: StructIR) -> tuple[str, str] | None`, recovering the `(module, qualname)` identity of a struct-typed symbol.

Invariants:

- A `FieldSpec` is resolved once at class creation: `attribute`, external `name`, `descriptor`, declared `logical_type`, `access_type`, optional description and annotations, and the optional `Struct`/`ComputedStruct` declaration.
- A declaration's fields are the inherited `Field` descriptors with normal Python shadowing. A non-field class attribute removes an inherited slot.
- External field names are unique within one declaration.
- Only final declarations enter the IR: a table, struct, computed struct or projection with `DeclarationSpec.final` is lowered; templates, pinned projection bases and unused declarations are not.

## IR

`table.internal.ir` owns the declaration IR.

- `DataIR(structs, tables, projections, sources)` is the frozen `data` part.
- `FieldIR(name, logical_type, description=None, annotations=())`.
- `StructIR(symbol_id, name, fields, description=None, annotations=())`.
- `TableIR(symbol_id, name, fields, description=None, annotations=())`.
- `ProjectionFieldIR(name, expression, description=None, annotations=())`.
- `ProjectionIR(symbol_id, name, fields, description=None, annotations=(), row_source=None)`; the projection codec refuses a missing `row_source`.
- `SourceIR(symbol_id, table, location, format, credential_reference=None, version=None, annotations=())`.
- `encode_data_part` emits `structs`, `tables`, `projections` and `sources`; `decode_data_part` reconstructs `DataIR`. Encoding is deterministic and round-trips.
- Symbol IDs are `python:table:<module>:<qualname>`, `python:struct:<module>:<qualname>` (also used for `ComputedStruct`), `python:projection:<module>:<qualname>`; a source is `source:<table name>`.
- Structs, tables, projections and sources are emitted in symbol-ID order. Field order follows resolved declaration order.

## Boundaries

- Surfaces: `kg_build_system.table` exposes only `table.public`; `table.public` is the author-facing declaration surface; `table.internal` exposes declaration and source values plus the `data` language; `table.internal.ir` is the declaration IR; mechanisms are in `table._private`.
- Allowed dependencies: `types.internal`, `annotations.internal`, `expressions.internal`, `_support.interfaces`, `_frozen_json` and `kernel`.
- `table` never imports `binding`, `topology`, `relational`, `compile`, `engines`, `workflow`, `modules`, `code_generation`, `cli` or `api`.
- `binding`, `relational`, `compile`, `engines` and `modules` import `table.internal` or `table.internal.ir`; they never import a table implementation module.

## Current decisions

### Fields and backing

- **One descriptor, three constructors.** `field()` declares source backing; `computed_field()` declares expression backing; `projection_field()` is the compatibility alias of `computed_field()`. There is no separate scalar, struct or collection field class.
- **Backing is chosen by the owner.** A `Table` or source `Struct` requires `field()` and rejects a computed field. A `Projection` or `ComputedStruct` requires an expression-backed field and rejects `field()`.
- **The annotation and the expression are different facts.** A source field requires a `Field[T]` annotation. A computed field is typed by its expression; it may omit the annotation. If it carries one, the annotation only supplies a declaration witness for a struct type.
- **Source access follows the declaration.** `Field[T]` reads as a present selection; `Field[T | None]` reads as a nullable selection. Array item nullability such as `Array[T | None]` remains part of the value.
- **Computed access follows the expression.** A non-null expression yields a present selection; a nullable expression yields a nullable selection.
- **A projection field is an output reference.** Reading `Projection.field` returns a reference to the projection's named output, not the expression that produced it.
- **One field instance, one declaration.** A `Field` instance may not be assigned to two declarations. Inheritance shares the descriptor without re-running `__set_name__`.

### Names, options, descriptions and annotations

- **Declaration names.** `options.name` wins. Otherwise the class name loses one matching suffix and becomes snake case:
  - `Table` removes `Table`; `Struct` removes `Struct`; `ComputedStruct` removes `ComputedStruct`;
  - `Projection` removes `Projection`; `TableGroup` removes `TableGroup`.
  - An explicit name is used exactly as written. A class name that becomes empty after suffix removal is an error.
- **Member names.** An external member name is `name=` when supplied, otherwise the attribute converted to snake case. One trailing underscore is the escape for a reserved attribute: `options_` has the external name `options`. Two members of one declaration may not share an external name.
- **Descriptions are own-only.** A declaration's description is `options.description` or its own class docstring; an inherited description does not flow. A member's description is an explicit `description=` or a documentation string written directly below the declaration; the explicit value wins. If source cannot be read, the member has no documentation string.
- **Options are class metadata.** They are never fields or graph properties. A declaration's own options must match its tier: `TableOptions`, `StructOptions`, `ProjectionOptions` or `TableGroupOptions`. `StructTemplate` takes `StructOptionsTemplate`. A wrong tier or an unwrapped annotation sequence is rejected at class creation.
- **Annotations are portable metadata.** `Field` and declaration options carry `Annotation` values. Annotations are stored as data; the declaration class is never stored in IR.
- **Annotation flow.** Effective declaration annotations are the template contributions in reverse MRO order, each template once, followed by the host's own `options.annotations`. Category or parent annotations do not flow to children.

### Declaration kinds and finality

- **`Table` is a final source relation.** It is both the typed shape expressions read and the row source a binding consumes. It may inherit templates and non-final mixins; a final table may not inherit another final table.
- **`Struct` is a value record.** It is a nested record referenced as `Field[T]` or `Array[T]`, composable but not a row source. It cannot be source-bound, placed in a table group or passed as `rows=`. Its identity is `(module, qualname)`.
- **`ComputedStruct` is an expression-built value record.** Its members are expression-backed; each member type comes from its expression, including nullability. It is usable as `Field[T]` and navigated with `extract`, but it is not a table or row source, cannot be source-bound and cannot be a table-group member. It enters the blueprint as a `StructIR`.
- **`Projection` is a final named relation.** It is a shape and a row source. It may be pinned with `Projection(source)` or declared unpinned with `projection_field`; see [projections](projections.md). A final projection must declare at least one output and may not inherit another final projection.
- **`TableGroup` is a final catalog.** It is not a shape and not a row source. It contains final `Table` declarations and nested `TableGroup` declarations, supplied as class attributes or through `TableGroupOptions.members`. It must be non-empty and may not inherit another final group.
- **`Struct` and `ComputedStruct` are not finality-guarded.** A value-record subclass merges inherited `Field` slots by normal Python shadowing. Shared shape concerns belong to `StructTemplate`; subclassing a value record is not the template API.
- **Templates never enter the blueprint.** A `StructTemplate` is an inert mixin carrying `Field` slots and annotations. It may be mixed into a `Table`, `Struct` or `ComputedStruct` host; mixing it into a `Projection` or `TableGroup` is rejected. The host's backing rule applies to every inherited slot.

### Table groups and physical sources

- **Group members are final declarations.** A group's members are class attributes whose values are final `Table` or `TableGroup` declarations, plus `TableGroupOptions.members`. Invalid member kinds, cycles, duplicate table inclusion and duplicate catalog paths are rejected.
- **Catalog paths are stable.** Flattening a group yields each concrete table with its path: group names in nesting order, then the table name. A group source expands to one source binding per table with the same config and annotations.
- **Group layout.** A group source requires `DataSourceConfig.layout`, which may interpolate only `{group_path}` and `{table_name}`. The resolved location is the group's location joined with the layout result. A group is never a row source; bindings target concrete tables.
- **Source binding.** `bind_source` accepts a final `Table` or `TableGroup` and returns a `BoundTable` or `BoundTableGroup`. A table has at most one physical source; source-bound table names are unique. Credentials are references, never resolved values; `version` is carried as source metadata.
- **Source validation.** The `data` language rejects duplicate table names or projection names, a table/projection name collision, duplicate field names, duplicate source-bound table names and a source that names an unknown table. It also rejects a projection dependency cycle and a missing projection row source.

### Language and IR

- **The IR contains facts, not classes.** Every field, table, struct, projection, source and row-plan node is frozen data. No declaration, descriptor, expression wrapper or connection appears in it.
- **The `data` language collects from the namespace.** `TableLanguage.collect` walks public namespace values, follows bound sources, row-source values, nested declarations and `rows` attributes, and keeps final declarations. It does not invoke arbitrary factories.
- **Deterministic output.** Structs, tables, projections and sources are sorted by symbol ID; fields keep declaration order. The same declarations produce the same `DataIR`.
- **Projection dependencies are derived.** They are not stored as a list; the language derives them from field-reference sources and plan scans.
