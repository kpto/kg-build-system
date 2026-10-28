"""Workflow operators: artifact transformations and validation."""

from .conflict_validation import (
    RejectConflictingNonNullValuesConfiguration,
    RejectConflictingNonNullValuesModule,
)
from .deduplication import CollapseExactDuplicatesModule
from .merging import (
    MergeCompatibleFactsModule, MergeCompatibleFactsModuleConfiguration,
)

__all__ = [
    "CollapseExactDuplicatesModule",
    "MergeCompatibleFactsModule",
    "MergeCompatibleFactsModuleConfiguration",
    "RejectConflictingNonNullValuesConfiguration",
    "RejectConflictingNonNullValuesModule",
]
