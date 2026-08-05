"""Composition root for the structured authoring reference.

Run ``python demo/build.py`` to compile the declarations and write inspectable
artifacts under ``demo/output``.
"""

from dataclasses import asdict
import json
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

from demo.bindings.bindings import demo_bindings
from demo.table.projections.association_evidence import AssociationEvidenceProjection
from demo.table.sources import demo_sources


OUTPUT_DIRECTORY = Path(__file__).parent / "build"


def create_demo_blueprint() -> BuildBlueprint:
    """Compose reusable declarations with concrete sources and workflow modules."""
    return create_blueprint(
        bindings=demo_bindings(),
        projections=(AssociationEvidenceProjection,),
        sources=demo_sources(),
        modules=(
            CollapseExactDuplicatesModule(),
            RejectConflictingNonNullValuesModule(),
            MergeCompatibleFactsModule(),
            FileModule(FileModuleConfiguration(str(OUTPUT_DIRECTORY / "graph.jsonl"))),
        ),
    )


def compile_demo() -> BuildContract:
    return compile_blueprint(blueprint=create_demo_blueprint())


def run_demo() -> None:
    """Write the graph and inspectable compilation artifacts to ``demo/output``."""
    OUTPUT_DIRECTORY.mkdir(exist_ok=True)
    blueprint = create_demo_blueprint()
    contract = compile_blueprint(blueprint=blueprint)
    (OUTPUT_DIRECTORY / "build_blueprint.json").write_text(blueprint.model_dump_json(indent=2), encoding="utf-8")
    (OUTPUT_DIRECTORY / "build_contract.json").write_text(contract.model_dump_json(indent=2), encoding="utf-8")
    report = build(contract)
    (OUTPUT_DIRECTORY / "build_report.json").write_text(
        json.dumps(
            asdict(report),
            indent=2,
            sort_keys=True,
            default=lambda item: item.model_dump(mode="json") if hasattr(item, "model_dump") else str(item),
        ),
        encoding="utf-8",
    )
    print(report)


if __name__ == "__main__":
    run_demo()
