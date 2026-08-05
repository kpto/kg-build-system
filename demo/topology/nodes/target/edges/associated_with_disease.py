from kg_build_system import GraphComponent, PropertySlot, edge, property

from demo.topology.nodes.disease.disease import DiseaseNode
from demo.topology.nodes.target.target import TargetNode


@edge(source=TargetNode, target=DiseaseNode, description="Evidence-backed target-disease association.")
class AssociatedWithEdge(GraphComponent):
    score: PropertySlot[float] = property()
    study_name: PropertySlot[str] = property()
    evidence_disease_id: PropertySlot[str] = property()
    evidence_label: PropertySlot[str] = property()
