"""Thin re-export of the Python executor implementation."""
from __future__ import annotations

from .._private.python import PythonExecutor

__all__ = ["PythonExecutor"]
