from pathlib import Path

from kg_build_system import build, compile_blueprint, create_blueprint
from kg_build_system.compile.models import BuildBlueprint
from kg_build_system.modules import (
    CollapseExactDuplicatesModule,
    FileModule,
    FileModuleConfiguration,
)


def create_demo_blueprint() -> BuildBlueprint:
    return create_blueprint(
        namespace_path=Path(__file__).parent,
        modules=(
            CollapseExactDuplicatesModule(),
            FileModule(FileModuleConfiguration("graph.jsonl")),
        ),
    )


def run_demo() -> None:
    """Write the graph and inspectable compilation artifacts to ``demo/build``."""
    output_dir = Path(__file__).parent / "build"
    output_dir.mkdir(exist_ok=True)

    blueprint = create_demo_blueprint()
    contract = compile_blueprint(blueprint=blueprint)
    build(contract, output_directory=output_dir)


if __name__ == "__main__":
    run_demo()
