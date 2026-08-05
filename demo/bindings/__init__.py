"""Graph-slot mappings, mirroring the topology's node-first hierarchy."""

from kg_build_system.binding.models import EdgeBinding, NodeBinding

from .nodes.disease.disease import disease_from_evidence
from .nodes.study.study import study_from_contract
from .nodes.target.edges.associated_with_disease import association_to_disease
from .nodes.target.target import target_from_association


def demo_bindings() -> tuple[NodeBinding | EdgeBinding, ...]:
    return (
        target_from_association,
        study_from_contract,
        disease_from_evidence,
        association_to_disease,
    )


__all__ = ["demo_bindings"]
