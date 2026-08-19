"""Generated logical contracts for the synthetic complex-cases demo."""

from kg_build_system.code_generation import generation
from kg_build_system.code_generation.builtins import (
    DataContractInferenceConfig,
    InferDataContractProvider,
)


complex_records = generation(
    InferDataContractProvider,
    DataContractInferenceConfig(
        source="../data/complex_records.json",
        mode="table",
    ),
)
