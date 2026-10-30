"""Declarative, typed, and reproducible knowledge-graph builds.

The author-facing surface is :mod:`kg_build_system.authoring`; this module
re-exports it so ``import kg_build_system`` and ``import kg_build_system.authoring``
name the same API.
"""
from __future__ import annotations

from .authoring import *  # noqa: F403
from .authoring import __all__  # noqa: F401
