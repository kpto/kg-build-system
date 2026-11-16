"""The reference project's composition: its blueprint and workflow.

The values are declarations. ``kbs blueprint``, ``kbs workflow`` and ``kbs run``
read them and perform the requested step; importing this module builds nothing.
"""

from pathlib import Path

from kg_build_system import Blueprint, Workflow
from kg_build_system.distribution import (
    DeduplicationPlanner,
    FileConfiguration,
    FilePlanner,
    MetaGraphPlanner,
    Neo4jPlanner,
)

ROOT = Path(__file__).parent

blueprint = Blueprint(namespace_path=ROOT)

workflow = Workflow(
    blueprint=blueprint,
    planners=(
        DeduplicationPlanner(),
        FilePlanner(FileConfiguration("graph.jsonl")),
        MetaGraphPlanner(),
        Neo4jPlanner(),
    ),
    output_directory=ROOT / "build",
)
