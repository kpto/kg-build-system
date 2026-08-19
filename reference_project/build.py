from pathlib import Path

from kg_build_system import build, compile, create_blueprint
from kg_build_system.compile.models import BuildBlueprint
from kg_build_system.modules import (
    CollapseExactDuplicatesModule,
    FileModule,
    FileModuleConfiguration,
    Neo4jModule,
    register_module,
)
from kg_build_system.workflow.ir import WorkflowContractIR


def create_demo_blueprint() -> BuildBlueprint:
    return create_blueprint(
        modules=(
            register_module(CollapseExactDuplicatesModule),
            register_module(FileModule, FileModuleConfiguration("graph.jsonl")),
            register_module(Neo4jModule),
        ),
    )


def compile_demo() -> WorkflowContractIR:
    return compile(
        modules=(
            register_module(CollapseExactDuplicatesModule),
            register_module(FileModule, FileModuleConfiguration("graph.jsonl")),
            register_module(Neo4jModule),
        ),
    )


def run_demo() -> None:
    """Write the graph and compilation artifacts to ``reference_project/build``."""
    output_dir = Path(__file__).parent / "build"
    output_dir.mkdir(exist_ok=True)

    contract = compile_demo()
    build(contract, output_directory=output_dir)


if __name__ == "__main__":
    run_demo()
