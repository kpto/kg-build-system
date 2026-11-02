# Types

## Responsibility

The `kg_build_system.types` package owns the canonical logical-type vocabulary, authoring normalization, representative aliases, graph-value validation and the type codecs.

## Public API

Names are defined in `types.public`; `kg_build_system.types` exposes only that package.

- Canonical type model used by the public marker surface and the internal interface:
  - `UnitType(name: UnitTypeName)` where `UnitTypeName = Literal["bool", "int", "float", "str", "date", "time", "timestamp", "uuid"]` (internal).
  - `CustomType(module: str, qualname: str)` for an application-defined scalar (internal).
  - `StructType(module: str, qualname: str)` for a declared `Struct` or `ComputedStruct` (internal).
  - `ArrayType(item: LogicalType)` and `NullableType(value: NonNullableLogicalType)` (public).
  - `NonNullableLogicalType = UnitType | CustomType | StructType | ArrayType`; `LogicalType = NonNullableLogicalType | NullableType`.
- Unit constants: `BOOL`, `INT`, `FLOAT`, `STR`, `DATE`, `TIME`, `TIMESTAMP`, `UUID`.
- Authoring markers:
  - `Array[T]` for an ordered collection.
  - `Nullable[T]` for the explicit nullable marker; `T | None` normalizes to the same value.
  - `CustomDataType` as the base of an application-defined scalar.
  - `Shape` and `Struct` as declaration markers; a `Struct` is a value record, not a row source.
- Representative aliases: `Date = datetime.date`, `Time = datetime.time`, `Timestamp = datetime.datetime`, `Uuid = uuid.UUID`.
- Public constructors and aliases re-exported by `kg_build_system.types`: `Array`, `ArrayType`, `Nullable`, `NullableType`, `Shape`, `Struct`, `CustomDataType`, the unit constants and the representative aliases.

## Internal interface

`types.internal` exposes the canonical names a declaration layer needs:

- `CustomType`, `StructType`, `UnitType`, `UnitTypeName`, `LogicalType`, `NonNullableLogicalType`.
- `CANONICAL_UNIT_NAMES` and `TEXT_CANONICAL_UNIT_NAMES`.
- `normalize_type(annotation: Any) -> LogicalType`.
- `is_nullable(value) -> bool`, `non_nullable(value) -> LogicalType`.
- `array_item(value) -> LogicalType`; raises `TypeError` when the value is not an array.
- `require_non_nullable(value, *, context)`, `require_scalar(value, *, context)`, `require_graph_property(value, *, context)`.
- `canonical_value_text(value) -> str` and `is_canonical_unit_name(name) -> TypeGuard[UnitTypeName]`.
- `type_to_ir(logical_type) -> LogicalTypeIR`.
- `encode_type`/`decode_type` for the domain logical type; `encode_type_ir`/`decode_type_ir` for the IR type.

Invariants:

- `UnitType` rejects an unknown unit name.
- `CustomType` and `StructType` reject an empty module or qualname.
- `NullableType` rejects another `NullableType`; nullability is flat.
- `ArrayType.item` is any logical type, including another array, a struct or a nullable type.
- `array_item` unwraps a nullable array before returning its item; item nullability is preserved.
- `require_graph_property` accepts a scalar (nullable or not) or a one-level array of non-null scalars. It rejects a struct, a nested array and an array with nullable items.

## IR

`types.internal.ir` owns the logical-type IR; the root `types.ir` module is a compatibility shim only.

- `UnitTypeIR(name)`, `CustomTypeIR(module, qualname)`, `StructTypeIR(module, qualname)`, `ArrayTypeIR(item)`, `NullableTypeIR(value)`.
- `NonNullableLogicalTypeIR = UnitTypeIR | CustomTypeIR | StructTypeIR | ArrayTypeIR`; `LogicalTypeIR = NonNullableLogicalTypeIR | NullableTypeIR`.
- `type_to_ir` is one way and never retains a declaration class.
- `encode_type_ir`/`decode_type_ir` use a canonical JSON object keyed by `kind`: `unit`, `custom`, `struct`, `array`, `nullable`. Decoding refuses an unknown kind, an unknown unit name and nested nullable IR.
- `encode_type`/`decode_type` use the same `kind` encoding for the domain model.

## Boundaries

- `types` imports nothing else from `kg_build_system`.
- Surfaces: `kg_build_system.types` exposes only `types.public`; `types.public` is the author-facing vocabulary; `types.internal` is normalization, validation and codecs; `types.internal.ir` is the logical-type IR. The root `types.ir` module is a compatibility shim.
- `expressions`, `table`, `topology`, `binding`, `relational`, `engines`, `modules` and `code_generation` import `types.internal` or `types.internal.ir`. They never import a `types` implementation module.
- DuckDB type acceptance, the digest table, SQL type composition and Parquet metadata live in `engines.internal`; `types` owns no physical type mapping.
- A target may narrow the canonical types it stores, but it may not invent a canonical type.

## Current decisions

- **Canonical names are lowercase.** `bool`, `int`, `float`, `str`, `date`, `time`, `timestamp` and `uuid` are the only unit names. A capitalised spelling is a representative type, never a canonical name.
- **Representative types are aliases, not classes.** Normalization dispatches on exact Python class identity, so `Field[Uuid]` and `Field[uuid.UUID]` are one declaration and cannot drift.
- **Canonical vocabulary.** A logical type is a unit, a custom scalar, a declared struct identity, an array, or a nullable wrapper. `CustomType` and `StructType` identify a declaration by `(module, qualname)`; the logical name is display only.
- **Normalization is explicit.**
  - A canonical logical type is accepted unchanged.
  - `T | None` and `Nullable[T]` require exactly one non-null member and produce one `NullableType`.
  - `Array[T]` requires exactly one item type.
  - `Any`, `list[T]`, `Sequence[T]`, `dict[K, V]`, tuples and multi-member unions are refused.
  - A `CustomDataType` subclass normalizes to `CustomType`; a `Struct` subclass normalizes to `StructType`.
  - Any other `Shape` subclass, including a `Table` or `Projection`, is refused as a value type with the row-source message.
  - No importability check is performed: a declaration's identity is whatever `__module__` and `__qualname__` it carries.
- **Nullability is flattened.** `NullableType` wraps only a non-nullable type and never wraps another `NullableType`.
- **Source-field access follows the declaration.** A source field carries the declared logical type, including any top-level nullable wrapper. `Field[T]` reads as a non-null selection; `Field[T | None]` reads as a nullable selection. A computed field carries its expression's type. Array item nullability is independent of the array's own nullability.
- **Struct identity is the declaration.** Two `Struct` or `ComputedStruct` classes with the same logical name in different modules are distinct. A generated record uses its `(module, qualname)` identity too; `types` owns no shape registry.
- **Graph properties accept a flat value.** Custom scalars count as scalars. A struct, a nested array and an array with nullable items are refused; the error names the conversion (`expand()` or `drop_null_items()`).
- **Keys are defined by the binding layer.** `types` supplies `require_scalar` and `require_non_nullable`; the binding factory requires both. `require_scalar` admits unit, custom and struct types and refuses arrays.
- **Canonical text.** `canonical_value_text` uses `isoformat()` for date, time and datetime, which gives timestamps the `T` separator, and lowercase hyphenated text for uuid. Arrays and structs have no single text form.
- **Targets may narrow capability.** Neo4j accepts `bool`, `int`, `float`, `str`, `date`, `time` and `timestamp` scalar properties; it refuses `uuid` and custom scalars. Its array properties hold `bool`, `int`, `float` or `str` items. The refusal happens at compile, never by coercion.
