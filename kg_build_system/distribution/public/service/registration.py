"""Author-facing module registration helpers."""
from __future__ import annotations

from typing import Any

from ...internal.model.module import Module
from ...internal.service.registration import (
    module_configuration_json as _module_configuration_json,
    register_module as _register_module,
)
from ..model.registration import (
    ModuleRegistration,
    ModuleRegistrationConfiguration,
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
        from kg_build_system.distribution import (
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
        from kg_build_system.distribution import (
            FileModule, FileModuleConfiguration, register_module,
        )
        from kg_build_system.distribution.public import module_configuration_json

        registration = register_module(
            FileModule, FileModuleConfiguration("graph.jsonl"),
        )
        module_configuration_json(registration.configuration)
        ```
    """
    return _module_configuration_json(configuration)


__all__ = ["module_configuration_json", "register_module"]
