"""Creation and fingerprinting of immutable workflow execution contracts."""
from __future__ import annotations

from hashlib import sha256

from pydantic import JsonValue

from .ir import WorkflowContractIR
from .._private.mapping import workflow_to_ir
from .models import WorkflowDefinition


def create_workflow_contract(
    workflow: WorkflowDefinition,
    provenance: JsonValue | None = None,
) -> WorkflowContractIR:
    """Freeze an assembled workflow into the executable contract.

    The fingerprint is the SHA-256 of the serialised workflow IR, so any change
    to contribution order, a step, an opening, a type, module data or a
    connection changes it. The contract carries no schema version.
    """
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
