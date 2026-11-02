"""No author-facing surface.

The engines package owns code generation; a graph author never writes SQL or
selects an engine directly. Use :mod:`kg_build_system.engines.internal` from
framework code.
"""
from __future__ import annotations

__all__: list[str] = []
