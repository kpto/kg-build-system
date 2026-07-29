"""Run with: python -m demo.basic (after installing project dependencies)."""
from pathlib import Path
from kg_build_system import (
    DataSourceConfig, Declaration, GraphComponent, InputFormat, TableContract, bind_source,
    build as execute_build, compile_build, compile_graph, edge, edge_binding,
    field, node, node_binding, projection, projected_field, property, provide, struct, table,
)
from kg_build_system.targets import FileTarget
from kg_build_system.specification import Specification

@node(description="A biological target")
class Target(GraphComponent):
    symbol: Declaration[str] = property(name="symbol", nullable=False)
@node(description="A disease")
class Disease(GraphComponent):
    name: Declaration[str] = property(name="name", nullable=False)
@node(description="A study that provides evidence provenance")
class StudyNode(GraphComponent):
    name: Declaration[str] = property(name="name", nullable=False)
@edge(source=Target, target=Disease)
class AssociatedWith(GraphComponent):
    score: Declaration[float] = property(name="score", nullable=False)
    study_name: Declaration[str] = property(name="study_name", nullable=False)
    evidence_disease_id: Declaration[str] = property(name="evidence_disease_id", nullable=False)
    evidence_label: Declaration[str] = property(name="evidence_label", nullable=False)

@struct
class Evidence(TableContract):
    disease_id: Declaration[str] = field(name="disease_id")
    labels: Declaration[list[str]] = field(name="labels")

@table(name="association")
class Association(TableContract):
    target_id: Declaration[str] = field(name="target_id")
    target_symbol: Declaration[str] = field(name="target_symbol")
    study_id: Declaration[str] = field(name="study_id")
    evidence: Declaration[list["Evidence"]] = field(name="evidence")
    score: Declaration[float] = field(name="score")

@table(name="study")
class Study(TableContract):
    id: Declaration[str] = field(name="id")
    name: Declaration[str] = field(name="name")

@projection
class AssociationTable(Specification):
    target_id: Declaration[str] = projected_field(Association.target_id)
    target_symbol: Declaration[str] = projected_field(Association.target_symbol)
    # One unnest level: Association.evidence → evidence.element.disease_id.
    disease_id: Declaration[str] = projected_field(provide.collection.expand(Association.evidence.element.disease_id))
    # Two unnest levels: Association.evidence → evidence.element.labels → label element.
    evidence_label: Declaration[str] = projected_field(provide.collection.expand(Association.evidence.element.labels))
    study_id: Declaration[str] = projected_field(Association.study_id)
    score: Declaration[float] = projected_field(Association.score)

root = Path(__file__).parent
source = bind_source(target=Association, config=DataSourceConfig(str(root / "association.json"), format=InputFormat.JSON))
study_source = bind_source(target=Study, config=DataSourceConfig(str(root / "studies.json"), format=InputFormat.JSON))
graph = compile_graph(bindings=[
    # Component 1: direct binding to Association table.
    node_binding(target=Target, build_key=Association.target_id, properties=Target(symbol=Association.target_symbol)),
    # Component 2: direct binding to a different Study table.
    node_binding(target=StudyNode, build_key=Study.id, properties=StudyNode(name=Study.name)),
    node_binding(target=Disease, build_key=AssociationTable.disease_id, properties=Disease(name=AssociationTable.disease_id)),
    # Component 3: projection values plus a Study-table lookup in one binding.
    edge_binding(target=AssociatedWith, build_key=provide.value.deterministic_uuid(provide.value.concat(AssociationTable.target_id, AssociationTable.disease_id, AssociationTable.evidence_label)), source_build_key=AssociationTable.target_id, target_build_key=AssociationTable.disease_id, properties=AssociatedWith(score=AssociationTable.score, study_name=provide.lookup.one(key=AssociationTable.study_id, match=Study.id, value=Study.name, as_type=str), evidence_disease_id=AssociationTable.disease_id, evidence_label=AssociationTable.evidence_label)),
], projections=[AssociationTable])
definition = compile_build(graph=graph, sources=[source, study_source], target=FileTarget(str(root / "graph.jsonl")))
if __name__ == "__main__":
    (root / "compiled_graph.json").write_text(graph.model_dump_json(indent=2), encoding="utf-8")
    (root / "compiled_build.json").write_text(definition.model_dump_json(indent=2), encoding="utf-8")
    print(definition.sql)
    print(execute_build(definition))
