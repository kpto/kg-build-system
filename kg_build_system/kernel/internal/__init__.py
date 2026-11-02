"""No internal-only composition surface.

``Registry`` is public, and its ordering and pipeline helpers are private.
Another package imports the kernel through :mod:`kg_build_system.kernel` or
:mod:`kg_build_system.kernel.public`.
"""
from __future__ import annotations

__all__: list[str] = []
