"""Compilation of a graph blueprint into a workflow contract.

The public entry point is :func:`compile_blueprint`; the module pipeline, the
engine-neutral plans and the instruction emitters are framework-internal.
"""
from __future__ import annotations

from .service.public import compile_blueprint

__all__ = ["compile_blueprint"]
