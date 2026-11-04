"""Encode a ``WorkflowReport`` as a JSON-safe document.

The report uses the same identity form as the workflow-plan codec: a step id is
a ``Key`` array and a publication opening is an ``OpeningId`` key array. An
artifact value keeps the dataclass conversion that ``dataclasses.asdict`` used
to apply, so a value is not silently replaced by its string form.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from typing import Any

from ...model.public.runtime import (
    Failure,
    PublishedArtifact,
    WorkflowReport,
)


def _value_to_document(value: Any) -> Any:
    """Convert one report value the way ``dataclasses.asdict`` did."""
    if is_dataclass(value) and not isinstance(value, type):
        return {
            item.name: _value_to_document(getattr(value, item.name))
            for item in fields(value)
        }
    if isinstance(value, Mapping):
        return {
            key: _value_to_document(item) for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_value_to_document(item) for item in value]
    return value


def _failure_to_document(failure: Failure) -> dict[str, Any]:
    return {
        "message": failure.message,
        "step_id": failure.step_id.key.to_document(),
        "exception_type": failure.exception_type,
    }


def _published_to_document(published: PublishedArtifact) -> dict[str, Any]:
    return {
        "opening": published.opening.key.to_document(),
        "type": published.type.key.to_document(),
        "value": _value_to_document(published.value),
    }


def workflow_report_to_document(report: WorkflowReport) -> dict[str, Any]:
    """Render a workflow report as a JSON-safe document.

    Example:
    ```python
    document = workflow_report_to_document(report)
    assert isinstance(document["published_artifacts"], list)
    ```
    """
    return {
        "published_artifacts": [
            _published_to_document(published)
            for published in report.published_artifacts
        ],
        "recovered_failures": [
            _failure_to_document(failure)
            for failure in report.recovered_failures
        ],
        "unresolved_failures": [
            _failure_to_document(failure)
            for failure in report.unresolved_failures
        ],
        "provenance": _value_to_document(report.provenance),
    }


__all__ = ["workflow_report_to_document"]
