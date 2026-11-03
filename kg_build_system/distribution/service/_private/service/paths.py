"""Shared path validation for modules that write into the build output.

The rule is a model invariant used by both configurations and executors; the
implementation lives in :mod:`kg_build_system.distribution.model.public.paths`.
"""
from __future__ import annotations

from ....model.public.paths import validate_relative_path

__all__ = ["validate_relative_path"]
