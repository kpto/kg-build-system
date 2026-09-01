"""Composition entry points for the monitored-sites reference build."""

from pathlib import Path

from kg_build_system import build, compile, create_blueprint
from kg_build_system.compile.models import BuildBlueprint
from kg_build_system.modules import (
    CollapseExactDuplicatesModule,
    FileModule,
    FileModuleConfiguration,
    MetaGraphModule,
    Neo4jModule,
    register_module,
)
from kg_build_system.workflow.ir import WorkflowContractIR


def _modules():
    return (
        register_module(CollapseExactDuplicatesModule),
        register_module(FileModule, FileModuleConfiguration("graph.jsonl")),
        register_module(MetaGraphModule),
        register_module(Neo4jModule),
    )


def create_reference_blueprint() -> BuildBlueprint:
    return create_blueprint(modules=_modules())


def compile_reference_build() -> WorkflowContractIR:
    return compile(modules=_modules())


def run_reference_build() -> None:
    """Write the graph and compilation artifacts to ``reference_project/build``."""
    output_dir = Path(__file__).parent / "build"
    output_dir.mkdir(exist_ok=True)

    contract = compile_reference_build()
    build(contract, output_directory=output_dir)


if __name__ == "__main__":
    run_reference_build()
