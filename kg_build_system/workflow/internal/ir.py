"""Compilation IR for a frozen workflow definition.

These values are the serialisable form used at the contract boundary. Execution
converts them back to the workflow models before any module handler sees them.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class WorkflowIR(BaseModel):
    """Base for the frozen, strict workflow IR values."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class ModuleReferenceIR(WorkflowIR):
    """The import coordinates and configuration of one module."""

    module_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    import_module: str = Field(min_length=1)
    class_qualname: str = Field(min_length=1)
    implementation_version: str = Field(min_length=1)
    configuration: JsonValue | None = None


class RuntimeFieldIR(WorkflowIR):
    """One runtime configuration field a module declares."""

    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    description: str = Field(min_length=1)
    required: bool = True
    value_type: Literal["string", "integer", "number", "boolean", "json"] = "string"
    secret: bool = False


class ArtifactTypeIR(WorkflowIR):
    """The namespace and name of one artifact type."""

    namespace: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1)


class InputIR(WorkflowIR):
    """One answered opening of an assembled step.

    ``name`` identifies the opening, which an open input shares nothing of with
    its siblings, and ``input_name`` is the declared input it came from, which
    they all share.
    """

    type: ArtifactTypeIR
    name: str = Field(min_length=1)
    input_name: str = Field(min_length=1)


class OutputIR(WorkflowIR):
    """One output a step gives out inside the workflow."""

    kind: Literal["output"] = "output"
    type: ArtifactTypeIR
    name: str = Field(min_length=1)


class PublicationIR(WorkflowIR):
    """One publication a step gives out of the workflow."""

    kind: Literal["publication"] = "publication"
    type: ArtifactTypeIR
    name: str = Field(min_length=1)


GivenIR = Annotated[OutputIR | PublicationIR, Field(discriminator="kind")]


class StepIR(WorkflowIR):
    """One assembled step and its opened inputs and outputs."""

    name: str = Field(min_length=1)
    inputs: tuple[InputIR, ...] = ()
    outputs: tuple[GivenIR, ...] = ()


class ContributionIR(WorkflowIR):
    """One module's assembled contribution."""

    reference: ModuleReferenceIR
    runtime_fields: tuple[RuntimeFieldIR, ...] = ()
    variables: JsonValue | None = None
    steps: tuple[StepIR, ...] = Field(min_length=1)


class ConnectionIR(WorkflowIR):
    """One resolved connection between two opening identities."""

    input_id: str = Field(min_length=1)
    output_id: str = Field(min_length=1)


class WorkflowDefinitionIR(WorkflowIR):
    """An assembled workflow in its serialisable form."""

    contributions: tuple[ContributionIR, ...] = Field(min_length=1)
    connections: tuple[ConnectionIR, ...] = ()


class WorkflowContractIR(WorkflowIR):
    """A frozen workflow, its content fingerprint and opaque provenance."""

    workflow: WorkflowDefinitionIR
    workflow_fingerprint: str = Field(min_length=1)
    provenance: JsonValue | None = None


def encode_workflow_contract(value: WorkflowContractIR) -> dict[str, Any]:
    """Encode a contract into its canonical JSON-compatible representation."""
    return value.model_dump(mode="json")


def decode_workflow_contract(value: Mapping[str, Any]) -> WorkflowContractIR:
    """Decode a contract from its canonical JSON-compatible representation."""
    return WorkflowContractIR.model_validate_json(json.dumps(value))


def workflow_contract_json(
    value: WorkflowContractIR, *, indent: int | None = None,
) -> str:
    """Render a contract as JSON text, the form written beside a build."""
    return value.model_dump_json(indent=indent)


def workflow_contract_from_json(value: str | bytes) -> WorkflowContractIR:
    """Read a contract from the JSON text written by an earlier build."""
    return WorkflowContractIR.model_validate_json(value)


workflow_contract_to_json = workflow_contract_json
"""Alias for :func:`workflow_contract_json`."""


__all__ = [
    "ArtifactTypeIR",
    "ConnectionIR",
    "ContributionIR",
    "GivenIR",
    "InputIR",
    "ModuleReferenceIR",
    "OutputIR",
    "PublicationIR",
    "RuntimeFieldIR",
    "StepIR",
    "WorkflowContractIR",
    "WorkflowDefinitionIR",
    "WorkflowIR",
    "decode_workflow_contract",
    "encode_workflow_contract",
    "workflow_contract_from_json",
    "workflow_contract_json",
    "workflow_contract_to_json",
]
