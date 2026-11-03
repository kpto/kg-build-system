"""The default KG distribution: blueprint, planners, executors and toolchain.

The distribution owns domain vocabulary: graph, blueprint, node, edge, binding,
projection, table, core, meta-graph, Neo4j, DuckDB and Python. The kernel owns
the toolchain vocabulary those values plug into.

Example:
    ```python
    from kg_build_system.distribution import (
        FileConfiguration, FilePlanner, GraphBlueprint, create_blueprint,
    )

    blueprint = create_blueprint()
    plan = compile(blueprint, planners=(FilePlanner(FileConfiguration("graph.jsonl")),))
    ```
"""
from __future__ import annotations

from .default import DEFAULT_TOOLCHAIN, default_toolchain
from .executors.conflict_validation import (
    ConflictingNonNullValueFinding,
    ConflictingNonNullValuesReport,
    ConflictReportExecutor,
)
from .executors.duckdb import (
    DuckDbExecutor,
    DuckDbInstructionEmitter,
    DuckDbResourceProvider,
    DuckDbSqlEmitter,
)
from .executors.file import (
    FileConfiguration,
    FileExecutor,
    FilePlanner,
)
from .executors.meta_graph import (
    MetaGraphConfiguration,
    MetaGraphExecutor,
    MetaGraphPlanner,
)
from .executors.neo4j import (
    Neo4jConfiguration,
    Neo4jExecutor,
    Neo4jPlanner,
)
from .executors.python import PythonExecutor
from .interpreter import GraphBlueprint, create_blueprint
from .model.public import BuildRuntime
from .planners import (
    ConflictValidationConfiguration,
    ConflictValidationPlanner,
    CorePlanner,
    DeduplicationPlanner,
    MergingConfiguration,
    MergingPlanner,
)

__all__ = [
    "BuildRuntime",
    "ConflictReportExecutor",
    "ConflictValidationConfiguration",
    "ConflictValidationPlanner",
    "ConflictingNonNullValueFinding",
    "ConflictingNonNullValuesReport",
    "CorePlanner",
    "DEFAULT_TOOLCHAIN",
    "DeduplicationPlanner",
    "DuckDbExecutor",
    "DuckDbInstructionEmitter",
    "DuckDbResourceProvider",
    "DuckDbSqlEmitter",
    "FileConfiguration",
    "FileExecutor",
    "FilePlanner",
    "GraphBlueprint",
    "MetaGraphConfiguration",
    "MetaGraphExecutor",
    "MetaGraphPlanner",
    "MergingConfiguration",
    "MergingPlanner",
    "Neo4jConfiguration",
    "Neo4jExecutor",
    "Neo4jPlanner",
    "PythonExecutor",
    "create_blueprint",
    "default_toolchain",
]
