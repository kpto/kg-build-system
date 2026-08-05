"""Collect the topology-aligned graph bindings for build composition."""

from kg_build_system.binding.models import EdgeBinding, NodeBinding

from demo.bindings.nodes.disease.disease import disease_from_evidence
from demo.bindings.nodes.study.study import study_from_contract
from demo.bindings.nodes.target.edges.associated_with_disease import association_to_disease
from demo.bindings.nodes.target.target import target_from_association


def demo_bindings() -> tuple[NodeBinding | EdgeBinding, ...]:
    return (
        target_from_association,
        study_from_contract,
        disease_from_evidence,
        association_to_disease,
    )
