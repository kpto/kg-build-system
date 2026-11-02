"""Author-facing workflow execution.

A graph author calls :func:`build` and reads :class:`BuildRuntime` and
:class:`WorkflowReport` here. The framework-internal workflow model, assembly,
contract, execution and private mechanisms are elsewhere in the package.
"""
from __future__ import annotations

from .public import BuildRuntime, WorkflowReport, build

__all__ = ["BuildRuntime", "WorkflowReport", "build"]
