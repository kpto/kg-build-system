"""Creation and fingerprinting of immutable workflow execution contracts."""
from __future__ import annotations

from hashlib import sha256

from pydantic import JsonValue

from .ir import WorkflowContractIR
from .mapping import workflow_to_ir
from .models import WorkflowDefinition


def create_workflow_contract(
    workflow: WorkflowDefinition,
    *,
    provenance: JsonValue | None = None,
) -> WorkflowContractIR:
    workflow_ir = workflow_to_ir(workflow)
    fingerprint = sha256(
        workflow_ir.model_dump_json().encode("utf-8")
    ).hexdigest()
    return WorkflowContractIR(
        workflow=workflow_ir,
        workflow_fingerprint=fingerprint,
        provenance=provenance,
    )


__all__ = ["create_workflow_contract"]
