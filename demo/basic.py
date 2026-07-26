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
@table(name="association")
class Association(TableContract):
    target_id: Declaration[str] = field(name="target_id")
    target_symbol: Declaration[str] = field(name="target_symbol")
    disease_ids: Declaration[list[str]] = field(name="disease_ids")
    score: Declaration[float] = field(name="score")

@projection
class AssociationTable(Specification):
    target_id: Declaration[str] = projected_field(Association.target_id)
    target_symbol: Declaration[str] = projected_field(Association.target_symbol)
    disease_id: Declaration[str] = projected_field(
        provide.collection.expand(provide.value.cast(Association.disease_ids, "VARCHAR[]"))
    )
    score: Declaration[float] = projected_field(Association.score)

root = Path(__file__).parent
source = bind_source(target=Association, config=DataSourceConfig(str(root / "association.csv")))
graph = compile_graph(bindings=[
    node_binding(target=Target, build_key=AssociationTable.target_id, properties=Target(symbol=AssociationTable.target_symbol)),
    node_binding(target=Disease, build_key=AssociationTable.disease_id, properties=Disease(name=AssociationTable.disease_id)),
    edge_binding(target=AssociatedWith, build_key=provide.value.deterministic_uuid(provide.value.concat(AssociationTable.target_id, AssociationTable.disease_id)), source_build_key=AssociationTable.target_id, target_build_key=AssociationTable.disease_id, properties=AssociatedWith(score=AssociationTable.score)),
], projections=[AssociationTable])
definition = compile_build(graph=graph, sources=[source], target=FileTarget(str(root / "graph.jsonl")))
if __name__ == "__main__":
    print(definition.sql)
    print(execute_build(definition))
