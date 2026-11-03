"""Python instruction emitter wrapper.

The emission mechanism lives in ``_private.instructions``; this wrapper keeps the
internal instruction path stable.
"""
from __future__ import annotations

from ..._private.instructions.python import (
    PythonInstructionEmitter as _PythonInstructionEmitter,
)


class PythonInstructionEmitter(_PythonInstructionEmitter):
    """Emit a Python instruction from a stable callable reference."""


__all__ = ["PythonInstructionEmitter"]
