"""Supplied module configurations and data returned by their targets."""
from __future__ import annotations

from .conflict_validation import (
    ConflictingNonNullValueFinding,
    ConflictingNonNullValuesReport,
    RejectConflictingNonNullValuesConfiguration,
)
from .core import CoreConfiguration
from .deduplication import DeduplicationConfiguration
from .file import FileModuleConfiguration
from .merging import MergeCompatibleFactsModuleConfiguration
from .meta_graph import MetaGraphModuleConfiguration
from .neo4j import Neo4jModuleConfiguration

__all__ = [
    "ConflictingNonNullValueFinding",
    "ConflictingNonNullValuesReport",
    "CoreConfiguration",
    "DeduplicationConfiguration",
    "FileModuleConfiguration",
    "MergeCompatibleFactsModuleConfiguration",
    "MetaGraphModuleConfiguration",
    "Neo4jModuleConfiguration",
    "RejectConflictingNonNullValuesConfiguration",
]
