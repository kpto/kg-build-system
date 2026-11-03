"""The kernel's public service: language, module and capability protocols.

The registry is the one author-facing service in the kernel. It delegates its
ordering and composition to ``service.internal``; the mechanism lives in
``service._private``.
"""
from __future__ import annotations

from .capability import Capability
from .language import (
    Language, LanguageContext, Namespace, RenderContext, SourceFragment,
)
from .module import Module, ModuleCompiler, ModuleExecutor
from .registry import Registry

__all__ = [
    "Capability", "Language", "LanguageContext", "Module", "ModuleCompiler",
    "ModuleExecutor", "Namespace", "Registry", "RenderContext",
    "SourceFragment",
]
