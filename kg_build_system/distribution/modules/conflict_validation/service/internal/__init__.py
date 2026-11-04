"""Internal service interface for the conflict-validation module."""
from __future__ import annotations

from .api import ConflictReportExecutor, ConflictValidationPlanner

__all__ = ["ConflictReportExecutor", "ConflictValidationPlanner"]
