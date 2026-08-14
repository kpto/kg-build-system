"""Infer edit-time data contracts from supported data inputs."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import keyword
from pathlib import Path, PurePosixPath
import re
from typing import Any, ClassVar, Literal
from urllib.parse import urlparse

import duckdb
import fsspec
from fsspec import AbstractFileSystem

from ..models import (
    GeneratedClass,
    GeneratedArrayType,
    GeneratedField,
    GeneratedNullableType,
    GeneratedScalarType,
    GeneratedStructType,
    GeneratedMember, GeneratedFile, GeneratedPackage,
    GenerationError,
    ProviderGenerationConfig,
)
from ..providers import Provider, ProviderContext


_DATABASE_SUFFIXES = {".db", ".ddb", ".duckdb"}
_REMOTE_SCHEMES = {"http", "https", "s3"}
_DATA_SUFFIXES = {".csv", ".tsv", ".json", ".jsonl", ".ndjson", ".parquet", ".pq"}
_HIVE_PARTITION = re.compile(r"^[^/=]+=[^/]+$")
_SCALAR_TYPES = {
    "BOOLEAN": "bool",
    "TINYINT": "int",
    "SMALLINT": "int",
    "INTEGER": "int",
    "BIGINT": "int",
    "HUGEINT": "int",
    "UTINYINT": "int",
    "USMALLINT": "int",
    "UINTEGER": "int",
    "UBIGINT": "int",
    "FLOAT": "float",
    "REAL": "float",
    "DOUBLE": "float",
    "DECIMAL": "float",
    "VARCHAR": "str",
    "CHAR": "str",
    "BPCHAR": "str",
    "STRING": "str",
    "UUID": "str",
    "DATE": "str",
    "TIME": "str",
    "TIME WITH TIME ZONE": "str",
    "TIMESTAMP": "str",
    "TIMESTAMP WITH TIME ZONE": "str",
    "TIMESTAMP_S": "str",
    "TIMESTAMP_MS": "str",
    "TIMESTAMP_NS": "str",
}


def _identifier(value: str, *, fallback: str = "field") -> str:
    result = re.sub(r"[^A-Za-z0-9_]", "_", value)
    result = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", result).lower().strip("_") or fallback
    if result[0].isdigit():
        result = f"{fallback}_{result}"
    if keyword.iskeyword(result) or result == "options":
        result += "_"
    return result


def _class_part(value: str) -> str:
    words = [part for part in re.split(r"[^A-Za-z0-9]+", value) if part]
    result = "".join(part[:1].upper() + part[1:] for part in words) or "Relation"
    return f"Relation{result}" if result[0].isdigit() else result


def _split_top_level(value: str, separator: str = ",") -> tuple[str, ...]:
    result: list[str] = []
    depth = 0
    start = 0
    for index, character in enumerate(value):
        if character in "([<":
            depth += 1
        elif character in ")]>":
            depth -= 1
        elif character == separator and depth == 0:
            result.append(value[start:index].strip())
            start = index + 1
    result.append(value[start:].strip())
    return tuple(part for part in result if part)


def _base_type(value: str) -> str:
    return value.split("(", 1)[0].strip().upper()


def _field_for_type(
    *, name: str, type_name: str, nullable: bool, struct_prefix: str,
) -> tuple[GeneratedField, tuple[GeneratedClass, ...]]:
    normalized = type_name.strip()
    if normalized.endswith("[]"):
        item_type = normalized[:-2].strip()
        item_declarations: tuple[GeneratedClass, ...] = ()
        scalar = _SCALAR_TYPES.get(_base_type(item_type))
        if scalar is not None:
            generated_type = GeneratedScalarType(scalar)
        elif item_type.upper().startswith("STRUCT("):
            struct_field, item_declarations = _field_for_type(
                name=name,
                type_name=item_type,
                nullable=False,
                struct_prefix=struct_prefix,
            )
            generated_type = struct_field.value_type
        else:
            raise GenerationError(f"column {name!r} has unsupported collection item type {item_type!r}")
        value_type = GeneratedArrayType(generated_type)
        if nullable:
            value_type = GeneratedNullableType(value_type)
        return GeneratedField(
            _identifier(name), name, value_type,
        ), item_declarations
    scalar = _SCALAR_TYPES.get(_base_type(normalized))
    if scalar is not None:
        value_type = GeneratedScalarType(scalar)
        return GeneratedField(
            _identifier(name), name,
            GeneratedNullableType(value_type) if nullable else value_type,
        ), ()
    if normalized.upper().startswith("STRUCT(") and normalized.endswith(")"):
        struct_name = f"{struct_prefix}{_class_part(name)}Struct"
        members: list[GeneratedField] = []
        nested: list[GeneratedClass] = []
        for member in _split_top_level(normalized[7:-1]):
            match = re.match(r'(?s)^(?:"((?:[^"]|"")+)"|([^ ]+))\s+(.+)$', member)
            if match is None:
                raise GenerationError(f"cannot interpret struct member {member!r} in column {name!r}")
            member_name = (match.group(1) or match.group(2) or "").replace('""', '"')
            generated, generated_nested = _field_for_type(
                name=member_name, type_name=match.group(3), nullable=False, struct_prefix=struct_name,
            )
            members.append(generated)
            nested.extend(generated_nested)
        nested.append(GeneratedClass(struct_name, tuple(members), base="Struct"))
        value_type = GeneratedStructType(struct_name)
        return GeneratedField(
            _identifier(name), name,
            GeneratedNullableType(value_type) if nullable else value_type,
        ), tuple(nested)
    raise GenerationError(f"column {name!r} has unsupported type {type_name!r}")


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _remote_source(value: str) -> bool:
    """Whether ``value`` is a DuckDB-readable remote object URL."""
    return urlparse(value).scheme.lower() in _REMOTE_SCHEMES


def _source_suffix(value: str) -> str:
    """Return a source suffix without treating a URL query as part of its name."""
    return Path(urlparse(value).path if _remote_source(value) else value).suffix.lower()


def _source_stem(value: str) -> str:
    return Path(urlparse(value).path if _remote_source(value) else value).stem


def _load_remote_access(connection: duckdb.DuckDBPyConnection, source: str) -> None:
    """Enable DuckDB's URL and S3 filesystem support when a remote input needs it."""
    if not _remote_source(source):
        return
    try:
        connection.execute("LOAD httpfs")
    except duckdb.Error:
        try:
            connection.execute("INSTALL httpfs")
            connection.execute("LOAD httpfs")
        except duckdb.Error as error:
            raise GenerationError(
                f"cannot enable DuckDB httpfs support required for remote source {source!r}: {error}"
            ) from error


@dataclass(frozen=True)
class _LogicalTable:
    group_path: tuple[str, ...]
    name: str
    sources: tuple[str, ...]
    hive_partitioned: bool = False


def _filesystem_source(filesystem: AbstractFileSystem, path: str) -> str:
    value = filesystem.unstrip_protocol(path)
    if isinstance(value, str) and value.startswith("file://"):
        return str(Path(value[7:]).resolve())
    return str(value)


def _logical_tables(
    source: str,
    request_id: str,
    layout: Literal["files", "parquet_parts", "hive_partitioned_parquet"],
    *,
    anonymous: bool = False,
) -> tuple[_LogicalTable, ...]:
    """Walk a filesystem and collapse partitions/parts into logical datasets."""
    storage_options = {"anon": True} if urlparse(source).scheme.lower() == "s3" and anonymous else {}
    filesystem, root = fsspec.core.url_to_fs(source, **storage_options)
    if filesystem.isfile(root):
        return (_LogicalTable((), _source_stem(source), (source,)),)
    if not filesystem.isdir(root):
        raise GenerationError(f"data-contract inference input does not exist: {source}")

    root_path = PurePosixPath(str(root).replace("\\", "/").rstrip("/"))
    grouped: dict[tuple[tuple[str, ...], str], list[tuple[str, bool]]] = {}
    for raw_path in sorted(filesystem.find(root)):
        if not filesystem.isfile(raw_path):
            continue
        path = PurePosixPath(str(raw_path).replace("\\", "/"))
        suffix = path.suffix.lower()
        if suffix not in _DATA_SUFFIXES:
            continue
        if layout != "files" and suffix not in {".parquet", ".pq"}:
            continue
        try:
            relative = path.relative_to(root_path)
        except ValueError as error:
            raise GenerationError(f"filesystem returned a path outside the inference root: {raw_path}") from error
        parents = relative.parts[:-1]
        partitioned = layout == "hive_partitioned_parquet" and any(
            _HIVE_PARTITION.fullmatch(part) for part in parents
        )
        logical_parents = tuple(
            part for part in parents
            if layout != "hive_partitioned_parquet" or not _HIVE_PARTITION.fullmatch(part)
        )
        if layout != "files":
            if logical_parents:
                group_path, table_name = logical_parents[:-1], logical_parents[-1]
            else:
                group_path, table_name = (), request_id
        else:
            group_path, table_name = logical_parents, path.stem
        grouped.setdefault((group_path, table_name), []).append(
            (_filesystem_source(filesystem, str(raw_path)), partitioned)
        )
    if not grouped:
        raise GenerationError(f"data input {source} contains no supported relations")
    return tuple(
        _LogicalTable(group_path, name, tuple(item[0] for item in files), any(item[1] for item in files))
        for (group_path, name), files in sorted(grouped.items())
    )


class DataContractInferenceConfig(ProviderGenerationConfig):
    source: str
    relation: str | None = None
    mode: Literal["table", "table_group"] = "table"
    layout: Literal["files", "parquet_parts", "hive_partitioned_parquet"] = "files"
    anonymous: bool = False


class InferDataContractProvider(Provider[DataContractInferenceConfig]):
    """Infer portable table or table-group declarations from a data input."""

    ID: ClassVar[str] = "infer_data_contract"
    VERSION: ClassVar[str] = "2"
    CONFIG_TYPE: ClassVar[type[ProviderGenerationConfig]] = DataContractInferenceConfig

    @classmethod
    async def dependencies(cls, context: ProviderContext[DataContractInferenceConfig]) -> tuple[Path, ...]:
        return await asyncio.to_thread(cls._dependencies, context)

    @classmethod
    def _dependencies(cls, context: ProviderContext[DataContractInferenceConfig]) -> tuple[Path, ...]:
        if _remote_source(context.config.source):
            return ()
        source = context.resolve_path(context.config.source)
        if source.is_dir():
            return tuple(
                path for path in sorted(source.rglob("*"), key=lambda item: item.as_posix())
                if path.is_file() and path.suffix.lower() in {
                    ".csv", ".tsv", ".json", ".jsonl", ".ndjson", ".parquet", ".pq",
                }
            )
        return (source,)

    @classmethod
    def _relations(cls, connection: duckdb.DuckDBPyConnection, source: str) -> tuple[str, ...]:
        if _source_suffix(source) not in _DATABASE_SUFFIXES:
            return (_source_stem(source),)
        rows = connection.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema NOT IN ('information_schema', 'pg_catalog') ORDER BY table_name"
        ).fetchall()
        return tuple(str(row[0]) for row in rows)

    @classmethod
    def _describe(
        cls, connection: duckdb.DuckDBPyConnection, sources: tuple[str, ...], relation: str,
        *, hive_partitioned: bool = False,
    ) -> tuple[tuple[str, str, bool], ...]:
        source = sources[0]
        suffix = _source_suffix(source)
        if suffix in _DATABASE_SUFFIXES:
            query = f"SELECT * FROM {_quote_identifier(relation)}"
            parameters: list[Any] = []
        elif suffix in {".parquet", ".pq"}:
            query = "SELECT * FROM read_parquet(?, hive_partitioning = true)" if hive_partitioned else "SELECT * FROM read_parquet(?)"
            parameters = [source if len(sources) == 1 else list(sources)]
        elif suffix in {".csv", ".tsv"}:
            query, parameters = "SELECT * FROM read_csv_auto(?)", [source if len(sources) == 1 else list(sources)]
        elif suffix in {".json", ".jsonl", ".ndjson"}:
            query, parameters = "SELECT * FROM read_json_auto(?)", [source if len(sources) == 1 else list(sources)]
        else:
            raise GenerationError(f"unsupported data-contract inference input format {suffix or '<none>'!r}")
        try:
            rows = connection.execute(f"DESCRIBE {query}", parameters).fetchall()
        except duckdb.Error as error:
            raise GenerationError(f"cannot infer schema for {source} relation {relation!r}: {error}") from error
        # ``DESCRIBE`` is the schema boundary.  Do not scan source rows merely
        # to infer whether a nullable column happens to contain null values.
        return tuple((str(row[0]), str(row[1]), str(row[2]).upper() != "NO") for row in rows)

    @classmethod
    def _table_classes(
        cls, *, connection: duckdb.DuckDBPyConnection, sources: tuple[str, ...],
        relation: str, class_name: str, final: bool, hive_partitioned: bool = False,
    ) -> tuple[GeneratedClass, ...]:
        fields: list[GeneratedField] = []
        supporting: list[GeneratedClass] = []
        used: dict[str, str] = {}
        for external_name, type_name, nullable in cls._describe(
            connection, sources, relation, hive_partitioned=hive_partitioned,
        ):
            generated, nested = _field_for_type(
                name=external_name, type_name=type_name, nullable=nullable,
                struct_prefix=class_name,
            )
            previous = used.get(generated.python_name)
            if previous is not None:
                raise GenerationError(
                    f"columns {previous!r} and {external_name!r} collide as {generated.python_name!r}"
                )
            used[generated.python_name] = external_name
            fields.append(generated)
            supporting.extend(nested)
        if not fields:
            raise GenerationError(f"relation {relation!r} has no columns")
        return (
            *supporting,
            GeneratedClass(
                class_name,
                tuple(fields),
                base="Table" if final else None,
                declaration_name=relation if final else None,
            ),
        )

    @classmethod
    def _table_group_package(
        cls, context: ProviderContext[DataContractInferenceConfig], tables: tuple[_LogicalTable, ...],
        connection: duckdb.DuckDBPyConnection,
    ) -> GeneratedPackage:
        files: list[GeneratedFile] = []
        group_paths = {prefix for table in tables for size in range(len(table.group_path) + 1) for prefix in (table.group_path[:size],)}

        def group_class(path: tuple[str, ...]) -> str:
            return f"{''.join(_class_part(part) for part in path) or _class_part(context.request_id)}TableGroup"

        for table in tables:
            table_name = f"{_class_part(table.name)}Table"
            classes = cls._table_classes(
                connection=connection,
                sources=table.sources,
                relation=table.name,
                class_name=table_name,
                final=True,
                hive_partitioned=table.hive_partitioned,
            )
            relative = Path(*table.group_path) / f"{_identifier(table.name, fallback='table')}.py"
            files.append(GeneratedFile(relative, classes, (table_name,)))

        for group_path in sorted(group_paths, key=lambda value: (-len(value), value)):
            members = [
                GeneratedMember(_identifier(table.name, fallback="table"), f"{_class_part(table.name)}Table")
                for table in tables if table.group_path == group_path
            ]
            children = sorted({path[len(group_path)] for path in group_paths if len(path) == len(group_path) + 1 and path[:len(group_path)] == group_path})
            members.extend(
                GeneratedMember(_identifier(child, fallback="group"), group_class((*group_path, child)))
                for child in children
            )
            logical_name = group_path[-1] if group_path else context.request_id
            declaration = GeneratedClass(
                group_class(group_path),
                members=tuple(members),
                base="TableGroup",
                declaration_name=logical_name,
            )
            files.append(GeneratedFile(Path(*group_path) / "__init__.py", (declaration,), (declaration.name,)))
        return GeneratedPackage(tuple(files))

    @classmethod
    async def generate(
        cls, context: ProviderContext[DataContractInferenceConfig],
    ) -> GeneratedPackage:
        return await asyncio.to_thread(cls._generate, context)

    @classmethod
    def _generate(
        cls, context: ProviderContext[DataContractInferenceConfig],
    ) -> GeneratedPackage:
        remote = _remote_source(context.config.source)
        path = None if remote else context.resolve_path(context.config.source)
        source = context.config.source if remote else str(path)
        if context.config.layout != "files" and context.config.mode != "table_group":
            raise GenerationError(f"layout={context.config.layout!r} requires mode='table_group'")
        if context.config.mode == "table_group" and _source_suffix(source) not in _DATABASE_SUFFIXES:
            if context.config.relation is not None:
                raise GenerationError("table-group inference does not accept relation=")
            tables = _logical_tables(
                source,
                context.request_id,
                context.config.layout,
                anonymous=context.config.anonymous,
            )
            connection = duckdb.connect(":memory:")
            try:
                if any(_remote_source(item) for table in tables for item in table.sources):
                    _load_remote_access(connection, tables[0].sources[0])
                return cls._table_group_package(context, tables, connection)
            finally:
                connection.close()
        if path is not None and not path.exists():
            raise GenerationError(f"data-contract inference input does not exist: {path}")
        if path is not None and path.is_dir():
            raise GenerationError("directory inference requires mode='table_group'")
        is_database = not remote and _source_suffix(source) in _DATABASE_SUFFIXES
        try:
            connection = duckdb.connect(source if is_database else ":memory:", read_only=is_database)
        except duckdb.Error as error:
            raise GenerationError(f"cannot open data-contract inference input {path}: {error}") from error
        try:
            _load_remote_access(connection, source)
            relations = cls._relations(connection, source)
            if not relations:
                raise GenerationError(f"data input {path} exposes no relations")
            if context.config.mode == "table":
                if context.config.relation is None and len(relations) != 1:
                    raise GenerationError("table-contract inference requires relation= when the input exposes multiple relations")
                relation = context.config.relation or relations[0]
                if relation not in relations:
                    raise GenerationError(f"data input {path} has no relation {relation!r}")
                class_name = f"{_class_part(context.request_id)}Table"
                classes = cls._table_classes(
                    connection=connection, sources=(source,), relation=relation,
                    class_name=class_name, final=True,
                )
                return GeneratedPackage((GeneratedFile(Path("__init__.py"), classes, (class_name,)),))
            if context.config.relation is not None:
                raise GenerationError("table-group inference does not accept relation=")
            members: list[GeneratedMember] = []
            files: list[GeneratedFile] = []
            used_members: dict[str, str] = {}
            group_name = f"{_class_part(context.request_id)}TableGroup"
            for relation in relations:
                member_name = _identifier(relation, fallback="table")
                previous = used_members.get(member_name)
                if previous is not None:
                    raise GenerationError(f"relations {previous!r} and {relation!r} collide as {member_name!r}")
                used_members[member_name] = relation
                table_name = f"{_class_part(relation)}Table"
                classes = cls._table_classes(
                    connection=connection, sources=(source,), relation=relation,
                    class_name=table_name, final=True,
                )
                files.append(GeneratedFile(Path(f"{member_name}.py"), classes, (table_name,)))
                members.append(GeneratedMember(member_name, table_name))
            group = GeneratedClass(group_name, members=tuple(members), base="TableGroup", declaration_name=context.request_id)
            files.append(GeneratedFile(Path("__init__.py"), (group,), (group_name,)))
            return GeneratedPackage(tuple(files))
        finally:
            connection.close()
