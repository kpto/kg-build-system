"""Composition entry points for the monitored-sites reference build."""

from pathlib import Path

from kg_build_system import compile, create_blueprint, execute
from kg_build_system.declaration.blueprint import GraphBlueprint
from kg_build_system.distribution import (
    CollapseExactDuplicatesModule,
    FileModule,
    FileModuleConfiguration,
    MetaGraphModule,
    Neo4jModule,
    register_module,
)
from kg_build_system.pipeline.contract import WorkflowContractDTO


PROJECT_ROOT = Path(__file__).parent


def _modules():
    return (
        register_module(CollapseExactDuplicatesModule),
        register_module(FileModule, FileModuleConfiguration("graph.jsonl")),
        register_module(MetaGraphModule),
        register_module(Neo4jModule),
    )


def create_reference_blueprint() -> GraphBlueprint:
    return create_blueprint(namespace_path=PROJECT_ROOT)


def compile_reference_build() -> WorkflowContractDTO:
    return compile(blueprint=create_reference_blueprint(), modules=_modules())


def run_reference_build() -> None:
    """Write the graph and compilation artifacts to ``reference_project/build``."""
    output_dir = PROJECT_ROOT / "build"
    output_dir.mkdir(exist_ok=True)

    contract = compile_reference_build()
    execute(contract, output_directory=output_dir)


if __name__ == "__main__":
    run_reference_build()
