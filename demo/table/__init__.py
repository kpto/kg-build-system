"""Logical input contracts generated from the example evidence release."""

from kg_build_system.code_generation import generation
from kg_build_system.code_generation.builtins import (
    DataContractInferenceConfig,
    InferDataContractProvider,
)

evidence_release = generation(
    InferDataContractProvider,
    DataContractInferenceConfig(
        source="../data/evidence_release",
        mode="table_group",
    ),
)
