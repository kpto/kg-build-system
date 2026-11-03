"""A capability is a named contract a module requires or provides.

Capabilities are compared by name. A module states the capabilities it needs
before it can compile or execute, and the capabilities it contributes to the
distribution.

Example:
    ```python
    from kg_build_system.kernel import Capability

    capability = Capability("data")
    assert capability.name == "data"
    ```
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Capability:
    """One named capability a module requires or provides.

    Example:
        ```python
        from kg_build_system.kernel import Capability

        Capability("topology")
        ```
    """

    name: str


__all__ = ["Capability"]
