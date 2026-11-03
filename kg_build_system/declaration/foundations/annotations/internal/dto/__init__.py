"""The annotation blueprint DTO and its document codec."""
from __future__ import annotations

from .blueprint_dto import AnnotationDTO
from .codec import annotation_from_document, annotation_to_document

__all__ = [
    "AnnotationDTO", "annotation_from_document", "annotation_to_document",
]
