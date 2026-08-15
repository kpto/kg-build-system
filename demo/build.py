from pathlib import Path

from kg_build_system import build, compile
from kg_build_system.compile.contracts import BuildContract
from kg_build_system.modules import (
    CollapseExactDuplicatesModule,
    FileModule,
    FileModuleConfiguration,
)


def compile_demo() -> BuildContract:
    return compile(
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

    contract = compile_demo()
    build(contract, output_directory=output_dir)


if __name__ == "__main__":
    run_demo()
