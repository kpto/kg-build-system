from kg_build_system import GraphComponent, PropertySlot, edge, property

from demo.topology.nodes.disease.disease import Disease
from demo.topology.nodes.target.target import Target


@edge(source=Target, target=Disease, description="Evidence-backed target-disease association.")
class AssociatedWith(GraphComponent):
    score: PropertySlot[float] = property(name="score", nullable=False)
    study_name: PropertySlot[str] = property(name="study_name", nullable=False)
    evidence_disease_id: PropertySlot[str] = property(name="evidence_disease_id", nullable=False)
    evidence_label: PropertySlot[str] = property(name="evidence_label", nullable=False)
