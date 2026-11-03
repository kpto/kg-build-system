"""The core module's configuration."""
from __future__ import annotations

from dataclasses import dataclass

from ..registration import ModuleRegistrationConfiguration


@dataclass(frozen=True)
class CoreConfiguration(ModuleRegistrationConfiguration):
    """The mandatory core module has no author-configurable behaviour.

    Example:
        ```python
        from kg_build_system.distribution.model.public.modules.core import (
            CoreConfiguration,
        )

        CoreConfiguration().to_json()
        ```
    """


__all__ = ["CoreConfiguration"]
