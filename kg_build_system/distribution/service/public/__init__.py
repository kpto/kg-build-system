"""The distribution's author-facing service: module classes and registration."""
from __future__ import annotations

from .modules import (
    CollapseExactDuplicatesModule,
    CoreModule,
    FileModule,
    MergeCompatibleFactsModule,
    MetaGraphModule,
    Neo4jModule,
    RejectConflictingNonNullValuesModule,
)
from .registration import module_configuration_json, register_module

__all__ = [
    "CollapseExactDuplicatesModule",
    "CoreModule",
    "FileModule",
    "MergeCompatibleFactsModule",
    "MetaGraphModule",
    "Neo4jModule",
    "RejectConflictingNonNullValuesModule",
    "module_configuration_json",
    "register_module",
]
