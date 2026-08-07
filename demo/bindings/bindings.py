"""Collect the topology-aligned graph bindings for build composition."""

from kg_build_system import Binding

from demo.bindings.nodes.disease.disease import disease_from_reference
from demo.bindings.nodes.study.study import study_from_contract
from demo.bindings.nodes.target.edges.associated_with_disease import association_to_disease
from demo.bindings.nodes.target.target import target_from_reference


def demo_bindings() -> tuple[Binding, ...]:
    return (
        target_from_reference,
        study_from_contract,
        disease_from_reference,
        association_to_disease,
    )
