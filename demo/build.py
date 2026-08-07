"""Composition root for the structured authoring reference.

Run ``python demo/build.py`` to compile the declarations and write inspectable
artifacts under ``demo/output``.
"""

from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).parents[1]))

from kg_build_system import BuildBlueprint, BuildContract, build, compile_blueprint, create_blueprint
from kg_build_system.modules import (
    CollapseExactDuplicatesModule,
    FileModule,
    FileModuleConfiguration,
    MergeCompatibleFactsModule,
    RejectConflictingNonNullValuesModule,
)


def run_demo() -> None:
    """Write the graph and inspectable compilation artifacts to ``demo/output``."""
    OUTPUT_DIRECTORY = Path(__file__).parent / "build"
    OUTPUT_DIRECTORY.mkdir(exist_ok=True)

    blueprint = create_blueprint(
        namespace_path=Path(__file__).parent,
        modules=(
            FileModule(FileModuleConfiguration("graph.jsonl")),
        ),
    )
    contract = compile_blueprint(blueprint=blueprint)
    build(contract, output_directory=OUTPUT_DIRECTORY)


if __name__ == "__main__":
    run_demo()
