"""Compilation-only annotation transfer objects.

This module is intentionally absent from :mod:`kg_build_system.annotations`
exports.  Authoring models must not retain these values.
"""
from __future__ import annotations

from dataclasses import dataclass

from .._frozen_json import FrozenJson


@dataclass(frozen=True, slots=True)
class AnnotationDTO:
    namespace: str
    annotation_id: str
    arguments: FrozenJson


__all__ = ["AnnotationDTO"]
