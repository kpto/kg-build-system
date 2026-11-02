"""How an assembled workflow names the steps and openings it was given.

Names belong to the thing that holds them: a step is named among the steps of
its module, and an input or output among the openings of its step. Identity is
what the whole workflow uses, and :func:`step_identity` and
:func:`opening_identity` form it from those names. Nothing here is stored on the
data it describes.
"""
from __future__ import annotations

from ...kernel import (
    ArtifactType,
    Input,
    Output,
    Publication,
    WorkflowStep,
)

DEFAULT_STEP_NAME: str = "step"
"""The word an unnamed step is counted from, when a module gives it no name."""

DEFAULT_INPUT_NAME = "input"
"""What an unnamed opening that takes is called."""

DEFAULT_OUTPUT_NAME = "output"
"""What an unnamed opening that gives out is called."""


def step_name(step: WorkflowStep, position: int) -> str:
    """The name a step goes by within its module: its own, or its position."""
    return step.name if step.name is not None else f"{DEFAULT_STEP_NAME}{position + 1}"


def input_name(declared: Input) -> str:
    """The name a declared input goes by within its step."""
    return declared.name if declared.name is not None else DEFAULT_INPUT_NAME


def output_name(given: Output | Publication) -> str:
    """The name a declared output or publication goes by within its step."""
    return given.name if given.name is not None else DEFAULT_OUTPUT_NAME


def type_text(artifact_type: ArtifactType) -> str:
    """One artifact type written as a single name, as it appears in an identity."""
    return f"{artifact_type.namespace}.{artifact_type.name}"


def expanded_input_name(declared_name: str, taken_type: ArtifactType) -> str:
    """The name of one port an open input grew into, so its ports stay neighbours."""
    return f"{declared_name}:{type_text(taken_type)}"


def step_identity(module_id: str, name: str) -> str:
    """The identity of one step across the whole workflow."""
    return f"{module_id}::{name}"


def opening_identity(identity: str, name: str) -> str:
    """The identity of one input or output of a step known by its identity."""
    return f"{identity}.{name}"


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
