# DuckDB type acceptance matrix

Measured against duckdb 1.5.5. Every row was executed rather than asserted: a value of the source
type was built, the normalising cast the design says the source view should apply was applied, and
both the reported SQL type and the Python object the client hands back were confirmed. All 41 rows
agreed with the design.

This document is the normative record of that measurement. The validation itself belongs in the test
suite, asserting the shipped DuckDB-to-canonical table against `duckdb_types()`, so that a DuckDB
upgrade which adds or renames a type fails a test rather than quietly leaving this table stale.

## Dispositions

| Disposition | Meaning | Types |
| --- | --- | --- |
| `accept` | Digestible as-is or by a widening cast applied automatically at the scan. | 22 |
| `declared` | Digestible only through an author-declared override, because the only available cast narrows the value or its precision. | 5 |
| `reject` | No meaning-preserving canonical type exists yet; the reason is recorded per row. | 14 |

## Matrix

| DuckDB type | Disposition | Canonical type | Graph property | Normalising cast | Reports after cast | Client returns | Representative Python type | Verdict | Note |
|---|---|---|---|---|---|---|---|---|---|
| BOOLEAN | accept | bool | yes | identity | BOOLEAN | bool | bool | verified |  |
| TINYINT | accept | int | yes | CAST(value AS BIGINT) | BIGINT | int | int | verified | widening |
| SMALLINT | accept | int | yes | CAST(value AS BIGINT) | BIGINT | int | int | verified | widening |
| INTEGER | accept | int | yes | CAST(value AS BIGINT) | BIGINT | int | int | verified | widening |
| BIGINT | accept | int | yes | identity | BIGINT | int | int | verified |  |
| UTINYINT | accept | int | yes | CAST(value AS BIGINT) | BIGINT | int | int | verified | widening |
| USMALLINT | accept | int | yes | CAST(value AS BIGINT) | BIGINT | int | int | verified | widening |
| UINTEGER | accept | int | yes | CAST(value AS BIGINT) | BIGINT | int | int | verified | widening |
| UBIGINT | declared | int | yes | CAST(value AS BIGINT) | BIGINT | int | int | verified | narrowing above 2^63-1 only, and it must never wrap; measured: checked: aborts outside range (Conversion Error: Type UINT64 with value 184) |
| HUGEINT | declared | int | yes | CAST(value AS BIGINT) | BIGINT | int | int | verified | engine-checked narrowing; without it Parquet export degrades HUGEINT to DOUBLE; measured: checked: aborts outside range (Conversion Error: Type INT128 with value 170) |
| UHUGEINT | declared | int | yes | CAST(value AS BIGINT) | BIGINT | int | int | verified | narrowing to the signed 64-bit domain; measured: checked: aborts outside range (Conversion Error: Type UINT128 with value 34) |
| BIGNUM | reject | - | - | none | - | str | str | design row (no cast to verify) | unbounded integer: decimal is bounded and str would change its meaning; the client also hands BIGNUM over as text |
| FLOAT | accept | float | yes | CAST(value AS DOUBLE) | DOUBLE | float | float | verified | widening fixes the arithmetic width only: the stored value is already single precision |
| DOUBLE | accept | float | yes | identity | DOUBLE | float | float | verified |  |
| DECIMAL(10,2) | reject | decimal(p, s) | - | none | - | decimal.Decimal | decimal.Decimal | design row (no cast to verify) | deferred: needs a parameterised canonical type plus DuckDB result-width rules; DECIMAL division returns DOUBLE, so no division operator may be offered |
| VARCHAR | accept | str | yes | identity | VARCHAR | str | str | verified |  |
| JSON | accept | str | yes | CAST(value AS VARCHAR) | VARCHAR | str | str | verified | JSON is a VARCHAR spelling, so .id cannot distinguish the two |
| UUID | accept | Uuid | yes | identity | UUID | uuid.UUID | uuid.UUID | verified | own canonical type: an identifier that merely has a canonical text form, carried unchanged with no cast and no conversion |
| BIT | reject | - | - | none | - | str | str | design row (no cast to verify) | rare; a str canonical would be cheap to add |
| BLOB | reject | binary | - | none | - | bytes | bytes | design row (no cast to verify) | deferred: no total order, so the core operators cannot merge or deduplicate it |
| DATE | accept | date | yes | identity | DATE | datetime.date | datetime.date | verified |  |
| TIME | accept | time | yes | identity | TIME | datetime.time | datetime.time | verified |  |
| TIME_NS | declared | time | yes | CAST(value AS TIME) | TIME | datetime.time | datetime.time | verified | unchecked narrowing: DuckDB rounds nanoseconds silently, so only the declaration protects the value; measured: silent: 10:00:00.123456789 becomes 10:00:00.123457 |
| TIME WITH TIME ZONE | reject | - | - | none | - | datetime.time | datetime.time | design row (no cast to verify) | a zoned time of day has no canonical type chosen |
| TIMESTAMP | accept | timestamp | yes | identity | TIMESTAMP | datetime.datetime | datetime.datetime | verified |  |
| TIMESTAMP_S | accept | timestamp | yes | CAST(value AS TIMESTAMP) | TIMESTAMP | datetime.datetime | datetime.datetime | verified | widening |
| TIMESTAMP_MS | accept | timestamp | yes | CAST(value AS TIMESTAMP) | TIMESTAMP | datetime.datetime | datetime.datetime | verified | widening |
| TIMESTAMP_NS | declared | timestamp | yes | CAST(value AS TIMESTAMP) | TIMESTAMP | datetime.datetime | datetime.datetime | verified | unchecked narrowing: nanoseconds are dropped silently, and Python datetimes cannot hold them either; measured: silent: 2026-01-01 10:00:00.123456789 becomes 2026-01-01 10:00:00.123456 |
| TIMESTAMP WITH TIME ZONE | reject | instant | - | none | - | datetime.datetime | datetime.datetime with tzinfo | design row (no cast to verify) | deferred: an instant and a local date-time are different types, and the fetched tzinfo comes from the session TimeZone rather than the data |
| INTERVAL | reject | interval | - | none | - | datetime.timedelta | datetime.timedelta | design row (no cast to verify) | deferred: calendar-aware months are not a duration value |
| INTEGER[] | accept | Array[int] | no | CAST(value AS BIGINT[]) | BIGINT[] | list | list | verified | element-wise widening |
| INTEGER[3] | accept | Array[int] | no | CAST(value AS BIGINT[]) | BIGINT[] | tuple | list | verified | fixed length widens to a list; the client hands arrays over as tuples, which the cast removes |
| STRUCT(a INTEGER) | accept | Struct{a: int} | no | CAST(value AS STRUCT(a BIGINT)) | STRUCT(a BIGINT) | dict | dict | verified | members widened element-wise |
| MAP(INTEGER, VARCHAR) | reject | Array[Struct{key, value}] | - | none | - | dict | dict | design row (no cast to verify) | digestible through the entries representation, but the nested-shape work is deferred |
| UNION(num INTEGER, txt VARCHAR) | reject | - | - | none | - | int | int | design row (no cast to verify) | a tagged sum has no framework analogue and the client drops the tag |
| VARIANT | reject | - | - | none | - | int | int | design row (no cast to verify) | per-row self-describing typing has no canonical form and the client drops it |
| ENUM('a', 'b') | accept | str | yes | CAST(value AS VARCHAR) | VARCHAR | str | str | verified | the permitted label set belongs on the field as metadata, not in the type |
| ROW (anonymous struct) | reject | - | - | none | - | tuple | tuple | design row (no cast to verify) | an anonymous record has no field names to declare |
| untyped NULL | reject | - | - | none | - | NoneType | NoneType | design row (no cast to verify) | an untyped NULL column is an absent declaration; DESCRIBE reports INTEGER for it |
| TYPE | reject | - | - | none | - | NoneType | NoneType | design row (no cast to verify) | internal pseudo-type |
| GEOMETRY | reject | - | - | none | - | NoneType | NoneType | design row (no cast to verify) | extension-conditional, so a definition using it is not portable |

## Canonical vocabulary

A canonical type is named for what it means in the framework, not for the Python builtin whose name it could have borrowed. `Uuid` is a canonical type rather than `str` because a UUID is an identifier that merely has a canonical text form, and the client already carries it as `uuid.UUID` with no cast and no conversion.

- Usable as a graph property or key: `bool`, `date`, `float`, `int`, `str`, `time`, `timestamp`, `Uuid`.
- Values that must be flattened before they can become a property: `Array[int]`, `Struct{a: int}`.

### Representative types

Two vocabularies, deliberately distinct. The canonical name is the identity carried by the logical
type, the IR, codecs and messages. The representative type is what an author writes in an annotation,
and it must be the very class of the value the client returns, because `ValueExpression[T]`,
`ValueSelection[T]` and `PropertySlot[T]` are all parameterised by it.

| Canonical name | Representative type | Class it denotes | Imported from |
| --- | --- | --- | --- |
| `bool`, `int`, `float`, `str` | `bool`, `int`, `float`, `str` | the builtins | builtins, no import |
| `date` | `Date` | `datetime.date` | `kg_build_system.types` |
| `time` | `Time` | `datetime.time` | `kg_build_system.types` |
| `timestamp` | `Timestamp` | `datetime.datetime` | `kg_build_system.types` |
| `Uuid` | `Uuid` | `uuid.UUID` | `kg_build_system.types` |

The representative types are exposed by `kg_build_system.types`, alongside the `Array`, `Nullable`,
`Struct` and `CustomDataType` markers already exported there, and are aliases of the stdlib classes
rather than new classes. Capitalised names keep the family consistent and avoid the `import time` and
`from datetime import date` bindings that are common in author code. `normalize_type` dispatches on
class identity, so the alias spelling and the stdlib spelling are the same annotation and cannot
drift into two meanings.

Generated files import the whole representative set from `kg_build_system.types` unconditionally,
rather than deriving the import list per file from what that file happens to use:

```python
# Generated by kg-build-system. Do not edit manually.
from kg_build_system import Field, Struct, Table, TableOptions, field
from kg_build_system.types import Array, Date, Time, Timestamp, Uuid

class SurveysTable(Table):
    options = TableOptions(name='surveys')
    surveyed_on: Field[Timestamp | None] = field(name='surveyed_on')
```

Importing unconditionally is what makes an un-imported annotation impossible rather than merely
unlikely: without `from __future__ import annotations`, a name a generated file failed to import
raises `NameError` while the class body executes, before any framework code runs. The same rule lets
the value-type marker `Array` join that line and removes the per-file usage derivation the renderer
does today.

## What the declared narrowings do

Engine-checked narrowings abort; silent narrowings rewrite the value, so the declaration is the only protection and belongs in front of the author rather than in a default.

| DuckDB type | Cast | Behaviour |
| --- | --- | --- |
| `UBIGINT` | `CAST(value AS BIGINT)` | checked: aborts outside range (Conversion Error: Type UINT64 with value 184) |
| `HUGEINT` | `CAST(value AS BIGINT)` | checked: aborts outside range (Conversion Error: Type INT128 with value 170) |
| `UHUGEINT` | `CAST(value AS BIGINT)` | checked: aborts outside range (Conversion Error: Type UINT128 with value 34) |
| `TIME_NS` | `CAST(value AS TIME)` | silent: 10:00:00.123456789 becomes 10:00:00.123457 |
| `TIMESTAMP_NS` | `CAST(value AS TIMESTAMP)` | silent: 2026-01-01 10:00:00.123456789 becomes 2026-01-01 10:00:00.123456 |

## Why the rejected types are rejected

| DuckDB type | Deferred canonical | Reason |
| --- | --- | --- |
| `BIGNUM` | — | unbounded integer: decimal is bounded and str would change its meaning; the client also hands BIGNUM over as text |
| `DECIMAL(10,2)` | `decimal(p, s)` | deferred: needs a parameterised canonical type plus DuckDB result-width rules; DECIMAL division returns DOUBLE, so no division operator may be offered |
| `BIT` | — | rare; a str canonical would be cheap to add |
| `BLOB` | `binary` | deferred: no total order, so the core operators cannot merge or deduplicate it |
| `TIME WITH TIME ZONE` | — | a zoned time of day has no canonical type chosen |
| `TIMESTAMP WITH TIME ZONE` | `instant` | deferred: an instant and a local date-time are different types, and the fetched object takes its tzinfo from the session `TimeZone` setting rather than from the data, so materialising an instant is machine-dependent until that setting is pinned |
| `INTERVAL` | `interval` | deferred: calendar-aware months are not a duration value |
| `MAP(INTEGER, VARCHAR)` | `Array[Struct{key, value}]` | digestible through the entries representation, but the nested-shape work is deferred |
| `UNION(num INTEGER, txt VARCHAR)` | — | a tagged sum has no framework analogue and the client drops the tag |
| `VARIANT` | — | per-row self-describing typing has no canonical form and the client drops it |
| `ROW (anonymous struct)` | — | an anonymous record has no field names to declare |
| `untyped NULL` | — | an untyped NULL column is an absent declaration; DESCRIBE reports INTEGER for it |
| `TYPE` | — | internal pseudo-type |
| `GEOMETRY` | — | extension-conditional, so a definition using it is not portable |

## Verification

41 of 41 rows agree with the design.
