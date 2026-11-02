"""Compile-time module protocols."""
from __future__ import annotations

from typing import Any, Protocol


class ModuleCompiler(Protocol):
    """Compile one module against a frozen build and its configuration."""

    async def compile(self, context: Any) -> Any:
        """Return this module's workflow contribution."""
        ...


class CompilableModule(Protocol):
    """A module class the compilation pipeline can load and compile."""

    ID: str
    VERSION: str
    CONFIGURATION_TYPE: type[Any]

    @classmethod
    async def create_compiler(cls, context: Any) -> ModuleCompiler:
        """Create the compiler for this module version."""
        ...


__all__ = ["CompilableModule", "ModuleCompiler"]
