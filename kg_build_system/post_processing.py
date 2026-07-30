"""Declarative graph-normalisation operations for build blueprints."""
from typing import Literal

from .definition.ir import PostProcessingDefinition

type NormalisationOperation = Literal[
    "collapse_exact_duplicates", "merge_compatible_facts",
    "reject_conflicting_non_null_values", "validate_edge_endpoints",
]

def collapse_exact_duplicates() -> Literal["collapse_exact_duplicates"]:
    return "collapse_exact_duplicates"

def merge_compatible_facts() -> Literal["merge_compatible_facts"]:
    return "merge_compatible_facts"

def reject_conflicting_non_null_values() -> Literal["reject_conflicting_non_null_values"]:
    return "reject_conflicting_non_null_values"

def validate_edge_endpoints() -> Literal["validate_edge_endpoints"]:
    return "validate_edge_endpoints"

def normalise_graph(*operations: NormalisationOperation) -> PostProcessingDefinition:
    """Declare the portable MVP graph-finalisation pipeline."""
    return PostProcessingDefinition(operations=operations)
