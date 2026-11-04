"""Annotation service-internal interface: payload, validation, codec and render."""
from __future__ import annotations

from ...model.internal.dto.blueprint_dto import AnnotationDTO
from .dto.codec import annotation_from_document, annotation_to_document
from .functions import annotation_dtos, annotation_payload, annotation_tuple
from .service.source import render_annotation_source

__all__ = [
    "AnnotationDTO", "annotation_dtos", "annotation_from_document",
    "annotation_payload", "annotation_to_document", "annotation_tuple",
    "render_annotation_source",
]
