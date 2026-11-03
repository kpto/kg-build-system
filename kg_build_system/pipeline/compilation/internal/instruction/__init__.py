"""Instruction kinds and their emitters.

``DuckDbSqlEmitter`` is the default SQL library. It is not a capability module:
a module compiler asks for an emitter, it does not register one.
"""
from __future__ import annotations

from .duckdb import DuckDbSqlEmitter
from .model import PythonReference, SqlEmissionContext
from .protocol import InstructionEmitter
from .python import PythonInstructionEmitter

__all__ = [
    "DuckDbSqlEmitter",
    "InstructionEmitter",
    "PythonInstructionEmitter",
    "PythonReference",
    "SqlEmissionContext",
]
