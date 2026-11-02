"""Implementation vocabulary for the core module.

Kept for the historical ``modules.core.core`` path; the module protocol value is
:class:`kg_build_system.modules.internal.adapters.core_module.CoreModule`.
"""
from __future__ import annotations

from .artifacts import CoreArtifactTypes, GraphRecordArtifact, graph_record_components
from .compiler import CoreCompiler
from .executor import CoreExecutor
from .module import CoreConfiguration
from ...internal.adapters.core_module import CoreModule

__all__ = [
    "CoreArtifactTypes",
    "CoreCompiler",
    "CoreConfiguration",
    "CoreExecutor",
    "CoreModule",
    "GraphRecordArtifact",
    "graph_record_components",
]
