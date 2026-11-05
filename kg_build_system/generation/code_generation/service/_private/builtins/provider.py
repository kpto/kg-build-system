"""The built-in data-contract inference provider.

The provider owns orchestration only. Formats, datasets, observation,
nullability, mapping, shapes, naming, overrides and provenance each live in
their own module and expose functions.
"""
from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path, PurePosixPath
from typing import ClassVar

import duckdb

from ....model._private.generated import (
    GeneratedAsset, GeneratedClass, GeneratedFile, GeneratedMember,
    GeneratedPackage, Nullability, NullabilityNote,
)
from ....model.public.errors import GenerationError
from ..adapters import resolve_provider_path
from ....model.internal.providers import (
    Provider, ProviderContext, ProviderGenerationConfig,
)
from .config import DataContractInferenceConfig
from .datasets import LogicalTable, logical_tables
from .formats import DATABASE_SUFFIXES, PARQUET_SUFFIXES, remote_source, source_suffix, tier_for_suffix
from .naming import (
    bind_records, class_part, group_class_name, identifier, table_class_name,
)
from .observation import (
    connect, describe, load_remote_access, parquet_schema_rows, relations,
)
from .overrides import declared_overrides, require_overrides
from .provenance import nullability_note, report_null_statistics, schema_digest, schema_facts
from .shapes import members, node_shape, parquet_trees
from .state import Inference


def _generated_asset(
    context: ProviderContext[DataContractInferenceConfig],
) -> GeneratedAsset | None:
    asset = context.asset
    if asset is None:
        return None
    return GeneratedAsset(asset.module, asset.qualname)


def _source(context: ProviderContext[DataContractInferenceConfig]) -> str:
    """The configured source, or the decorated asset layout's locator."""
    if context.config.source is not None:
        return context.config.source
    asset = context.asset
    layout = None if asset is None else asset.options.layout
    if layout is not None and layout.locator is not None:
        return layout.locator
    raise GenerationError(
        "data-contract inference requires source= or an asset layout with a locator"
    )


class InferDataContractProvider(Provider[DataContractInferenceConfig]):
    """Infer portable table or table-group declarations from a data input.

    The configured source is observed when a request is generated or the
    project is explicitly regenerated, never tracked: its location is a
    reference, and the observed schema's digest rides along in the manifest
    as provenance.
    """

    ID: ClassVar[str] = "infer_data_contract"
    VERSION: ClassVar[str] = "8"
    CONFIG_TYPE: ClassVar[type[ProviderGenerationConfig]] = DataContractInferenceConfig

    @classmethod
    def _table_classes(
        cls,
        *,
        connection: duckdb.DuckDBPyConnection,
        sources: tuple[str, ...],
        relation: str,
        relation_path: str,
        class_name: str,
        final: bool,
        hive_partitioned: bool = False,
        inference: Inference,
        asset: GeneratedAsset | None = None,
    ) -> tuple[GeneratedClass, ...]:
        fields = []
        supporting: list[GeneratedClass] = []
        inference.used_names = {}
        described = describe(
            connection, sources, relation, hive_partitioned=hive_partitioned,
        )
        try:
            rows = (
                parquet_schema_rows(connection, sources)
                if source_suffix(sources[0]) in PARQUET_SUFFIXES else ()
            )
            nodes = parquet_trees(rows) if rows else ()
            for field_, nested in members(
                described=described,
                nodes=nodes,
                sources=sources,
                relation_path=relation_path,
                inference=inference,
            ):
                previous = inference.used_names.get(field_.python_name)
                if previous is not None:
                    raise GenerationError(
                        f"columns {previous!r} and {field_.external_name!r} "
                        f"collide as {field_.python_name!r}"
                    )
                inference.used_names[field_.python_name] = field_.external_name
                fields.append(field_)
                supporting.extend(nested)
            if not fields:
                raise GenerationError(f"relation {relation!r} has no columns")
            inference.columns[relation_path] = {field.external_name for field in fields}
            inference.schema_facts.extend(schema_facts(
                class_name=class_name, relation=relation, sources=sources,
                hive_partitioned=hive_partitioned, described=described,
                node_shape=node_shape(nodes),
            ))
        except GenerationError as error:
            resource = sources[0]
            additional = (
                f" and {len(sources) - 1} additional resources"
                if len(sources) > 1 else ""
            )
            raise GenerationError(
                f"cannot generate data contract for resource {resource!r}{additional} "
                f"relation {relation!r}: {error}"
            ) from error
        report_null_statistics(
            connection, sources,
            {
                field.schema_path for field in fields
                if field.nullability is not Nullability.DEFAULTED
            },
        )
        return (
            *supporting,
            GeneratedClass(
                class_name,
                tuple(fields),
                base="Table" if final else None,
                declaration_name=relation if final else None,
                asset=asset if final else None,
            ),
        )

    @classmethod
    def _table_group_package(
        cls,
        context: ProviderContext[DataContractInferenceConfig],
        tables: tuple[LogicalTable, ...],
        connection: duckdb.DuckDBPyConnection,
        inference: Inference,
    ) -> GeneratedPackage:
        files: list[GeneratedFile] = []
        notes: dict[str, NullabilityNote] = {}
        group_paths = {
            prefix for table in tables
            for size in range(len(table.group_path) + 1)
            for prefix in (table.group_path[:size],)
        }
        for table in tables:
            table_name = table_class_name(table.name)
            classes = cls._table_classes(
                connection=connection,
                sources=table.sources,
                relation=table.name,
                relation_path=".".join((*table.group_path, table.name)),
                class_name=table_name,
                final=True,
                hive_partitioned=table.hive_partitioned,
                inference=inference,
                asset=_generated_asset(context),
            )
            note = nullability_note(
                tier_for_suffix(source_suffix(table.sources[0])),
                table.sources[0], table.sources, table.name, (table_name,),
            )
            notes.setdefault(note.line, note)
            relative = Path(*table.group_path) / f"{identifier(table.name, fallback='table')}.py"
            files.append(GeneratedFile(
                relative,
                bind_records(classes, PurePosixPath(relative.as_posix())),
                (table_name,),
            ))
        for group_path in sorted(group_paths, key=lambda value: (-len(value), value)):
            group_members = [
                GeneratedMember(
                    identifier(table.name, fallback="table"),
                    table_class_name(table.name),
                )
                for table in tables if table.group_path == group_path
            ]
            children = sorted({
                path[len(group_path)] for path in group_paths
                if len(path) == len(group_path) + 1
                and path[:len(group_path)] == group_path
            })
            group_members.extend(
                GeneratedMember(
                    identifier(child, fallback="group"),
                    group_class_name((*group_path, child), context.request_id),
                )
                for child in children
            )
            logical_name = group_path[-1] if group_path else context.request_id
            declaration = GeneratedClass(
                group_class_name(group_path, context.request_id),
                members=tuple(group_members),
                base="TableGroup",
                declaration_name=logical_name,
            )
            files.append(GeneratedFile(
                Path(*group_path) / "__init__.py", (declaration,), (declaration.name,),
            ))
        return GeneratedPackage(tuple(files), tuple(notes.values()))

    @classmethod
    async def generate(
        cls, context: ProviderContext[DataContractInferenceConfig],
    ) -> GeneratedPackage:
        return await asyncio.to_thread(cls._generate, context)

    @classmethod
    def _generate(
        cls, context: ProviderContext[DataContractInferenceConfig],
    ) -> GeneratedPackage:
        source = _source(context)
        remote = remote_source(source)
        path = None if remote else resolve_provider_path(context, source)
        source = source if remote else str(path)
        if context.config.layout != "files" and context.config.mode != "table_group":
            raise GenerationError(f"layout={context.config.layout!r} requires mode='table_group'")
        if source_suffix(source) in DATABASE_SUFFIXES:
            raise GenerationError(
                f"data-contract inference input {source} is a DuckDB database: its "
                "relations can be inferred but never bound, because no source "
                "planner selects a database reader. Export the relation to Parquet, or "
                "declare the contract outside a generated package."
            )
        inference = Inference(overrides=declared_overrides(context.config.override))
        if context.config.mode == "table_group":
            if context.config.relation is not None:
                raise GenerationError("table-group inference does not accept relation=")
            tables = logical_tables(
                source,
                context.request_id,
                context.config.layout,
                anonymous=context.config.anonymous,
            )
            connection = connect()
            try:
                for table in tables:
                    for item in table.sources:
                        load_remote_access(connection, item)
                package = cls._table_group_package(context, tables, connection, inference)
                require_overrides(inference)
                return replace(package, source_digest=schema_digest(inference))
            finally:
                connection.close()
        if path is not None and not path.exists():
            raise GenerationError(f"data-contract inference input does not exist: {path}")
        if path is not None and path.is_dir():
            raise GenerationError("directory inference requires mode='table_group'")
        connection = connect()
        try:
            load_remote_access(connection, source)
            exposed = relations(connection, source)
            if not exposed:
                raise GenerationError(f"data input {path} exposes no relations")
            if context.config.relation is None and len(exposed) != 1:
                raise GenerationError(
                    "table-contract inference requires relation= when the input "
                    "exposes multiple relations"
                )
            relation = context.config.relation or exposed[0]
            if relation not in exposed:
                raise GenerationError(f"data input {path} has no relation {relation!r}")
            class_name = table_class_name(context.request_id)
            classes = cls._table_classes(
                connection=connection, sources=(source,), relation=relation,
                relation_path=relation, class_name=class_name, final=True,
                inference=inference, asset=_generated_asset(context),
            )
            require_overrides(inference)
            package = GeneratedPackage(
                (GeneratedFile(
                    Path("__init__.py"),
                    bind_records(classes, PurePosixPath("__init__.py")),
                    (class_name,),
                ),),
                (nullability_note(
                    tier_for_suffix(source_suffix(source)), source, (source,), relation,
                ),),
            )
            return replace(package, source_digest=schema_digest(inference))
        finally:
            connection.close()


__all__ = ["InferDataContractProvider"]
