"""Plan a source-relation step for every asset-backed table the graph reads."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.distribution.languages.asset.model.public import AssetLayout
from kg_build_system.distribution.model.public.artifacts import CoreArtifactTypes
from kg_build_system.distribution.service.internal import AssetTable, asset_tables
from kg_build_system.kernel import Instruction, InstructionKind, Output, Step
from kg_build_system.kernel.service.internal.types import type_to_document, type_to_dto
from .reading import declared_read_paths

SOURCE_RELATION = InstructionKind("source_relation", "duckdb")
SUPPORTED_FORMATS = frozenset({"parquet", "json", "csv"})


def _is_relative(value: str) -> bool:
    return not urlsplit(value).scheme and not value.startswith(("/", "\\", "~"))


def _join(locator: str | None, value: str) -> str:
    if locator is None or not _is_relative(value):
        return value
    return f"{locator.rstrip('/\\')}/{value.lstrip('/\\')}"


def _format(layout: AssetLayout) -> str | None:
    value = layout.format or layout.kind
    return value if value in SUPPORTED_FORMATS else None


def _location(layout: AssetLayout, table: AssetTable) -> str | None:
    member = layout.members.get(table.relation_name)
    if member is not None:
        return _join(layout.locator, member)
    if layout.selector is not None:
        selected = layout.selector.format(
            table=table.relation_name,
            table_path=table.relation_name.replace(".", "/"),
        )
        return _join(layout.locator, selected)
    return layout.locator


def _payload(
    blueprint: GraphBlueprint,
    table: AssetTable,
    *,
    location: str,
    source_format: str,
) -> dict[str, Any]:
    layout = table.asset.layout
    read_paths = declared_read_paths(blueprint).get(table.relation_name, ())
    return {
        "relation": table.relation,
        "location": location,
        "format": source_format,
        "credential_reference": (
            None if layout is None else layout.properties.get("credentials")
        ),
        "declaration": table.relation_name,
        "declared_columns": [
            {
                "name": column.name,
                "logical_type": type_to_document(type_to_dto(column.logical_type)),
            }
            for column in table.columns
        ],
        "declared_paths": [
            {
                "schema_path": path.schema_path,
                "logical_path": path.logical_path,
            }
            for path in read_paths
        ],
    }


def source_steps(
    blueprint: GraphBlueprint,
    *,
    formats: frozenset[str] = SUPPORTED_FORMATS,
) -> tuple[Step, ...]:
    """One ``source.<relation>`` step per compatible asset-backed table."""
    steps: list[Step] = []
    for table in asset_tables(blueprint):
        layout = table.asset.layout
        if layout is None:
            continue
        source_format = _format(layout)
        if source_format is None or source_format not in formats:
            continue
        location = _location(layout, table)
        if location is None:
            continue
        steps.append(Step(
            component="duckdb",
            name=f"source.{table.relation_name}",
            inputs=(),
            outputs=(Output(CoreArtifactTypes.table(table.relation_name)),),
            instruction=Instruction(
                SOURCE_RELATION,
                _payload(
                    blueprint,
                    table,
                    location=location,
                    source_format=source_format,
                ),
            ),
        ))
    return tuple(steps)


__all__ = ["SUPPORTED_FORMATS", "source_steps"]
