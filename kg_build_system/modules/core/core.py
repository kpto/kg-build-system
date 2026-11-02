"""Compatibility surface for the core module.

The implementation is split by responsibility; this module keeps the historical
``modules.core.core`` path working for targets and contracts.
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
