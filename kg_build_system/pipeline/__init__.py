"""Pipeline stages that share the workflow contract.

Compilation reads the blueprint and produces a workflow contract; build consumes
that contract. The two stages share this package so neither has to import the
other.
"""
from __future__ import annotations

__all__: list[str] = []
