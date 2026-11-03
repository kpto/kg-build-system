# pyright: reportUnsupportedDunderAll=false
"""Framework-internal interface of the table language.

Another subpackage imports the language adapter, its blueprint DTO and codec
here. The author-facing names live in the package's ``public`` zone.

The adapter, services and row algebra are resolved lazily: class creation imports
the model specs while the internal package is still initialising, and those
specs must not pull the public field descriptors back through this facade.
"""
from __future__ import annotations

from typing import Any

from .dto.blueprint_dto import (
    ColumnDTO, DataPartDTO, ProjectionDTO, RelationDTO, RowDistinctDTO,
    RowFilterDTO, RowGroupByDTO, RowJoinDTO, RowOrderByDTO, RowScanDTO,
    RowSourcePlanDTO, RowUnionDTO, SourceDTO, StructDTO,
)
from .dto.codec import data_from_document, data_to_document
from .model.declarations import DeclarationSpec
from .model.fields import FieldSpec

_LAZY = {
    "SourceFragment": ("service.source", "SourceFragment"),
    "TableLanguage": ("adapters.kernel_language", "TableLanguage"),
    "as_row_source": ("model.rows", "as_row_source"),
    "collect_declarations": ("service.transcription", "collect_declarations"),
    "collect_values": ("service.transcription", "collect_values"),
    "declaration_source_name": ("model.rows", "declaration_source_name"),
    "derive_distinct": ("model.rows", "derive_distinct"),
    "derive_group_by": ("model.rows", "derive_group_by"),
    "derive_join": ("model.rows", "derive_join"),
    "derive_order_by": ("model.rows", "derive_order_by"),
    "derive_row_source": ("model.rows", "derive_row_source"),
    "derive_union": ("model.rows", "derive_union"),
    "derive_where": ("model.rows", "derive_where"),
    "plan_expressions": ("model.rows", "plan_expressions"),
    "plan_fields": ("model.rows", "plan_fields"),
    "plan_inputs": ("model.rows", "plan_inputs"),
    "plan_scan_sources": ("model.rows", "plan_scan_sources"),
    "plan_shape_source_name": ("model.rows", "plan_shape_source_name"),
    "render_data": ("service.source", "render_data"),
    "retarget_expression_dto": ("model.rows", "retarget_expression_dto"),
    "row_source_key": ("model.rows", "row_source_key"),
    "row_source_plan_dto": ("model.rows", "row_source_plan_dto"),
    "transcribe_data": ("service.transcription", "transcribe_data"),
    "validate_data": ("service.transcription", "validate_data"),
}


def __getattr__(name: str) -> Any:
    try:
        module_name, attribute = _LAZY[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    from importlib import import_module

    module = import_module(f".{module_name}", __name__)
    value = getattr(module, attribute)
    globals()[name] = value
    return value


__all__ = [
    "ColumnDTO", "DataPartDTO", "DeclarationSpec", "FieldSpec", "ProjectionDTO",
    "RelationDTO", "RowDistinctDTO", "RowFilterDTO", "RowGroupByDTO",
    "RowJoinDTO", "RowOrderByDTO", "RowScanDTO", "RowSourcePlanDTO",
    "RowUnionDTO", "SourceDTO", "SourceFragment", "StructDTO", "TableLanguage",
    "as_row_source", "collect_declarations", "collect_values",
    "data_from_document", "data_to_document", "declaration_source_name",
    "derive_distinct", "derive_group_by", "derive_join", "derive_order_by",
    "derive_row_source", "derive_union", "derive_where", "plan_expressions",
    "plan_fields", "plan_inputs", "plan_scan_sources",
    "plan_shape_source_name", "render_data", "retarget_expression_dto",
    "row_source_key", "row_source_plan_dto", "transcribe_data", "validate_data",
]
