"""Compatibility shim for :mod:`kg_build_system.workflow._private.identity`."""
from __future__ import annotations

from ._private.identity import (
    DEFAULT_INPUT_NAME,
    DEFAULT_OUTPUT_NAME,
    DEFAULT_STEP_NAME,
    expanded_input_name,
    input_name,
    opening_identity,
    output_name,
    step_identity,
    step_name,
    type_text,
)

__all__ = [
    "DEFAULT_INPUT_NAME",
    "DEFAULT_OUTPUT_NAME",
    "DEFAULT_STEP_NAME",
    "expanded_input_name",
    "input_name",
    "opening_identity",
    "output_name",
    "step_identity",
    "step_name",
    "type_text",
]
