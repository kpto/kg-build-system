"""Instruction kinds, their protocol and thin emitter wrappers.

``DuckDbSqlEmitter`` is the default SQL library. It is not a capability module:
a module compiler asks for an emitter, it does not register one.
"""
from __future__ import annotations

from .duckdb import DuckDbSqlEmitter
from .model import (
    PYTHON_INSTRUCTION_KIND,
    SQL_INSTRUCTION_KIND,
    PythonReference,
    SqlEmissionContext,
)
from .protocol import InstructionEmitter
from .python import PythonInstructionEmitter

__all__ = [
    "DuckDbSqlEmitter",
    "InstructionEmitter",
    "PYTHON_INSTRUCTION_KIND",
    "PythonInstructionEmitter",
    "PythonReference",
    "SQL_INSTRUCTION_KIND",
    "SqlEmissionContext",
]
