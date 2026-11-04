"""The default KG distribution: blueprint, modules and toolchain.

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

from .implementations import (
    BindingLanguage,
    BlueprintLinker,
    DataLanguage,
    ExpressionsLanguage,
    TopologyLanguage,
)
from .interpreter import GraphBlueprint, create_blueprint
from .model.public import (
    BuildRuntime,
    EdgeRef,
    FieldRef,
    NodeRef,
    OperationRef,
    PropertyRef,
    Ref,
    RelationRef,
    SourceRef,
    ref_from_document,
    ref_to_document,
)
from .modules.conflict_validation import (
    ConflictingNonNullValueFinding,
    ConflictingNonNullValuesReport,
    ConflictReportExecutor,
    ConflictValidationConfiguration,
    ConflictValidationPlanner,
)
from .modules.core import (
    BindingPlanner,
    InputPlanner,
    ProjectionPlanner,
    RecordsPlanner,
    RowSourcePlanner,
    core_planners,
)
from .modules.deduplication import DeduplicationPlanner
from .modules.duckdb import (
    DuckDbExecutor,
    DuckDbInstructionEmitter,
    DuckDbResourceProvider,
    DuckDbService,
    DuckDbSqlEmitter,
)
from .modules.file import (
    FileConfiguration,
    FileExecutor,
    FilePlanner,
)
from .modules.merging import (
    MergingConfiguration,
    MergingPlanner,
)
from .modules.meta_graph import (
    MetaGraphConfiguration,
    MetaGraphExecutor,
    MetaGraphPlanner,
)
from .modules.neo4j import (
    Neo4jConfiguration,
    Neo4jExecutor,
    Neo4jPlanner,
)
from .modules.python import PythonExecutor
from .modules.runtime import RuntimeResources

__all__ = [
    "BindingLanguage",
    "BindingPlanner",
    "BlueprintLinker",
    "BuildRuntime",
    "ConflictReportExecutor",
    "ConflictValidationConfiguration",
    "ConflictValidationPlanner",
    "ConflictingNonNullValueFinding",
    "ConflictingNonNullValuesReport",
    "DataLanguage",
    "DeduplicationPlanner",
    "DuckDbExecutor",
    "DuckDbInstructionEmitter",
    "DuckDbResourceProvider",
    "DuckDbService",
    "DuckDbSqlEmitter",
    "EdgeRef",
    "ExpressionsLanguage",
    "FieldRef",
    "FileConfiguration",
    "FileExecutor",
    "FilePlanner",
    "GraphBlueprint",
    "InputPlanner",
    "MetaGraphConfiguration",
    "MetaGraphExecutor",
    "MetaGraphPlanner",
    "MergingConfiguration",
    "MergingPlanner",
    "Neo4jConfiguration",
    "Neo4jExecutor",
    "Neo4jPlanner",
    "NodeRef",
    "OperationRef",
    "ProjectionPlanner",
    "PropertyRef",
    "PythonExecutor",
    "RecordsPlanner",
    "Ref",
    "RelationRef",
    "RowSourcePlanner",
    "RuntimeResources",
    "SourceRef",
    "TopologyLanguage",
    "core_planners",
    "create_blueprint",
    "ref_from_document",
    "ref_to_document",
]
