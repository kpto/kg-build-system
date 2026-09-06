"""Turn a framework contract-inference result into IR document sections.

Data-shape import has to produce the same thing the studio would have authored:
document tables and structs, not files on disk. The framework's
``InferDataContractProvider`` already classifies every column into a canonical type
and applies the three-tier nullability policy, so the studio calls it and maps its
:class:`GeneratedPackage` into the document. Nothing here re-implements inference.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kg_build_system.code_generation.builtins import (
    DataContractInferenceConfig,
    InferDataContractProvider,
)
from kg_build_system.code_generation.models import (
    GeneratedArrayType,
    GeneratedClass,
    GeneratedField,
    GeneratedFile,
    GeneratedNullableType,
    GeneratedPackage,
    GeneratedScalarType,
    GeneratedStructType,
    GeneratedType,
)
from kg_build_system.code_generation.providers import ProviderContext

from .ir.document import (
    ArrayType,
    DataField,
    LogicalType,
    NullableType,
    ProjectDocument,
    Source,
    Struct,
    StructType,
    Table,
    TableGroupMember,
    UnitType,
)
from .ir.names import snake

_MODES = ("table", "table_group")


@dataclass(frozen=True, slots=True)
class InferredShape:
    tables: tuple[Table, ...]
    structs: tuple[Struct, ...]
    sources: tuple[Source, ...]
    notes: tuple[str, ...]

    def merge_into(self, document: ProjectDocument) -> ProjectDocument:
        """Add the inferred declarations, leaving anything already declared alone."""
        tables = list(document.tables)
        existing_tables = {table.id for table in tables}
        for table in self.tables:
            if table.id not in existing_tables:
                tables.append(table)
        structs = list(document.structs)
        existing_structs = {struct.id for struct in structs}
        for struct in self.structs:
            if struct.id not in existing_structs:
                structs.append(struct)
        sources = list(document.sources)
        existing_sources = {source.id for source in sources}
        for source in self.sources:
            if source.id not in existing_sources:
                sources.append(source)
        return document.updated(tables=tables, structs=structs, sources=sources)


async def infer_shape(
    *,
    project_root: Path,
    package: str,
    location: str,
    mode: str = "table",
    layout: str | None = None,
    relation: str | None = None,
    override: dict[str, dict[str, Any]] | None = None,
    request_id: str | None = None,
) -> InferredShape:
    """Observe one data location and express it as tables, structs and a source."""
    if mode not in _MODES:
        raise ValueError(f"mode must be one of {_MODES}")
    identifier = request_id or snake(Path(location).stem or "imported")
    # The provider resolves its source against the request file's directory, so the
    # studio hands it an absolute path derived from the project root; the document
    # keeps the project-relative spelling so it stays portable.
    observed = str((project_root / location).resolve())
    config_kwargs: dict[str, Any] = {"source": observed, "mode": mode}
    if layout is not None:
        config_kwargs["layout"] = layout
    if relation is not None:
        config_kwargs["relation"] = relation
    if override is not None:
        config_kwargs["override"] = override
    config = DataContractInferenceConfig(**config_kwargs)
    context = ProviderContext(
        project_root=project_root,
        request_path=project_root / package / "table" / "__init__.py",
        request_id=identifier,
        config=config,
    )
    package_result = await InferDataContractProvider.generate(context)
    return _to_shape(
        package=package,
        table_id=identifier,
        generated=package_result,
        location=location,
        mode=mode,
        layout=layout,
    )


def _to_shape(
    *,
    package: str,
    table_id: str,
    generated: GeneratedPackage,
    location: str,
    mode: str,
    layout: str | None,
) -> InferredShape:
    del layout  # the provider's layout choice is an input to inference, not a document field
    structs: list[Struct] = []
    tables: list[Table] = []
    groups: list[GeneratedClass] = []
    # Struct identity is (name, declaring file); the document keys them by id, so a
    # file prefix keeps same-named records in different tables distinct.
    file_prefix: dict[str, str] = {}
    for index, file in enumerate(generated.files):
        file_prefix[file.relative_path.as_posix()] = _file_prefix(file, index, table_id)

    for file in generated.files:
        for declaration in file.declarations:
            if declaration.base == "Struct":
                structs.append(_struct(file_prefix[file.relative_path.as_posix()], declaration))
            elif declaration.base == "TableGroup":
                groups.append(declaration)
            else:
                tables.append(_table(declaration))

    by_declaration = {table.declaration_name: table for table in tables}
    for group in groups:
        members: list[TableGroupMember] = []
        for member in group.members:
            target = by_declaration.get(member.declaration_name)
            if target is None:
                continue
            # The models are frozen, so re-parenting means replacing the entry.
            index = tables.index(target)
            tables[index] = target.updated(group=_group_id(group))
            members.append(TableGroupMember(python_name=member.python_name, ref=target.id))
        tables.append(
            Table(
                id=_group_id(group),
                declaration_name=group.name,
                name=_group_id(group),
                description=group.description,
                members=tuple(members),
            )
        )

    notes = tuple(note.line for note in generated.nullability_notes)
    return InferredShape(
        tables=tuple(tables),
        structs=tuple(structs),
        sources=(_source(table_id, tables, groups, location, mode),),
        notes=notes,
    )


def _source(
    table_id: str,
    tables: list[Table],
    groups: list[GeneratedClass],
    location: str,
    mode: str,
) -> Source:
    """The physical binding for what was just inferred.

    A group source is anchored one level *above* the group's directory, because the
    framework resolves ``{group_path}`` starting at the root group's own name — the
    layout then rebuilds the directory the files were observed in.
    """
    if mode == "table_group" or groups:
        return Source(
            id=table_id,
            table=table_id,
            location=Path(location).parent.as_posix(),
            format=_format(location),
            layout="{group_path}/{table_name}.json",
        )
    table = tables[0] if tables else None
    return Source(
        id=table.id if table is not None else table_id,
        table=table.id if table is not None else table_id,
        location=Path(location).as_posix(),
        format=_format(location),
    )


def _file_prefix(file: GeneratedFile, index: int, table_id: str) -> str:
    """The id prefix for structs declared by one file.

    A single relation's package is ``__init__.py``, whose own name carries nothing, so
    the request identity prefixes it: struct ids read ``pathways_steps_struct`` and
    stay stable when the same feed is re-imported.
    """
    stem = file.relative_path.stem
    if stem == "__init__":
        parent = file.relative_path.parent.name
        return snake(parent) if parent else snake(table_id)
    return snake(stem)


def _group_id(declaration: GeneratedClass) -> str:
    return snake(declaration.name.removesuffix("TableGroup"))


def _struct(prefix: str, declaration: GeneratedClass) -> Struct:
    return Struct(
        id=f"{prefix}_{snake(declaration.name)}",
        declaration_name=declaration.name,
        name=snake(declaration.name.removesuffix("Struct")),
        description=declaration.description,
        fields=_fields(declaration.fields),
    )


def _table(declaration: GeneratedClass) -> Table:
    return Table(
        id=snake(declaration.name.removesuffix("Table")),
        declaration_name=declaration.name,
        name=snake(declaration.name.removesuffix("Table")),
        description=declaration.description,
        fields=_fields(declaration.fields),
    )


def _fields(fields: tuple[GeneratedField, ...]) -> tuple[DataField, ...]:
    result: list[DataField] = []
    for field in fields:
        result.append(
            DataField(
                name=snake(field.python_name),
                logical_type=_logical_type(field.value_type),
                description=field.description,
                external_name=field.external_name if field.external_name != field.python_name else None,
                nullability=field.nullability.value,
                schema_path=field.schema_path or field.logical_path,
            )
        )
    return tuple(result)


def _logical_type(value: GeneratedType) -> LogicalType:
    if isinstance(value, GeneratedScalarType):
        return UnitType(name=value.name)  # type: ignore[arg-type]
    if isinstance(value, GeneratedNullableType):
        inner = _logical_type(value.value)
        if isinstance(inner, NullableType):
            return inner
        return NullableType(value=inner)  # type: ignore[arg-type]
    if isinstance(value, GeneratedArrayType):
        return ArrayType(item=_logical_type(value.item))
    if isinstance(value, GeneratedStructType):
        return StructType(module="", qualname=value.declaration_name)
    raise TypeError(f"unsupported generated type {value!r}")


def _format(location: str) -> str:
    suffix = Path(location).suffix.lower()
    if suffix in {".ndjson", ".jsonl", ".json"} or suffix == "":
        return "json"
    if suffix in {".csv", ".tsv"}:
        return "csv"
    if suffix in {".parquet", ".pq"}:
        return "parquet"
    return "json"


def _relative(location: str) -> str:
    return Path(location).as_posix()
