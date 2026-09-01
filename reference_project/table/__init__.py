"""Generated logical contracts for the monitored-sites reference build."""

from kg_build_system.code_generation import generation
from kg_build_system.code_generation.builtins import (
    DataContractInferenceConfig,
    InferDataContractProvider,
)


monitored_sites = generation(
    InferDataContractProvider,
    DataContractInferenceConfig(
        source="../data/monitored_sites.json",
        mode="table",
    ),
)
