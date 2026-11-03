"""Compatibility import path for the built-in inference provider."""
from __future__ import annotations

from .config import ColumnOverride, DataContractInferenceConfig
from .provider import InferDataContractProvider

__all__ = ["ColumnOverride", "DataContractInferenceConfig", "InferDataContractProvider"]
