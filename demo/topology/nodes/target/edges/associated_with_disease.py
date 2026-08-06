from kg_build_system import Edge, PropertySlot, property

from demo.topology.nodes.disease.disease import DiseaseNode
from demo.topology.nodes.target.target import TargetNode


class AssociatedWithEdge(Edge[TargetNode, DiseaseNode]):
    """Evidence-backed target-disease association."""
    score: PropertySlot[float] = property()
    study_name: PropertySlot[str] = property()
    evidence_disease_id: PropertySlot[str] = property()
    evidence_label: PropertySlot[str] = property()
