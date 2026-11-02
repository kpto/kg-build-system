"""Core workflow module and its artifact vocabulary.

The package is split by responsibility: plan, authored steps, guards, source
reading, lowering and execution. ``CoreModule``, ``CoreArtifactTypes`` and
``graph_record_components`` are the names another package composes with.
"""
from __future__ import annotations

from .artifacts import CoreArtifactTypes, GraphRecordArtifact, graph_record_components
from .compiler import CoreCompiler
from .executor import CoreExecutor
from .module import CoreConfiguration, CoreModule

__all__ = [
    "CoreArtifactTypes",
    "CoreCompiler",
    "CoreConfiguration",
    "CoreExecutor",
    "CoreModule",
    "GraphRecordArtifact",
    "graph_record_components",
]
