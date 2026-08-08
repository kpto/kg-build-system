"""Infer edit-time data contracts from supported data inputs."""

from __future__ import annotations

import keyword
from pathlib import Path
import re
from typing import ClassVar, Literal

import duckdb

from ..models import (
    GeneratedClass,
    GeneratedField,
    GeneratedFieldKind,
    GeneratedMember,
    GeneratedModule,
    GenerationError,
    ProviderGenerationConfig,
)
from ..providers import Provider, ProviderContext


_DATABASE_SUFFIXES = {".db", ".ddb", ".duckdb"}
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
        scalar = _SCALAR_TYPES.get(_base_type(item_type))
        if scalar is None:
            raise GenerationError(f"column {name!r} has unsupported collection item type {item_type!r}")
        return GeneratedField(
            _identifier(name), name, GeneratedFieldKind.COLLECTION, scalar,
            nullable=nullable, item_nullable=True,
        ), ()
    scalar = _SCALAR_TYPES.get(_base_type(normalized))
    if scalar is not None:
        return GeneratedField(_identifier(name), name, GeneratedFieldKind.SCALAR, scalar, nullable=nullable), ()
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
                name=member_name, type_name=match.group(3), nullable=True, struct_prefix=struct_name,
            )
            members.append(generated)
            nested.extend(generated_nested)
        nested.append(GeneratedClass(struct_name, tuple(members), base="Struct"))
        return GeneratedField(
            _identifier(name), name, GeneratedFieldKind.STRUCT, struct_name, nullable=nullable,
        ), tuple(nested)
    raise GenerationError(f"column {name!r} has unsupported type {type_name!r}")


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


class DataContractInferenceConfig(ProviderGenerationConfig):
    source: str
    relation: str | None = None
    mode: Literal["table", "table_group"] = "table"


class InferDataContractProvider(Provider[DataContractInferenceConfig]):
    """Infer portable table or table-group declarations from a data input."""

    ID: ClassVar[str] = "infer_data_contract"
    VERSION: ClassVar[str] = "1"
    CONFIG_TYPE: ClassVar[type[ProviderGenerationConfig]] = DataContractInferenceConfig

    @classmethod
    def dependencies(cls, context: ProviderContext[DataContractInferenceConfig]) -> tuple[Path, ...]:
        return (context.resolve_path(context.config.source),)

    @classmethod
    def _relations(cls, connection: duckdb.DuckDBPyConnection, path: Path) -> tuple[str, ...]:
        if path.suffix.lower() not in _DATABASE_SUFFIXES:
            return (path.stem,)
        rows = connection.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema NOT IN ('information_schema', 'pg_catalog') ORDER BY table_name"
        ).fetchall()
        return tuple(str(row[0]) for row in rows)

    @classmethod
    def _describe(
        cls, connection: duckdb.DuckDBPyConnection, path: Path, relation: str,
    ) -> tuple[tuple[str, str, bool], ...]:
        suffix = path.suffix.lower()
        if suffix in _DATABASE_SUFFIXES:
            query = f"SELECT * FROM {_quote_identifier(relation)}"
            parameters: list[str] = []
        elif suffix in {".parquet", ".pq"}:
            query, parameters = "SELECT * FROM read_parquet(?)", [str(path)]
        elif suffix in {".csv", ".tsv"}:
            query, parameters = "SELECT * FROM read_csv_auto(?)", [str(path)]
        elif suffix in {".json", ".jsonl", ".ndjson"}:
            query, parameters = "SELECT * FROM read_json_auto(?)", [str(path)]
        else:
            raise GenerationError(f"unsupported data-contract inference input format {suffix or '<none>'!r}")
        try:
            rows = connection.execute(f"DESCRIBE {query}", parameters).fetchall()
        except duckdb.Error as error:
            raise GenerationError(f"cannot infer schema for {path} relation {relation!r}: {error}") from error
        return tuple((str(row[0]), str(row[1]), str(row[2]).upper() != "NO") for row in rows)

    @classmethod
    def _table_classes(
        cls, *, connection: duckdb.DuckDBPyConnection, path: Path,
        relation: str, class_name: str, final: bool,
    ) -> tuple[GeneratedClass, ...]:
        fields: list[GeneratedField] = []
        supporting: list[GeneratedClass] = []
        used: dict[str, str] = {}
        for external_name, type_name, nullable in cls._describe(connection, path, relation):
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
        return (*supporting, GeneratedClass(class_name, tuple(fields), base="Table" if final else None))

    @classmethod
    def generate(
        cls, context: ProviderContext[DataContractInferenceConfig], *, generated_name: str,
    ) -> GeneratedModule:
        path = cls.dependencies(context)[0]
        if not path.is_file():
            raise GenerationError(f"data-contract inference input does not exist: {path}")
        is_database = path.suffix.lower() in _DATABASE_SUFFIXES
        try:
            connection = duckdb.connect(str(path) if is_database else ":memory:", read_only=is_database)
        except duckdb.Error as error:
            raise GenerationError(f"cannot open data-contract inference input {path}: {error}") from error
        try:
            relations = cls._relations(connection, path)
            if not relations:
                raise GenerationError(f"data input {path} exposes no relations")
            if context.config.mode == "table":
                if context.config.relation is None and len(relations) != 1:
                    raise GenerationError("table-contract inference requires relation= when the input exposes multiple relations")
                relation = context.config.relation or relations[0]
                if relation not in relations:
                    raise GenerationError(f"data input {path} has no relation {relation!r}")
                return GeneratedModule(cls._table_classes(
                    connection=connection, path=path, relation=relation,
                    class_name=generated_name, final=False,
                ))
            if context.config.relation is not None:
                raise GenerationError("table-group inference does not accept relation=")
            classes: list[GeneratedClass] = []
            members: list[GeneratedMember] = []
            used_members: dict[str, str] = {}
            for relation in relations:
                member_name = _identifier(relation, fallback="table")
                previous = used_members.get(member_name)
                if previous is not None:
                    raise GenerationError(f"relations {previous!r} and {relation!r} collide as {member_name!r}")
                used_members[member_name] = relation
                table_name = f"{generated_name}{_class_part(relation)}Table"
                classes.extend(cls._table_classes(
                    connection=connection, path=path, relation=relation,
                    class_name=table_name, final=True,
                ))
                members.append(GeneratedMember(member_name, table_name))
            classes.append(GeneratedClass(generated_name, members=tuple(members)))
            return GeneratedModule(tuple(classes))
        finally:
            connection.close()
