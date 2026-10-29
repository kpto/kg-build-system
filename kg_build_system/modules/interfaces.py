"""Framework-internal interface of the module domain.

Other subpackages implement the module protocols and read module-produced IR
here. A graph author registers modules through the names re-exported by
:mod:`kg_build_system.modules`; module-produced IR is
:mod:`kg_build_system.modules.ir`.
"""
from __future__ import annotations

from .protocols import (
    Module,
    ModuleRegistration,
    ModuleRegistrationConfiguration,
    module_configuration_json,
    register_module,
)

__all__ = [
    "Module",
    "ModuleRegistration",
    "ModuleRegistrationConfiguration",
    "module_configuration_json",
    "register_module",
]
