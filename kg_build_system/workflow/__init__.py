"""Author-facing workflow execution.

A graph author calls :func:`build` and reads :class:`BuildRuntime` and
:class:`WorkflowReport` here. The framework-internal workflow model, extension
protocols and contract codec are :mod:`kg_build_system.workflow.interfaces`; the
contract IR is :mod:`kg_build_system.workflow.ir`.
"""
from __future__ import annotations

from .executor import build
from .models import BuildRuntime, WorkflowReport

__all__ = ["BuildRuntime", "WorkflowReport", "build"]
