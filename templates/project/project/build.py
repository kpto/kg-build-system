"""Compose, compile and run the template fixture."""

from pathlib import Path

from kg_build_system import compile, create_blueprint, execute
from kg_build_system.distribution import (
    DeduplicationPlanner,
    FileConfiguration,
    FilePlanner,
    MetaGraphPlanner,
)

ROOT = Path(__file__).parent


def create_project_blueprint():
    """Link the project namespace into one blueprint."""
    return create_blueprint(namespace_path=ROOT)


def compile_project():
    """Compile the blueprint with the template's planner composition."""
    return compile(
        blueprint=create_project_blueprint(),
        planners=(
            DeduplicationPlanner(),
            FilePlanner(FileConfiguration("graph.jsonl")),
            MetaGraphPlanner(),
        ),
    )


def run() -> None:
    """Write the fixture's plan, records, meta graph and report."""
    output_directory = ROOT.parent / "build"
    output_directory.mkdir(exist_ok=True)
    execute(compile_project(), output_directory=output_directory)


if __name__ == "__main__":
    run()
