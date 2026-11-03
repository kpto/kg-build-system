"""Framework-internal services of the compilation package.

The interfaces here are thin wrappers or protocols; implementations live in
``service._private``.
"""
from __future__ import annotations

from .compiler import (
    GraphBlueprint,
    assemble_contract,
    compile_blueprint,
    decompose,
    wrap_contribution,
)
from .instruction import (
    DuckDbSqlEmitter,
    InstructionEmitter,
    PYTHON_INSTRUCTION_KIND,
    PythonInstructionEmitter,
    PythonReference,
    SQL_INSTRUCTION_KIND,
    SqlEmissionContext,
)
from .planning import expansion_scope, plan_product

__all__ = [
    "DuckDbSqlEmitter",
    "GraphBlueprint",
    "InstructionEmitter",
    "PYTHON_INSTRUCTION_KIND",
    "PythonInstructionEmitter",
    "PythonReference",
    "SQL_INSTRUCTION_KIND",
    "SqlEmissionContext",
    "assemble_contract",
    "compile_blueprint",
    "decompose",
    "expansion_scope",
    "plan_product",
    "wrap_contribution",
]
