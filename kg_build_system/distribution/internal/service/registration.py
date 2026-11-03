"""Implementation of module registration."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...internal.model.module import Module
    from ...public.model.registration import (
        ModuleRegistration,
        ModuleRegistrationConfiguration,
    )


def register_module(
    module_class: type[Module],
    configuration: ModuleRegistrationConfiguration | None = None,
) -> ModuleRegistration[Any]:
    """Pair a module class with a validated configuration value."""
    from ...public.model.registration import ModuleRegistration

    resolved = configuration or module_class.CONFIGURATION_TYPE()
    return ModuleRegistration(module_class, resolved)


def module_configuration_json(
    configuration: ModuleRegistrationConfiguration,
) -> Any:
    """Return a module configuration in its JSON-compatible form."""
    return configuration.to_json()


__all__ = ["module_configuration_json", "register_module"]
