"""The distribution module model."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from .....kernel import ExecutorFactoryContext, ModuleExecutor


class Module(ABC):
    """The declaration one supplied module implements."""

    ID: ClassVar[str]
    VERSION: ClassVar[str]
    CONFIGURATION_TYPE: ClassVar[type[Any]]

    @classmethod
    @abstractmethod
    def compiler(cls, configuration: Any) -> Any:
        """Create the compilation-side compiler for one configuration."""
        ...

    @classmethod
    @abstractmethod
    def executor(cls, context: ExecutorFactoryContext) -> ModuleExecutor:
        """Create the build-side executor for one factory context."""
        ...


__all__ = ["Module"]
