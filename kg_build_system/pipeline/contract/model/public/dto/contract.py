"""The shared workflow contract: contributions, steps, connections, provenance.

The contract owns structure only. A step owns its instruction, and an
instruction is an opaque kind plus a JSON payload; SQL is one instruction kind,
not a contract field. Every value here is frozen and anaemic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, TypeAlias

from pydantic import JsonValue


@dataclass(frozen=True, slots=True)
class ArtifactTypeDTO:
    """The namespace and name of one artifact type."""

    namespace: str
    name: str


@dataclass(frozen=True, slots=True)
class InputDTO:
    """One opening a step takes.

    ``name`` is the opening's own name once assembly settles it; it is
    ``None`` while the contribution is still only a declaration. ``input_name``
    is the declared input the opening came from, which every opening expanded
    from one open input shares.
    """

    type: ArtifactTypeDTO
    name: str | None
    input_name: str


@dataclass(frozen=True, slots=True)
class OutputDTO:
    """One output a step gives out inside the workflow."""

    type: ArtifactTypeDTO
    name: str | None = None
    kind: Literal["output"] = field(default="output", init=False)


@dataclass(frozen=True, slots=True)
class PublicationDTO:
    """One publication a step gives out of the workflow."""

    type: ArtifactTypeDTO
    name: str | None = None
    kind: Literal["publication"] = field(default="publication", init=False)


GivenDTO: TypeAlias = OutputDTO | PublicationDTO


@dataclass(frozen=True, slots=True)
class InstructionDTO:
    """One opaque instruction: a kind and a JSON payload.

    The contract never reads the kind or the payload. A ``python`` instruction
    and a ``sql`` instruction travel through the same fields.
    """

    kind: str
    payload: JsonValue


@dataclass(frozen=True, slots=True)
class StepDTO:
    """One assembled step and its opened inputs, outputs and instruction."""

    name: str
    inputs: tuple[InputDTO, ...]
    outputs: tuple[GivenDTO, ...]
    instruction: InstructionDTO
    assembly_preference: Literal["eager", "deferred"] = "eager"


@dataclass(frozen=True, slots=True)
class RuntimeFieldDTO:
    """One runtime configuration field a module declares."""

    key: str
    description: str
    required: bool = True
    value_type: Literal["string", "integer", "number", "boolean", "json"] = "string"
    secret: bool = False


@dataclass(frozen=True, slots=True)
class ModuleReferenceDTO:
    """The import coordinates and configuration of one module."""

    module_id: str
    import_module: str
    class_qualname: str
    implementation_version: str
    configuration: JsonValue | None = None


@dataclass(frozen=True, slots=True)
class ModuleDefinitionDTO:
    """A module reference plus the runtime fields its execution needs."""

    reference: ModuleReferenceDTO
    runtime_fields: tuple[RuntimeFieldDTO, ...] = ()


@dataclass(frozen=True, slots=True)
class ContributionDTO:
    """One module's assembled contribution to the workflow."""

    module: ModuleDefinitionDTO
    steps: tuple[StepDTO, ...] = ()


@dataclass(frozen=True, slots=True)
class ConnectionDTO:
    """One resolved connection between two opening identities."""

    input_id: str
    output_id: str


@dataclass(frozen=True, slots=True)
class WorkflowContractDTO:
    """An assembled workflow, its connections and opaque provenance."""

    contributions: tuple[ContributionDTO, ...]
    connections: tuple[ConnectionDTO, ...] = ()
    provenance: JsonValue | None = None


__all__ = [
    "ArtifactTypeDTO",
    "ConnectionDTO",
    "ContributionDTO",
    "GivenDTO",
    "InputDTO",
    "InstructionDTO",
    "ModuleDefinitionDTO",
    "ModuleReferenceDTO",
    "OutputDTO",
    "PublicationDTO",
    "RuntimeFieldDTO",
    "StepDTO",
    "WorkflowContractDTO",
]
