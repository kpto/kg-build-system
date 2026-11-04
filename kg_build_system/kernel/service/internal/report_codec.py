"""Workflow report codec interface: a thin wrapper over the private codec.

The implementation lives in ``service._private``; this function delegates with a
function-local import.
"""
from __future__ import annotations

from typing import Any

from ...model.public.runtime import WorkflowReport


def workflow_report_to_document(report: WorkflowReport) -> dict[str, Any]:
    """Render a workflow report as a JSON-safe document."""
    from .._private.report_codec import (
        workflow_report_to_document as implementation,
    )

    return implementation(report)


__all__ = ["workflow_report_to_document"]
