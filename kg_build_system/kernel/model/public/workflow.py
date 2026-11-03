"""The workflow model: instructions, steps, connections and components.

These values are frozen and anaemic. The kernel owns their shape and scheduling
facts; it never reads an instruction's payload or an artifact's value.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

type JsonValue = str | int | float | bool | None | list["JsonValue"] | dict[
    str, "JsonValue"
]
type InstructionKind = tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Instruction:
    """One opaque instruction discriminated by an exact tuple kind.

    ``kind`` is compared exactly; there is no prefix matching. ``payload`` is
    JSON-compatible and is read only by the executor registered for the kind.

    Example:
    ```python
    from kg_build_system.kernel import Instruction

    instruction = Instruction(("echo", "default"), {"text": "hello"})
    assert instruction.kind == ("echo", "default")
    ```
    """

    kind: InstructionKind
    payload: JsonValue


@dataclass(frozen=True, slots=True)
class ArtifactType:
    """The declared type of an artifact, as a namespace and a name.

    Both fields are patterns when used in an ``Input``; matching uses
    ``fnmatchcase``. An actual artifact type must match both patterns.

    Example:
    ```python
    from kg_build_system.kernel import ArtifactType

    value_type = ArtifactType("echo", "text")
    assert value_type.name == "text"
    ```
    """

    namespace: str
    name: str


@dataclass(frozen=True, slots=True)
class Input:
    """A typed input a step consumes from another step's output.

    ``name`` is the resolved opening name, or ``None`` while the input is still
    only a declaration. ``input_name`` is the declared input the opening came
    from; every opening expanded from one open input shares it.

    Example:
    ```python
    from kg_build_system.kernel import ArtifactType, Input

    source = Input(ArtifactType("echo", "text"), "value", "value")
    assert source.input_name == "value"
    ```
    """

    type: ArtifactType
    name: str | None = None
    input_name: str = ""


@dataclass(frozen=True, slots=True)
class Output:
    """An artifact a step produces for downstream steps.

    Example:
    ```python
    from kg_build_system.kernel import ArtifactType, Output

    result = Output(ArtifactType("echo", "text"), "value")
    ```
    """

    type: ArtifactType
    name: str | None = None


@dataclass(frozen=True, slots=True)
class Publication:
    """An output that is also a final workflow artifact.

    A publication is addressable downstream like an output and appears in the
    workflow report after execution.

    Example:
    ```python
    from kg_build_system.kernel import ArtifactType, Publication

    report = Publication(ArtifactType("echo", "text"), "value")
    ```
    """

    type: ArtifactType
    name: str | None = None


type Given = Output | Publication


@dataclass(frozen=True, slots=True)
class Step:
    """One scheduled instruction and the ports it reads and writes.

    ``component`` is the id assigned by the planner that produced the step.
    ``assembly_preference`` is ``"eager"`` when the assembler may share or
    reorganise the step, and ``"deferred"`` when it must keep the step intact.

    Example:
    ```python
    from kg_build_system.kernel import (
        ArtifactType, Input, Instruction, Output, Step,
    )

    step = Step(
        "echo",
        "echo",
        (Input(ArtifactType("echo", "text"), "value", "value"),),
        (Output(ArtifactType("echo", "text"), "value"),),
        Instruction(("echo", "default"), None),
    )
    ```
    """

    component: str
    name: str
    inputs: tuple[Input, ...]
    outputs: tuple[Output | Publication, ...]
    instruction: Instruction
    assembly_preference: Literal["eager", "deferred"] = "eager"


@dataclass(frozen=True, slots=True)
class Connection:
    """A resolved edge from one input opening to one output opening.

    Example:
    ```python
    from kg_build_system.kernel import Connection

    edge = Connection("echo.source", "echo.value")
    ```
    """

    input_id: str
    output_id: str


@dataclass(frozen=True, slots=True)
class RuntimeField:
    """One runtime value an operator must supply for a component.

    Example:
    ```python
    from kg_build_system.kernel import RuntimeField

    field = RuntimeField("api_token", "Token for the source API", secret=True)
    assert field.secret
    ```
    """

    key: str
    description: str
    required: bool = True
    value_type: Literal["string", "integer", "number", "boolean", "json"] = "string"
    secret: bool = False


@dataclass(frozen=True, slots=True)
class Component:
    """One planner's identity, version and runtime fields.

    Example:
    ```python
    from kg_build_system.kernel import Component, RuntimeField

    component = Component(
        "echo", "1", (RuntimeField("prefix", "Text to prepend"),),
    )
    assert component.id == "echo"
    ```
    """

    id: str
    version: str
    runtime_fields: tuple[RuntimeField, ...] = ()


@dataclass(frozen=True, slots=True)
class WorkflowPlan:
    """An assembled instruction DAG and the components that declared it.

    Step identity is ``f"{component}.{name}"`` and an opening identity is
    ``f"{step_id}.{opening_name}"``. Provenance is opaque to the kernel.

    Example:
    ```python
    from kg_build_system.kernel import WorkflowPlan

    plan = WorkflowPlan(components=(), steps=())
    assert plan.connections == ()
    ```
    """

    components: tuple[Component, ...]
    steps: tuple[Step, ...]
    connections: tuple[Connection, ...] = ()
    provenance: JsonValue | None = None


__all__ = [
    "ArtifactType", "Component", "Connection", "Given", "Input", "Instruction",
    "InstructionKind", "JsonValue", "Output", "Publication", "RuntimeField",
    "Step", "WorkflowPlan",
]
