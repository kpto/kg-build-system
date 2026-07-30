"""Declarative graph-normalisation operations for build blueprints."""
from typing import Literal, cast

from .compile.models import PostProcessingDefinition

type NormalisationOperation = Literal["collapse_exact_duplicates", "merge_compatible_facts"]
type ValidationOperation = Literal["reject_null_build_keys", "reject_null_edge_endpoints", "reject_conflicting_non_null_values", "require_edge_endpoints"]

def collapse_exact_duplicates() -> Literal["collapse_exact_duplicates"]:
    return "collapse_exact_duplicates"

def merge_compatible_facts() -> Literal["merge_compatible_facts"]:
    return "merge_compatible_facts"

def reject_conflicting_non_null_values() -> Literal["reject_conflicting_non_null_values"]:
    return "reject_conflicting_non_null_values"

def reject_null_build_keys() -> Literal["reject_null_build_keys"]:
    return "reject_null_build_keys"

def reject_null_edge_endpoints() -> Literal["reject_null_edge_endpoints"]:
    return "reject_null_edge_endpoints"

def require_edge_endpoints() -> Literal["require_edge_endpoints"]:
    return "require_edge_endpoints"

def validate(*checks: ValidationOperation) -> tuple[Literal["validation"], tuple[ValidationOperation, ...]]:
    return "validation", checks

def normalise_graph(*operations: NormalisationOperation | tuple[Literal["validation"], tuple[ValidationOperation, ...]]) -> PostProcessingDefinition:
    """Declare the portable MVP graph-finalisation pipeline."""
    normalisation = tuple(operation for operation in operations if isinstance(operation, str))
    validation_blocks = tuple(operation[1] for operation in operations if not isinstance(operation, str))
    if len(validation_blocks) != 1: raise ValueError("normalise_graph requires exactly one validate(...) block")
    return PostProcessingDefinition(operations=cast(tuple[NormalisationOperation, ...], normalisation), validations=validation_blocks[0])
