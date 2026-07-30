"""Run with: python -m demo.basic."""
from pathlib import Path
from kg_build_system import (
    DataSourceConfig, Field, GraphComponent, InputFormat, ProjectedField, PropertySlot, bind,
    bind_source, build as execute_build, compile_build, compile_graph, edge,
    edge_binding, field, node, node_binding, projection, projected_field,
    property, provide, struct, table,
)
from kg_build_system.targets import FileTarget

@node(description="A biological target")
class Target(GraphComponent):
    symbol: PropertySlot[str] = property(name="symbol", nullable=False)

@node(description="A disease")
class Disease(GraphComponent):
    name: PropertySlot[str] = property(name="name", nullable=False)

@node(description="A study that provides evidence provenance")
class StudyNode(GraphComponent):
    name: PropertySlot[str] = property(name="name", nullable=False)

@edge(source=Target, target=Disease)
class AssociatedWith(GraphComponent):
    score: PropertySlot[float] = property(name="score", nullable=False)
    study_name: PropertySlot[str] = property(name="study_name", nullable=False)
    evidence_disease_id: PropertySlot[str] = property(name="evidence_disease_id", nullable=False)
    evidence_label: PropertySlot[str] = property(name="evidence_label", nullable=False)

@struct
class Evidence:
    disease_id: Field[str] = field(name="disease_id")
    labels: Field[list[str]] = field(name="labels")

@table(name="association")
class Association:
    target_id: Field[str] = field(name="target_id")
    target_symbol: Field[str] = field(name="target_symbol")
    study_id: Field[str] = field(name="study_id")
    evidence: Field[list[Evidence]] = field(name="evidence")
    score: Field[float] = field(name="score")

@table(name="study")
class Study:
    id: Field[str] = field(name="id")
    name: Field[str] = field(name="name")

@projection
class AssociationTable:
    target_id: ProjectedField[str] = projected_field(Association.target_id)
    target_symbol: ProjectedField[str] = projected_field(Association.target_symbol)
    disease_id: ProjectedField[str] = projected_field(provide.collection.expand(Association.evidence.element.disease_id))
    evidence_label: ProjectedField[str] = projected_field(provide.collection.expand(Association.evidence.element.labels))
    study_id: ProjectedField[str] = projected_field(Association.study_id)
    score: ProjectedField[float] = projected_field(Association.score)

root = Path(__file__).parent
source = bind_source(target=Association, config=DataSourceConfig(str(root / "association.json"), format=InputFormat.JSON))
study_source = bind_source(target=Study, config=DataSourceConfig(str(root / "studies.json"), format=InputFormat.JSON))
graph = compile_graph(bindings=[
    node_binding(target=Target, build_key=Association.target_id, properties=Target(symbol=bind(Association.target_symbol))),
    node_binding(target=StudyNode, build_key=Study.id, properties=StudyNode(name=bind(Study.name))),
    node_binding(target=Disease, build_key=AssociationTable.disease_id, properties=Disease(name=bind(AssociationTable.disease_id))),
    edge_binding(target=AssociatedWith, build_key=provide.value.deterministic_uuid(provide.value.concat(AssociationTable.target_id, AssociationTable.disease_id, AssociationTable.evidence_label)), source_build_key=AssociationTable.target_id, target_build_key=AssociationTable.disease_id, properties=AssociatedWith(score=bind(AssociationTable.score), study_name=bind(provide.lookup.one(key=AssociationTable.study_id, match=Study.id, value=Study.name, as_type=str)), evidence_disease_id=bind(AssociationTable.disease_id), evidence_label=bind(AssociationTable.evidence_label))),
], projections=[AssociationTable])
definition = compile_build(graph=graph, sources=[source, study_source], target=FileTarget(str(root / "graph.jsonl")))

if __name__ == "__main__":
    (root / "compiled_graph.json").write_text(graph.model_dump_json(indent=2), encoding="utf-8")
    (root / "compiled_build.json").write_text(definition.model_dump_json(indent=2), encoding="utf-8")
    print(definition.sql)
    print(execute_build(definition))
