"""Logical contracts for the monitored-estate reference build.

Every contract is inferred from the data it reads, and regenerated whenever a
feed changes. The telemetry directory becomes a table group because each logger
family writes its own partition; the generated catalog follows the directory
layout under ``data/readings``.
"""

from kg_build_system.generation.code_generation import generation
from kg_build_system.generation.code_generation.builtins import (
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
    DataContractInferenceConfig(
        source="../data/surveys.json",
        mode="table",
        # ``surveyed_on`` holds ``YYYY-MM-DDTHH:MM`` without seconds, which
        # ``read_json_auto`` sniffs as VARCHAR rather than TIMESTAMP, so the
        # temporal type is declared here and the scan applies the checked cast.
        # That seconds-free spelling is load-bearing: writing ``14:20:00`` makes
        # the reader report TIMESTAMP and this declaration silently does nothing.
        # Overrides are keyed by the column's full ``<relation>.<column>`` path.
        override={"surveys.surveyed_on": {"type": "timestamp"}},
    ),
)

readings = generation(
    InferDataContractProvider,
    DataContractInferenceConfig(
        source="../data/readings",
        mode="table_group",
        layout="files",
        # Every logger family records ``recorded_on`` as ``YYYY-MM-DDTHH:MM``
        # without seconds, which ``read_json_auto`` sniffs as VARCHAR rather
        # than TIMESTAMP, so the type is declared per relation: the full path
        # says which relation's column it means, and relations keep their own
        # contracts. That seconds-free spelling is load-bearing: writing
        # ``14:20:00`` makes the reader report TIMESTAMP and a declaration
        # silently does nothing.
        override={
            "temperature.recorded_on": {"type": "timestamp"},
            "mechanical.vibration.recorded_on": {"type": "timestamp"},
        },
    ),
)
