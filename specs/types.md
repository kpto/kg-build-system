# types

## Responsibility

The `kg_build_system.types` package owns the canonical logical-type vocabulary, authoring normalization, representative aliases, graph-value validation and type codecs; the DuckDB digest gate owns the mapping from physical DuckDB types onto that vocabulary.

## Public interface

- Canonical type model:
  - `UnitType(name: UnitTypeName)` where `UnitTypeName = Literal["bool", "int", "float", "str", "date", "time", "timestamp", "uuid"]`.
  - `CustomType(module: str, qualname: str)` for an application-defined scalar.
  - `StructType(module: str, qualname: str)` for a declared `Struct` or `ComputedStruct`; `ShapeType` is the same type.
  - `ArrayType(item: LogicalType)`.
  - `NullableType(value: NonNullableLogicalType)`.
  - `NonNullableLogicalType = UnitType | CustomType | StructType | ArrayType`; `LogicalType = NonNullableLogicalType | NullableType`.
- Unit constants: `BOOL`, `INT`, `FLOAT`, `STR`, `DATE`, `TIME`, `TIMESTAMP`, `UUID`.
- Authoring markers:
  - `Array[T]` for an ordered collection.
  - `Nullable[T]` for the internal nullable marker; authors write `T | None`, not `Nullable[T]`.
  - `CustomDataType` as the base of an application-defined scalar.
  - `Shape` and `Struct` as declaration markers; a `Struct` is a value record, not a row source.
- Representative aliases: `Date = datetime.date`, `Time = datetime.time`, `Timestamp = datetime.datetime`, `Uuid = uuid.UUID`.
- `normalize_type(annotation: Any) -> LogicalType` converts one authoring annotation to canonical form.
- Validation functions:
  - `is_nullable(logical_type) -> bool`
  - `non_nullable(logical_type) -> UnitType | CustomType | StructType | ArrayType`
  - `array_item(logical_type) -> LogicalType | None`
  - `require_non_nullable(logical_type, *, context: str) -> LogicalType`
  - `require_scalar(logical_type, *, context: str) -> LogicalType`
  - `require_graph_property(logical_type, *, context: str) -> LogicalType`
- `canonical_value_text(value: Date | Time | Timestamp | Uuid) -> str` returns the one text form for a text-canonical unit.
- Shape registry: `register_shape(shape: type[Shape]) -> None` and `resolve_shape(module: str, qualname: str) -> type[Shape] | None` resolve generated shapes by the identity a logical type stores.
- Codecs:
  - `encode_type(logical_type) -> dict[str, Any]` and `decode_type(value) -> LogicalType`.
  - `encode_type_ir(value: LogicalTypeIR) -> dict[str, Any]` and `decode_type_ir(value) -> LogicalTypeIR`.
- Compilation mapping: `type_to_ir(logical_type: LogicalType) -> LogicalTypeIR`, with `UnitTypeIR`, `CustomTypeIR`, `StructTypeIR`, `ArrayTypeIR` and `NullableTypeIR`.
- DuckDB digest interface in `engines.interfaces`:
  - `DIGEST_TABLE: dict[str, TypeDigest]`.
  - `TypeDigest = CanonicalDigest | DeclaredOnlyDigest | RefusedDigest`.
  - `digest_for(value: str) -> TypeDigest | None`, where `None` means the name is unknown, not refused.
  - `canonical_type_name(value: str) -> str` removes a parameter list and upper-cases the family name.
  - `CANONICAL_SQL_TYPES`, `ArraySqlType`, `StructSqlType`, `SqlType` and `canonical_sql_type(value: SqlType) -> str`.
- Type errors are `TypeError` or `ValueError`. Canonical type construction rejects an unknown unit name, an empty module or qualname, and nested `NullableType`.

## Boundaries

- `types` imports nothing else from `kg_build_system`. It carries no expressions, declarations, bindings, topology, workflow or engine behaviour.
- Surfaces: `kg_build_system.types` is the author-facing vocabulary; `types.interfaces` is normalization, validation, codecs and the internal `Nullable` marker; `types.ir` is the logical-type IR.
- The mapping from a domain type to IR is one way; IR never retains a declaration class.
- `engines` may import `types.interfaces`; it is a leaf and must not import declarations, bindings, compile or workflow. The digest gate maps physical types to canonical types; it does not materialise values or plan relations.
- A target's capability set is not part of `types`. A target may narrow the canonical types it stores, but it may not invent a new canonical type.

## Current decisions

- **Canonical names are lowercase.** `bool`, `int`, `float`, `str`, `date`, `time`, `timestamp` and `uuid` are the only unit names. A capitalised spelling is a representative type, never a canonical name.
- **Representative types are aliases, not classes.** `Date`, `Time`, `Timestamp` and `Uuid` alias the stdlib classes the engine returns. Normalization dispatches on class identity, so `Field[Uuid]` and `Field[uuid.UUID]` are one declaration and cannot drift.
- **Canonical vocabulary.** A logical type is a unit, a custom scalar, a declared struct identity, an array, or a nullable wrapper. `CustomType` and `StructType` identify a declaration by `(module, qualname)`; the logical name is display only.
- **Arrays.** `ArrayType.item` is any logical type, including another array or a struct. Item nullability is independent of array nullability; `Array[T | None]` is a present array whose items may be null.
- **Nullability is flattened.** `NullableType` wraps only a non-nullable type and never wraps another `NullableType`. `T | None` normalizes once; nested nullability is rejected.
- **Normalization is explicit.**
  - `Any`, `list[T]`, `Sequence[T]`, `dict[K, V]`, tuples, and unions other than exactly one non-null member plus `None` are refused.
  - A `Struct` or `CustomDataType` declared inside a function is refused because it has no importable `(module, qualname)` identity.
  - A `Table`, `Projection` or other row source is refused as a field type with a redirect to `Struct` or `ComputedStruct`.
  - `Struct` and `ComputedStruct` normalize to `StructType`; a custom scalar normalizes to `CustomType`.
- **Source-field access is nullable.** A source declaration names the value type: `field()` strips a top-level `NullableType` from its annotation and access adds it back. A computed field keeps its expression's type, including expression nullability. Array item nullability stays in the declared value.
- **Struct identity is the declaration.** Two `Struct` or `ComputedStruct` classes with the same logical name in different modules are distinct. Generated shapes register under the same `(module, qualname)` identity and resolve without importing a module attribute.
- **Graph properties accept a flat value.** `require_graph_property` accepts a scalar (nullable or not) or a one-level array of non-null scalars. Custom scalars count as scalars. It rejects a struct, a nested array, and an array with nullable items; the error names the conversion (`expand()` or `drop_null_items()`).
- **Keys are present scalars.** A node build key and both edge endpoint keys must be non-null scalar expressions. Nullable scalars, arrays and structs are refused at the binding factory and again at blueprint validation. An array becomes key material only through `sort()`, `unique()` and `concat()`.
- **Targets may narrow capability.** Neo4j accepts `bool`, `int`, `float`, `str`, `date`, `time` and `timestamp` scalar properties; it refuses `uuid` and custom scalars. Its array properties hold `bool`, `int`, `float` or `str` items. The refusal happens at compile, never by coercion.

### DuckDB acceptance

The digest dispositions are:

| Disposition | Meaning |
| --- | --- |
| `canonical` | Digestible as reported, or through the widening cast the source view applies automatically. |
| `declared_only` | Digestible only through an author declaration, because the only available cast narrows the value or its precision. |
| `refused` | No meaning-preserving canonical type exists; the reason is recorded in the digest. |

- **Canonical units and containers:**
  - `BOOLEAN` → `bool`; `TINYINT`, `SMALLINT`, `INTEGER`, `BIGINT`, `UTINYINT`, `USMALLINT`, `UINTEGER` → `int` (widened to `BIGINT`).
  - `FLOAT`, `DOUBLE` → `float` (`FLOAT` is widened to `DOUBLE`; the stored value remains single precision).
  - `VARCHAR`, `JSON`, `ENUM` → `str`. `JSON` is a `VARCHAR` spelling; an enum's labels belong on the field as metadata.
  - `UUID` → `uuid`; `DATE` → `date`; `TIME` → `time`.
  - `TIMESTAMP`, `TIMESTAMP_S`, `TIMESTAMP_MS` → `timestamp`; `LIST`, `ARRAY` → `Array[item]`; `STRUCT` → `Struct{members}`.
- **Declared only:**
  - `UBIGINT`, `HUGEINT`, `UHUGEINT` → `int` through a checked cast to `BIGINT`; values outside the signed 64-bit range abort rather than wrap.
  - `TIME_NS` → `time` and `TIMESTAMP_NS` → `timestamp` through a silent cast to microsecond precision. The declaration is the only protection against the loss.
- **Refused:**
  - `DECIMAL` needs a parameterised `decimal(p, s)` type and result-width rules; division returns `DOUBLE`, so no division operator may be offered.
  - `BIGNUM` is an unbounded integer; `BIT` is a bit string; neither has a meaning-preserving canonical form.
  - `BLOB` has no total order, so core merge and deduplicate operations cannot carry it.
  - `TIME WITH TIME ZONE` has no chosen canonical zoned-time type.
  - `TIMESTAMP WITH TIME ZONE` is an instant, not a local date-time, and its fetched `tzinfo` depends on the session `TimeZone`.
  - `INTERVAL` is calendar-aware, not a fixed duration.
  - `MAP` is digestible only as an entries shape, which is not implemented.
  - `UNION` is a tagged sum; `VARIANT` is per-row self-describing typing; `ROW` is an anonymous record.
  - Untyped `NULL` is an absent declaration; `TYPE` is an internal pseudo-type; `GEOMETRY` and `GEOGRAPHY` are extension-conditional and not portable.
- **Aliases and unknown names.** `JSON`, `TIMETZ` and `TIMESTAMPTZ` resolve to the reported family before lookup. `digest_for` returns `None` for a name outside the table; an unknown physical type is not accepted by default.
- **Acceptance is only canonicalization.** A canonical `Array` or `Struct` may still be refused as a graph property. Property shape and target capability are separate checks.
- **SQL composition.** `CANONICAL_SQL_TYPES` maps units to `BOOLEAN`, `BIGINT`, `DOUBLE`, `VARCHAR`, `DATE`, `TIME`, `TIMESTAMP` and `UUID`; an array appends `[]`; a struct composes `STRUCT(name TYPE, ...)`. A bare container name is not a valid SQL type.
- **Canonical text.** `canonical_value_text` uses `isoformat()` for date, time and timestamp, which gives timestamps the `T` separator, and lowercase hyphenated text for uuid. Arrays and structs have no single text form.
