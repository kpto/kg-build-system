"""Workflow plan codec interface: thin wrappers over the private codec.

The implementation lives in ``service._private``; these functions delegate with
function-local imports.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ...model.public.workflow import WorkflowPlan


def workflow_plan_to_document(plan: WorkflowPlan) -> dict[str, Any]:
    """Render a workflow plan as a JSON-safe document."""
    from .._private.workflow_codec import (
        workflow_plan_to_document as implementation,
    )

    return implementation(plan)


def workflow_plan_from_document(document: Mapping[str, Any]) -> WorkflowPlan:
    """Read a workflow plan from its JSON-safe document."""
    from .._private.workflow_codec import (
        workflow_plan_from_document as implementation,
    )

    return implementation(document)


__all__ = ["workflow_plan_from_document", "workflow_plan_to_document"]
