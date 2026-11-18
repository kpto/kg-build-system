"""The project's composition: its blueprint and workflow.

The values are declarations. `kbs blueprint`, `kbs workflow` and `kbs run` read
them and perform the requested step; importing this module builds nothing.

The empty manifest composes the default languages and the graph workflow. Add a
project planner, executor, emitter or operation only when the project needs one.
"""

from pathlib import Path

from kg_build_system import (
    Blueprint,
    Workflow,
    default_languages,
    default_toolchain,
)
from kg_build_system.distribution import (
    DeduplicationPlanner,
    FileConfiguration,
    FilePlanner,
    MetaGraphPlanner,
)

ROOT = Path(__file__).parent

languages = default_languages()

blueprint = Blueprint(namespace_path=ROOT, languages=languages)

toolchain = default_toolchain(
    languages=languages,
    planners=(
        DeduplicationPlanner(),
        FilePlanner(FileConfiguration("graph.jsonl")),
        MetaGraphPlanner(),
    ),
)

workflow = Workflow(
    blueprint=blueprint,
    toolchain=toolchain,
    output_directory=ROOT.parent / "build",
)
