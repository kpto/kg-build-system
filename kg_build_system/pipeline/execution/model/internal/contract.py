"""The build's frozen view of a workflow contract."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .....kernel import (
    Connection,
    DefinedStep,
    Given,
    ModuleDefinition,
    TakenInput,
)


@dataclass(frozen=True, slots=True)
class Instruction:
    """One step instruction, discriminated by ``kind``.

    ``payload`` is the JSON-compatible value the instruction carries. The build
    interprets it according to ``kind``; it does not look for execution facts in
    any other contract field.
    """

    kind: str
    payload: Any = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, str) or not self.kind:
            raise ValueError("an instruction kind must be a non-empty string")


@dataclass(frozen=True, slots=True)
class ContractStep:
    """One step with the module and instruction it will execute."""

    module_id: str
    module: ModuleDefinition
    name: str
    inputs: tuple[TakenInput, ...] = ()
    outputs: tuple[Given, ...] = ()
    instruction: Instruction | None = None
    variables: Any = None

    @property
    def defined_step(self) -> DefinedStep:
        """The kernel step value passed to an instruction executor."""
        return DefinedStep(
            self.name, self.inputs, self.outputs, self.instruction,
        )


@dataclass(frozen=True, slots=True)
class ContractWorkflow:
    """A contract workflow flattened into its executable steps."""

    steps: tuple[ContractStep, ...] = ()
    connections: tuple[Connection, ...] = ()

    @property
    def steps_by_module(self) -> tuple[tuple[str, ContractStep], ...]:
        """Every step with the id of the module that contributed it."""
        return tuple((step.module_id, step) for step in self.steps)


@dataclass(frozen=True, slots=True)
class BuildContract:
    """The contract body a build executes, with its provenance."""

    workflow: ContractWorkflow
    fingerprint: str = ""
    provenance: Any = None


__all__ = [
    "BuildContract",
    "ContractStep",
    "ContractWorkflow",
    "Instruction",
]
