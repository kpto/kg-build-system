"""Optional provider implementations distributed with kg-build-system.

These providers use exactly the same public provider contract as third-party
implementations and have no privileged access to the generation engine.
"""

from .schema_inference import (
    ColumnOverride,
    DataContractInferenceConfig,
    InferDataContractProvider,
)

__all__ = [
    "ColumnOverride",
    "DataContractInferenceConfig",
    "InferDataContractProvider",
]
