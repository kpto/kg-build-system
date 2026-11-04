"""The workflow model: instructions, steps, connections and components.

These values are frozen and anaemic. The kernel owns their shape and scheduling
facts; it never reads an instruction's payload or an artifact's value.

Every pipeline identity that crosses a planner, executor, runtime or codec
boundary is a role type over ``Key``. A formatted string is display only: it is
never parsed back into an identity.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from .key import Key

type JsonValue = str | int | float | bool | None | list["JsonValue"] | dict[
    str, "JsonValue"
]


class OpeningDirection(StrEnum):
    """Which side of a step one opening belongs to.

    Direction is part of an ``OpeningId`` because an input and an output may
    share one opening name. They are then different openings.

    Example:
    ```python
    from kg_build_system.kernel import OpeningDirection

    assert OpeningDirection.INPUT != OpeningDirection.OUTPUT
    ```
    """

    INPUT = "input"
    OUTPUT = "output"


@dataclass(frozen=True, slots=True)
class StepId:
    """The identity of one step: its component id and its step name.

    ``name`` is one key segment even when it contains dots, such as
    ``projection.defect``. ``Component.version`` is not part of the identity;
    it describes the planner implementation, not the logical step.

    Example:
    ```python
    from kg_build_system.kernel import Key, StepId

    step = StepId("core", "projection.defect")
    assert step.key == Key(("core", "projection.defect"))
    ```
    """

    component: str
    name: str

    def __post_init__(self) -> None:
        for role, value in (
            ("step component", self.component),
            ("step name", self.name),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(f"{role} must be a non-empty string")
            if "/" in value:
                raise ValueError(f"{role} must not contain '/': {value!r}")

    @property
    def key(self) -> Key:
        return Key((self.component, self.name))

    def __str__(self) -> str:
        return str(self.key)


@dataclass(frozen=True, slots=True, init=False)
class OpeningId:
    """The identity of one input or output opening of one step.

    The direction is part of the key, so an input and an output with the same
    opening name are distinct. The opening name is a ``Key``; an expanded open
    input uses one key segment per artifact-type segment.

    Example:
    ```python
    from kg_build_system.kernel import (
        Key, OpeningDirection, OpeningId, StepId,
    )

    step = StepId("core", "echo")
    taken = OpeningId(step, OpeningDirection.INPUT, Key(("value",)))
    given = OpeningId(step, OpeningDirection.OUTPUT, "value")
    assert taken.key != given.key
    ```
    """

    step: StepId
    direction: OpeningDirection
    name: Key

    def __init__(
        self,
        step: StepId,
        direction: OpeningDirection,
        name: Key | str,
    ) -> None:
        if not isinstance(step, StepId):
            raise TypeError("an opening step must be a StepId")
        if not isinstance(direction, OpeningDirection):
            raise TypeError("an opening direction must be an OpeningDirection")
        resolved = Key((name,)) if isinstance(name, str) else name
        if not isinstance(resolved, Key):
            raise TypeError("an opening name must be a Key or a string")
        if not resolved.segments:
            raise ValueError("an opening name must not be empty")
        for segment in resolved.segments:
            if not isinstance(segment, str) or not segment:
                raise ValueError("an opening name segment must be a string")
            if "/" in segment:
                raise ValueError(
                    f"an opening name segment must not contain '/': {segment!r}"
                )
        object.__setattr__(self, "step", step)
        object.__setattr__(self, "direction", direction)
        object.__setattr__(self, "name", resolved)

    @property
    def key(self) -> Key:
        return self.step.key.child(self.direction.value, *self.name.segments)

    def __str__(self) -> str:
        return str(self.key)


@dataclass(frozen=True, slots=True)
class ArtifactType:
    """The concrete type of one artifact, as a ``Key``.

    The key has at least a namespace and one name segment. A concrete type
    contains no wildcard; a pattern is an ``ArtifactPattern``. ``namespace``
    and ``name`` are display properties; an identity is the key.

    Example:
    ```python
    from kg_build_system.kernel import ArtifactType, Key

    node = ArtifactType.of("core", "graph", "node", "defect")
    assert node.key == Key(("core", "graph", "node", "defect"))
    assert node.name == "graph.node.defect"
    ```
    """

    key: Key

    def __post_init__(self) -> None:
        if len(self.key.segments) < 2:
            raise ValueError(
                "an artifact type requires at least two key segments"
            )
        for segment in self.key.segments:
            if not isinstance(segment, str) or not segment:
                raise ValueError("an artifact type has an empty key segment")
            if "/" in segment:
                raise ValueError(
                    f"an artifact type key segment contains '/': {segment!r}"
                )
            if any(character in segment for character in "*?["):
                raise ValueError(
                    "an artifact type must be concrete, not a wildcard: "
                    f"{self.key!r}"
                )

    @classmethod
    def of(cls, namespace: str, *name: str) -> ArtifactType:
        """Build a concrete artifact type from a namespace and name segments.

        Example:
        ```python
        from kg_build_system.kernel import ArtifactType

        value = ArtifactType.of("echo", "text")
        assert value.namespace == "echo"
        ```
        """
        return cls(Key((namespace, *name)))

    @property
    def namespace(self) -> str:
        return self.key.segments[0]

    @property
    def name(self) -> str:
        """The dotted display name. Never parse it; use ``key``."""
        return ".".join(self.key.segments[1:])

    def __str__(self) -> str:
        return str(self.key)


@dataclass(frozen=True, slots=True)
class ArtifactPattern:
    """The declared type an input accepts, as a ``Key`` pattern.

    ``*`` matches inside one segment; a final ``**`` matches zero or more
    remaining segments. Without ``**`` the keys must have the same length.
    ``exact()`` returns the concrete type of a pattern with no wildcard.

    Example:
    ```python
    from kg_build_system.kernel import ArtifactPattern, ArtifactType

    records = ArtifactPattern.of("core", "graph", "**")
    assert records.matches(ArtifactType.of("core", "graph", "node", "defect"))
    ```
    """

    key: Key

    def __post_init__(self) -> None:
        if not self.key.segments:
            raise ValueError("an artifact pattern requires a key segment")
        for segment in self.key.segments:
            if not isinstance(segment, str) or not segment:
                raise ValueError("an artifact pattern has an empty key segment")
            if "/" in segment:
                raise ValueError(
                    f"an artifact pattern segment contains '/': {segment!r}"
                )
        for index, segment in enumerate(self.key.segments):
            if segment == "**" and index != len(self.key.segments) - 1:
                raise ValueError("'**' is only allowed as the final key segment")

    @classmethod
    def of(cls, namespace: str, *name: str) -> ArtifactPattern:
        """Build a pattern from a namespace and name segments.

        Example:
        ```python
        from kg_build_system.kernel import ArtifactPattern

        records = ArtifactPattern.of("core", "graph", "**")
        assert records.is_pattern
        ```
        """
        return cls(Key((namespace, *name)))

    @property
    def namespace(self) -> str:
        return self.key.segments[0]

    @property
    def name(self) -> str:
        """The dotted display name. Never parse it; use ``key``."""
        return ".".join(self.key.segments[1:])

    @property
    def is_pattern(self) -> bool:
        return any(
            segment == "**" or any(character in segment for character in "*?[")
            for segment in self.key.segments
        )

    def matches(self, actual: ArtifactType) -> bool:
        """Whether a concrete artifact type matches this pattern.

        Example:
        ```python
        from kg_build_system.kernel import ArtifactPattern, ArtifactType

        pattern = ArtifactPattern.of("core", "graph", "*", "*")
        assert pattern.matches(ArtifactType.of("core", "graph", "node", "site"))
        ```
        """
        return actual.key.matches(self.key)

    def exact(self) -> ArtifactType:
        """Return the concrete artifact type, refusing a wildcard pattern.

        Example:
        ```python
        from kg_build_system.kernel import ArtifactPattern

        concrete = ArtifactPattern.of("echo", "text").exact()
        assert concrete.name == "text"
        ```
        """
        if self.is_pattern:
            raise ValueError(f"{self} is a pattern, not an exact artifact type")
        return ArtifactType(self.key)

    def __str__(self) -> str:
        return str(self.key)


@dataclass(frozen=True, slots=True)
class InstructionKind:
    """The exact two-segment kind of one instruction.

    ``operation`` names the work and ``engine`` names the executor family.
    Kinds are compared exactly; there is no prefix matching. The named fields
    fix the arity that a bare tuple would leave open.

    Example:
    ```python
    from kg_build_system.kernel import InstructionKind, Key

    kind = InstructionKind("sql", "duckdb")
    assert kind.key == Key(("sql", "duckdb"))
    ```
    """

    operation: str
    engine: str

    def __post_init__(self) -> None:
        for role, value in (
            ("instruction operation", self.operation),
            ("instruction engine", self.engine),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(f"{role} must be a non-empty string")
            if "/" in value:
                raise ValueError(f"{role} must not contain '/': {value!r}")

    @property
    def key(self) -> Key:
        return Key((self.operation, self.engine))

    def __str__(self) -> str:
        return str(self.key)


@dataclass(frozen=True, slots=True)
class Instruction:
    """One opaque instruction discriminated by an exact kind.

    ``kind`` is compared exactly; there is no prefix matching. ``payload`` is
    JSON-compatible and is read only by the executor registered for the kind.

    Example:
    ```python
    from kg_build_system.kernel import Instruction, InstructionKind

    instruction = Instruction(InstructionKind("echo", "default"), {"text": "hi"})
    assert instruction.kind == InstructionKind("echo", "default")
    ```
    """

    kind: InstructionKind
    payload: JsonValue


@dataclass(frozen=True, slots=True)
class Input:
    """A typed opening a step consumes from another step's output.

    ``type`` is the pattern the input accepts. ``opening_name`` is the resolved
    opening name, or ``None`` while the input is still only a declaration.
    ``declared_name`` is the executor's input-map key and remains a string; it
    is not a pipeline identity.

    Example:
    ```python
    from kg_build_system.kernel import ArtifactPattern, Input, Key

    source = Input(ArtifactPattern.of("echo", "text"), Key(("value",)), "value")
    assert source.declared_name == "value"
    ```
    """

    type: ArtifactPattern
    opening_name: Key | None = None
    declared_name: str = ""


@dataclass(frozen=True, slots=True)
class Output:
    """An artifact a step produces for downstream steps.

    Example:
    ```python
    from kg_build_system.kernel import ArtifactType, Key, Output

    result = Output(ArtifactType.of("echo", "text"), Key(("value",)))
    ```
    """

    type: ArtifactType
    opening_name: Key | None = None


@dataclass(frozen=True, slots=True)
class Publication:
    """An output that is also a final workflow artifact.

    A publication is addressable downstream like an output and appears in the
    workflow report after execution.

    Example:
    ```python
    from kg_build_system.kernel import ArtifactType, Key, Publication

    report = Publication(ArtifactType.of("echo", "text"), Key(("value",)))
    ```
    """

    type: ArtifactType
    opening_name: Key | None = None


type Given = Output | Publication


@dataclass(frozen=True, slots=True)
class Step:
    """One scheduled instruction and the ports it reads and writes.

    ``component`` is the id assigned by the planner that produced the step;
    ``name`` is a free-form label inside that component. The pair is the facts;
    ``step_id(step)`` derives the identity. ``assembly_preference`` is
    ``"eager"`` when the assembler may share or reorganise the step, and
    ``"deferred"`` when it must keep the step intact.

    Example:
    ```python
    from kg_build_system.kernel import (
        ArtifactPattern, ArtifactType, Input, Instruction, InstructionKind,
        Key, Output, Step,
    )

    step = Step(
        "echo",
        "echo",
        (Input(ArtifactPattern.of("echo", "text"), Key(("value",)), "value"),),
        (Output(ArtifactType.of("echo", "text"), Key(("value",))),),
        Instruction(InstructionKind("echo", "default"), None),
    )
    ```
    """

    component: str
    name: str
    inputs: tuple[Input, ...]
    outputs: tuple[Output | Publication, ...]
    instruction: Instruction
    assembly_preference: Literal["eager", "deferred"] = "eager"

    @property
    def id(self) -> StepId:
        return StepId(self.component, self.name)


def step_id(step: Step) -> StepId:
    """Derive the identity of one step from the facts it owns.

    Example:
    ```python
    from kg_build_system.kernel import StepId, step_id

    assert str(step_id(step)) == "echo/echo"
    ```
    """
    return step.id


def input_opening(step: Step, taken: Input) -> OpeningId:
    """Return the resolved input opening of one step.

    Example:
    ```python
    from kg_build_system.kernel import OpeningDirection, input_opening

    opening = input_opening(step, step.inputs[0])
    assert opening.direction is OpeningDirection.INPUT
    ```
    """
    if taken.opening_name is None:
        raise ValueError(f"step {step_id(step)} has an unresolved input")
    return OpeningId(step_id(step), OpeningDirection.INPUT, taken.opening_name)


def output_opening(step: Step, given: Output | Publication) -> OpeningId:
    """Return the resolved output opening of one step.

    Example:
    ```python
    from kg_build_system.kernel import OpeningDirection, output_opening

    opening = output_opening(step, step.outputs[0])
    assert opening.direction is OpeningDirection.OUTPUT
    ```
    """
    if given.opening_name is None:
        raise ValueError(f"step {step_id(step)} has an unresolved output")
    return OpeningId(step_id(step), OpeningDirection.OUTPUT, given.opening_name)


@dataclass(frozen=True, slots=True)
class Connection:
    """A resolved edge from one input opening to one output opening.

    The input field holds an input opening and the output field holds an output
    opening; the constructor refuses any other direction.

    Example:
    ```python
    from kg_build_system.kernel import Connection, input_opening, output_opening

    edge = Connection(
        input=input_opening(consumer, consumer.inputs[0]),
        output=output_opening(producer, producer.outputs[0]),
    )
    ```
    """

    input: OpeningId
    output: OpeningId

    def __post_init__(self) -> None:
        if self.input.direction is not OpeningDirection.INPUT:
            raise ValueError("a connection input must be an input opening")
        if self.output.direction is not OpeningDirection.OUTPUT:
            raise ValueError("a connection output must be an output opening")


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

    `StepId` and `OpeningId` identify every step and port. A step must be
    resolved before the plan is executable. Provenance is opaque to the kernel.

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
    "ArtifactPattern", "ArtifactType", "Component", "Connection", "Given",
    "Input", "Instruction", "InstructionKind", "JsonValue", "OpeningDirection",
    "OpeningId", "Output", "Publication", "RuntimeField", "Step", "StepId",
    "WorkflowPlan", "input_opening", "output_opening", "step_id",
]
