"""Author-facing registration values for a supplied module."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Generic, TypeVar

from ..internal.model.module import Module


ConfigT = TypeVar("ConfigT")


@dataclass(frozen=True, slots=True)
class ModuleRegistrationConfiguration:
    """Serialisable, non-secret configuration declared for a module.

    Subclasses are frozen dataclasses. Configuration is compile-time input: it
    changes the contract and its fingerprint, and must never hold credentials.
    :meth:`to_json` is the form carried in module provenance.

    Example:
        ```python
        from dataclasses import dataclass

        from kg_build_system.distribution import ModuleRegistrationConfiguration

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
            from kg_build_system.distribution import (
                ModuleRegistrationConfiguration,
            )
            assert ModuleRegistrationConfiguration().to_json() == {}
            ```
        """
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ModuleRegistration(Generic[ConfigT]):
    """A module class paired with its validated frozen configuration.

    Construct a registration with :func:`register_module` rather than directly.
    The constructor rejects a configuration that is not an instance of
    ``module_class.CONFIGURATION_TYPE``.

    Example:
        ```python
        from kg_build_system.distribution import (
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


__all__ = ["ModuleRegistration", "ModuleRegistrationConfiguration"]
