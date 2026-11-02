"""Module protocol: compile a frozen build and execute its steps."""
from __future__ import annotations

from typing import Any, ClassVar, Protocol


class ModuleCompiler(Protocol):
    async def compile(self, context: Any) -> Any: ...


class ModuleExecutor(Protocol):
    def handle(self, context: Any) -> Any: ...

    def handle_disrupted(self, context: Any) -> Any: ...


class Module(Protocol):
    ID: ClassVar[str]
    VERSION: ClassVar[str]
    CONFIGURATION_TYPE: ClassVar[type[Any]]

    @classmethod
    async def create_compiler(cls, context: Any) -> ModuleCompiler: ...

    @classmethod
    def create_executor(cls, context: Any) -> ModuleExecutor: ...


__all__ = ["Module", "ModuleCompiler", "ModuleExecutor"]
