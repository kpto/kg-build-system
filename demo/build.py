"""Composition root for the structured authoring reference.

Run ``python demo/build.py`` to compile the declarations and write inspectable
artifacts under ``demo/output``.
"""

import sys
from pathlib import Path

from kg_build_system.compile.models import BuildBlueprint

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).parents[1]))

from kg_build_system import build, compile_blueprint, create_blueprint
from kg_build_system.modules import (
    FileModule,
    FileModuleConfiguration,
)


def create_demo_blueprint() -> BuildBlueprint:
    return create_blueprint(
        namespace_path=Path(__file__).parent,
        modules=(FileModule(FileModuleConfiguration("graph.jsonl")),),
    )


def run_demo() -> None:
    """Write the graph and inspectable compilation artifacts to ``demo/output``."""
    OUTPUT_DIRECTORY = Path(__file__).parent / "build"
    OUTPUT_DIRECTORY.mkdir(exist_ok=True)

    blueprint = create_demo_blueprint()
    contract = compile_blueprint(blueprint=blueprint)
    build(contract, output_directory=OUTPUT_DIRECTORY)


if __name__ == "__main__":
    run_demo()
