"""Framework-internal data service interface.

Transcription, validation, codec, source rendering, row-source planning and the
kernel language adapter are resolved through this package. The mechanisms live
in ``service._private``; each name here is a thin delegation.
"""
from __future__ import annotations

from .adapters.kernel_language import DataLanguage
from .codec import data_from_document, data_to_document
from .declarations import (
    projection_row_source, relation_plan_dto,
)
from .rows import (
    as_row_source, declaration_source_name, derive_distinct, derive_group_by,
    derive_join, derive_order_by, derive_row_source, derive_union, derive_where,
    plan_expressions, plan_fields, plan_inputs, plan_scan_sources,
    plan_shape_source_name, retarget_expression_dto, row_source_key,
    row_source_plan_dto, shape_context,
)
from .source import SourceFragment, data_to_fragment, render, render_data
from .transcription import (
    collect_declarations, collect_values, transcribe_data, validate_data,
)

__all__ = [
    "DataLanguage", "SourceFragment", "as_row_source", "collect_declarations",
    "collect_values", "data_from_document", "data_to_document",
    "data_to_fragment", "declaration_source_name", "derive_distinct",
    "derive_group_by", "derive_join", "derive_order_by", "derive_row_source",
    "derive_union", "derive_where", "plan_expressions", "plan_fields",
    "plan_inputs", "plan_scan_sources", "plan_shape_source_name",
    "projection_row_source", "relation_plan_dto", "render",
    "render_data", "retarget_expression_dto", "row_source_key",
    "row_source_plan_dto", "shape_context", "transcribe_data", "validate_data",
]
