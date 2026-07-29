"""Run with: python -m demo.basic (after installing project dependencies)."""
from pathlib import Path
from kg_build_system import (
    DataSourceConfig, Declaration, GraphComponent, TableContract, bind_source,
    build as execute_build, compile_build, compile_graph, edge, edge_binding,
    field, node, node_binding, projection, projected_field, property, provide, table,
)
from kg_build_system.targets import FileTarget
from kg_build_system.specification import Specification

@node(description="A biological target")
class Target(GraphComponent):
    symbol: Declaration[str] = property(name="symbol", nullable=False)
@node(description="A disease")
class Disease(GraphComponent):
    name: Declaration[str] = property(name="name", nullable=False)
@edge(source=Target, target=Disease)
class AssociatedWith(GraphComponent):
    score: Declaration[float] = property(name="score", nullable=False)
    study_name: Declaration[str] = property(name="study_name", nullable=False)
    evidence_label: Declaration[str] = property(name="evidence_label", nullable=False)
@table(name="association")
class Association(TableContract):
    target_id: Declaration[str] = field(name="target_id")
    target_symbol: Declaration[str] = field(name="target_symbol")
    study_id: Declaration[str] = field(name="study_id")
    evidence: Declaration[str] = field(name="evidence")
    score: Declaration[float] = field(name="score")

@table(name="study")
class Study(TableContract):
    id: Declaration[str] = field(name="id")
    name: Declaration[str] = field(name="name")

@projection
class AssociationTable(Specification):
    target_id: Declaration[str] = projected_field(Association.target_id)
    target_symbol: Declaration[str] = projected_field(Association.target_symbol)
    evidence_item = provide.collection.expand(
        provide.value.cast(Association.evidence, "STRUCT(disease_id VARCHAR, labels VARCHAR[])[]")
    )
    disease_id: Declaration[str] = projected_field(provide.value.struct_field(evidence_item, "disease_id", as_type=str))
    evidence_label: Declaration[str] = projected_field(
        provide.collection.expand(provide.value.struct_field(evidence_item, "labels", as_type=list[str]))
    )
    study_name: Declaration[str] = projected_field(
        provide.lookup.one(key=Association.study_id, match=Study.id, value=Study.name, as_type=str)
    )
    score: Declaration[float] = projected_field(Association.score)

root = Path(__file__).parent
source = bind_source(target=Association, config=DataSourceConfig(str(root / "association.csv")))
study_source = bind_source(target=Study, config=DataSourceConfig(str(root / "studies.csv")))
graph = compile_graph(bindings=[
    node_binding(target=Target, build_key=AssociationTable.target_id, properties=Target(symbol=AssociationTable.target_symbol)),
    node_binding(target=Disease, build_key=AssociationTable.disease_id, properties=Disease(name=AssociationTable.disease_id)),
    edge_binding(target=AssociatedWith, build_key=provide.value.deterministic_uuid(provide.value.concat(AssociationTable.target_id, AssociationTable.disease_id, AssociationTable.evidence_label)), source_build_key=AssociationTable.target_id, target_build_key=AssociationTable.disease_id, properties=AssociatedWith(score=AssociationTable.score, study_name=AssociationTable.study_name, evidence_label=AssociationTable.evidence_label)),
], projections=[AssociationTable])
definition = compile_build(graph=graph, sources=[source, study_source], target=FileTarget(str(root / "graph.jsonl")))
if __name__ == "__main__":
    print(definition.sql)
    print(execute_build(definition))
