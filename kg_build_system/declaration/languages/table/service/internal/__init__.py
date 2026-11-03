"""Framework-internal table service interface.

Transcription, validation, codec, source rendering, row-source planning and the
kernel language adapter are resolved through this package. The mechanisms live
in ``service._private``; each name here is a thin delegation.
"""
from __future__ import annotations

from typing import Any

_LAZY = {
    "SourceFragment": ("source", "SourceFragment"),
    "TableLanguage": ("adapters.kernel_language", "TableLanguage"),
    "as_row_source": ("rows", "as_row_source"),
    "collect_declarations": ("transcription", "collect_declarations"),
    "collect_values": ("transcription", "collect_values"),
    "data_to_fragment": ("source", "data_to_fragment"),
    "data_from_document": ("codec", "data_from_document"),
    "data_to_document": ("codec", "data_to_document"),
    "declaration_source_name": ("rows", "declaration_source_name"),
    "derive_distinct": ("rows", "derive_distinct"),
    "derive_group_by": ("rows", "derive_group_by"),
    "derive_join": ("rows", "derive_join"),
    "derive_order_by": ("rows", "derive_order_by"),
    "derive_row_source": ("rows", "derive_row_source"),
    "derive_union": ("rows", "derive_union"),
    "derive_where": ("rows", "derive_where"),
    "plan_expressions": ("rows", "plan_expressions"),
    "plan_fields": ("rows", "plan_fields"),
    "plan_inputs": ("rows", "plan_inputs"),
    "plan_scan_sources": ("rows", "plan_scan_sources"),
    "plan_shape_source_name": ("rows", "plan_shape_source_name"),
    "projection_base": ("declarations", "projection_base"),
    "projection_row_source": ("declarations", "projection_row_source"),
    "relation_plan_dto": ("declarations", "relation_plan_dto"),
    "render": ("source", "render"),
    "render_data": ("source", "render_data"),
    "retarget_expression_dto": ("rows", "retarget_expression_dto"),
    "row_source_key": ("rows", "row_source_key"),
    "row_source_plan_dto": ("rows", "row_source_plan_dto"),
    "shape_context": ("rows", "shape_context"),
    "transcribe_data": ("transcription", "transcribe_data"),
    "validate_data": ("transcription", "validate_data"),
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


__all__ = sorted(_LAZY)
