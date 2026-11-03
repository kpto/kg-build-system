"""The kernel ``Module`` protocol implemented for distribution modules.

A supplied module declares ``compiler`` and ``executor`` factories. This adapter
maps those to the kernel protocol's ``create_compiler`` and ``create_executor``.
The new compilation pipeline calls the ``compiler`` factory directly; the
``create_compiler`` method remains for the kernel's compatibility path.
"""
from __future__ import annotations

from typing import Any

from .....kernel import (
    CompilationContext,
    ExecutorFactoryContext,
    ModuleCompiler,
    ModuleExecutor,
)
from ....model.internal.model.module import Module


class KernelModule(Module):
    """Base class implementing the kernel module protocol."""

    @classmethod
    async def create_compiler(
        cls, context: CompilationContext[Any],
    ) -> ModuleCompiler:
        """Create the compiler for the compatibility compilation path."""
        return cls.compiler(context.configuration)

    @classmethod
    def create_executor(
        cls, context: ExecutorFactoryContext,
    ) -> ModuleExecutor:
        """Create the executor for this module version."""
        return cls.executor(context)


__all__ = ["KernelModule"]
