"""Thin registration wrappers over the private implementation."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...model.internal.model.module import Module
    from ...model.public.registration import (
        ModuleRegistration,
        ModuleRegistrationConfiguration,
    )


def register_module(
    module_class: type[Module],
    configuration: ModuleRegistrationConfiguration | None = None,
) -> ModuleRegistration[Any]:
    """Pair a module class with a validated configuration value."""
    from .._private.service.registration import register_module as implementation

    return implementation(module_class, configuration)


def module_configuration_json(
    configuration: ModuleRegistrationConfiguration,
) -> Any:
    """Return a module configuration in its JSON-compatible form."""
    from .._private.service.registration import (
        module_configuration_json as implementation,
    )

    return implementation(configuration)


__all__ = ["module_configuration_json", "register_module"]
