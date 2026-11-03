"""Supplied distribution module classes."""
from __future__ import annotations

from .conflict_validation import RejectConflictingNonNullValuesModule
from .core import CoreModule
from .deduplication import CollapseExactDuplicatesModule
from .file import FileModule
from .merging import MergeCompatibleFactsModule
from .meta_graph import MetaGraphModule
from .neo4j import Neo4jModule

__all__ = [
    "CollapseExactDuplicatesModule",
    "CoreModule",
    "FileModule",
    "MergeCompatibleFactsModule",
    "MetaGraphModule",
    "Neo4jModule",
    "RejectConflictingNonNullValuesModule",
]
