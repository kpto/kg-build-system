"""Implementation of module registration.

The framework-internal interface in :mod:`kg_build_system.modules.interfaces`
re-exports these functions as thin wrappers. Nothing here is author-facing.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .interfaces import (
        Module,
        ModuleRegistration,
        ModuleRegistrationConfiguration,
    )


def register_module(
    module_class: type[Module],
    configuration: ModuleRegistrationConfiguration | None = None,
) -> ModuleRegistration[Any]:
    from .interfaces import ModuleRegistration

    resolved = configuration or module_class.CONFIGURATION_TYPE()
    return ModuleRegistration(module_class, resolved)


def module_configuration_json(
    configuration: ModuleRegistrationConfiguration,
) -> Any:
    return configuration.to_json()


__all__ = ["module_configuration_json", "register_module"]
