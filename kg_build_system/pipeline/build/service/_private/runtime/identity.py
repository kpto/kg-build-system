"""How the build names steps and openings across one workflow."""
from __future__ import annotations

from ......kernel import Given

DEFAULT_OUTPUT_NAME = "output"


def output_name(given: Given) -> str:
    """The name an output or publication takes in an outcome."""
    return given.name or DEFAULT_OUTPUT_NAME


def step_identity(module_id: str, name: str) -> str:
    """The identity of one step across the whole workflow."""
    return f"{module_id}::{name}"


def opening_identity(identity: str, name: str) -> str:
    """The identity of one input or output of a step known by its identity."""
    return f"{identity}.{name}"


__all__ = [
    "DEFAULT_OUTPUT_NAME",
    "opening_identity",
    "output_name",
    "step_identity",
]
