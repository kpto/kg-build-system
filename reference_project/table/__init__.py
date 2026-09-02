"""Logical contracts for the monitored-estate reference build.

Every contract is inferred from the data it reads, and regenerated whenever a
feed changes. The telemetry directory becomes a table group because each logger
family writes its own partition; the generated catalog follows the directory
layout under ``data/readings``.
"""

from kg_build_system.code_generation import generation
from kg_build_system.code_generation.builtins import (
    DataContractInferenceConfig,
    InferDataContractProvider,
)

sites = generation(
    InferDataContractProvider,
    DataContractInferenceConfig(source="../data/sites.json", mode="table"),
)

equipment = generation(
    InferDataContractProvider,
    DataContractInferenceConfig(source="../data/equipment.json", mode="table"),
)

surveys = generation(
    InferDataContractProvider,
    DataContractInferenceConfig(source="../data/surveys.json", mode="table"),
)

readings = generation(
    InferDataContractProvider,
    DataContractInferenceConfig(
        source="../data/readings",
        mode="table_group",
        layout="files",
    ),
)
