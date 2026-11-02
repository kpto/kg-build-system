"""Module extension protocols and registration.

A supplied module implements :class:`Module` and the compiler/executor
protocols; a graph author only registers it or reads its configuration. Module
IR is :mod:`kg_build_system.modules.ir`; the author-facing names are re-exported
by :mod:`kg_build_system.modules`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any, ClassVar, Generic, TypeVar

from ..compile.interfaces import ModuleCompiler
from ..kernel import CompilationContext, ExecutorFactoryContext, ModuleExecutor
from ._registration import (
    module_configuration_json as _module_configuration_json,
    register_module as _register_module,
)


ConfigT = TypeVar("ConfigT")


@dataclass(frozen=True, slots=True)
class ModuleRegistrationConfiguration:
    """Serializable, non-secret configuration declared for a module.

    Subclasses are frozen dataclasses. Configuration is compile-time input: it
    changes the contract and its fingerprint, and must never hold credentials.
    :meth:`to_json` is the form carried in module provenance; a subclass may
    override it when a field needs a different serialised shape.

    Example:
        ```python
        from dataclasses import dataclass

        from kg_build_system.modules import ModuleRegistrationConfiguration

        @dataclass(frozen=True)
        class ExportConfiguration(ModuleRegistrationConfiguration):
            relative_path: str = "graph.jsonl"

        ExportConfiguration().to_json()
        ```
    """

    def to_json(self) -> Any:
        """Return the JSON-compatible form carried in module provenance.

        Example:
            ```python
            from kg_build_system.modules import ModuleRegistrationConfiguration
            assert ModuleRegistrationConfiguration().to_json() == {}
            ```
        """
        return asdict(self)


class Module(ABC):
    """The protocol a supplied build-stage module class implements.

    A module class declares a stable ``ID``, an implementation ``VERSION`` and
    the ``CONFIGURATION_TYPE`` that validates its registration. It builds a
    compile-time contribution with ``create_compiler`` and a runtime executor
    with ``create_executor``. Authors compose supplied modules through
    :func:`register_module`; they do not instantiate a module.

    Example:
        ```python
        from kg_build_system.modules import (
            CollapseExactDuplicatesModule, register_module,
        )

        modules = (register_module(CollapseExactDuplicatesModule),)
        ```
    """

    ID: ClassVar[str]
    VERSION: ClassVar[str]
    CONFIGURATION_TYPE: ClassVar[type[Any]]

    @classmethod
    @abstractmethod
    async def create_compiler(
        cls, context: CompilationContext[Any],
    ) -> ModuleCompiler: ...

    @classmethod
    @abstractmethod
    def create_executor(
        cls, context: ExecutorFactoryContext,
    ) -> ModuleExecutor: ...


@dataclass(frozen=True, slots=True)
class ModuleRegistration(Generic[ConfigT]):
    """A module class paired with its validated frozen configuration.

    Construct a registration with :func:`register_module` rather than directly.
    The constructor rejects a configuration that is not an instance of
    ``module_class.CONFIGURATION_TYPE``.

    Example:
        ```python
        from kg_build_system.modules import (
            FileModule, FileModuleConfiguration, register_module,
        )

        registration = register_module(
            FileModule, FileModuleConfiguration("graph.jsonl"),
        )
        registration.module_class is FileModule
        ```
    """

    module_class: type[Module]
    configuration: ConfigT

    def __post_init__(self) -> None:
        if not isinstance(self.configuration, self.module_class.CONFIGURATION_TYPE):
            raise TypeError(
                f"{self.module_class.__name__} requires "
                f"{self.module_class.CONFIGURATION_TYPE.__name__} configuration"
            )


def register_module(
    module_class: type[Module],
    configuration: ModuleRegistrationConfiguration | None = None,
) -> ModuleRegistration[Any]:
    """Pair a module class with its configuration, or construct its default.

    With no configuration, the module's ``CONFIGURATION_TYPE`` is called with
    no arguments; a type with required fields therefore needs an explicit
    instance. Registration is inert: it holds data and does not import a
    callable or run a module.

    Example:
        ```python
        from kg_build_system.modules import (
            FileModule, FileModuleConfiguration, register_module,
        )

        modules = (
            register_module(
                FileModule, FileModuleConfiguration("graph.jsonl"),
            ),
        )
        ```
    """
    return _register_module(module_class, configuration)


def module_configuration_json(
    configuration: ModuleRegistrationConfiguration,
) -> Any:
    """Return the JSON-compatible form of a registration configuration.

    This is the value recorded in module provenance. The configuration's own
    :meth:`ModuleRegistrationConfiguration.to_json` decides the exact shape.

    Example:
        ```python
        from kg_build_system.modules import (
            FileModule, FileModuleConfiguration, register_module,
        )
        from kg_build_system.modules.interfaces import module_configuration_json

        registration = register_module(
            FileModule, FileModuleConfiguration("graph.jsonl"),
        )
        module_configuration_json(registration.configuration)
        ```
    """
    return _module_configuration_json(configuration)


__all__ = [
    "Module",
    "ModuleRegistration",
    "ModuleRegistrationConfiguration",
    "module_configuration_json",
    "register_module",
]
