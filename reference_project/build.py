"""Composition entry points for the monitored-sites reference build."""

from pathlib import Path

from kg_build_system import compile, create_blueprint, execute
from kg_build_system.distribution import (
    DeduplicationPlanner,
    FileConfiguration,
    FilePlanner,
    MetaGraphPlanner,
    Neo4jPlanner,
)
from kg_build_system.distribution.interpreter import GraphBlueprint
from kg_build_system.kernel import WorkflowPlan


PROJECT_ROOT = Path(__file__).parent


def _planners():
    return (
        DeduplicationPlanner(),
        FilePlanner(FileConfiguration("graph.jsonl")),
        MetaGraphPlanner(),
        Neo4jPlanner(),
    )


def create_reference_blueprint() -> GraphBlueprint:
    return create_blueprint(namespace_path=PROJECT_ROOT)


def compile_reference_build() -> WorkflowPlan:
    return compile(blueprint=create_reference_blueprint(), planners=_planners())


def run_reference_build() -> None:
    """Write the graph and workflow artifacts to ``reference_project/build``."""
    output_dir = PROJECT_ROOT / "build"
    output_dir.mkdir(exist_ok=True)

    plan = compile_reference_build()
    execute(plan, output_directory=output_dir)


if __name__ == "__main__":
    run_reference_build()
