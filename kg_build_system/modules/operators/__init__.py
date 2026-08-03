"""Workflow operators: artifact transformations and validation."""

from .aggregation import BindingAggregationModule
from .conflict_validation import RejectConflictingNonNullValuesConfiguration, RejectConflictingNonNullValuesModule
from .deduplication import CollapseExactDuplicatesModule
from .merging import MergeCompatibleFactsModule

__all__ = ["BindingAggregationModule", "CollapseExactDuplicatesModule", "MergeCompatibleFactsModule", "RejectConflictingNonNullValuesConfiguration", "RejectConflictingNonNullValuesModule"]
