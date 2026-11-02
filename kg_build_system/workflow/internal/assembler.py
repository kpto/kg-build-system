"""Assembling contributed steps into a workflow definition.

A contribution says what its steps take and give out; it never says who feeds
them. The assembler works the connections out in two passes. First it makes every
connection that holds of any valid wiring — an input with a single legal writer,
an output with a single legal reader — and repeats until none is left. Then it
goes through the inputs in rank order and makes the first connection its rules
justify, starting over after each one, because a new connection can settle what
was still open elsewhere.

Rank decides one thing: which writer a reader takes. It never gates a step and
never refuses a connection.

The module is split into four kinds of value: the expansion turns declarations
into typed ports, the ranking orders them, the rules decide connections, and the
definition reads the finished wiring back in contribution order.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from .._private.identity import (
    expanded_input_name,
    input_name,
    opening_identity,
    output_name,
    step_identity,
    step_name,
)
from .models import (
    ArtifactType,
    Connection,
    DefinedContribution,
    DefinedStep,
    Input,
    Output,
    Publication,
    TakenInput,
    WorkflowContribution,
    WorkflowDefinition,
    WorkflowStep,
    type_matches,
)


class AssemblyError(ValueError):
    """The contributed steps have no wiring that feeds every input and reads every output."""


@dataclass(frozen=True, slots=True)
class _DeclaredStep:
    """Internal implementation of DeclaredStep."""
    identity: str
    step: WorkflowStep


@dataclass(frozen=True, slots=True)
class _OutputPort:
    """Internal implementation of OutputPort."""
    sequence: int
    step_id: str
    name: str
    type: ArtifactType
    rank: int
    must_read: bool

    def __str__(self) -> str:
        """Return the readable form."""
        return f"{self.step_id}.{self.name}"


@dataclass(frozen=True, slots=True)
class _InputPort:
    """Internal implementation of InputPort."""
    sequence: int
    step_id: str
    name: str
    input_name: str
    type: ArtifactType
    rank: int

    def __str__(self) -> str:
        """Return the readable form."""
        return f"{self.step_id}.{self.name}"


@dataclass(frozen=True, slots=True)
class _Expansion:
    """Everything the rules may read about the declaration, fixed once expanded."""

    contributions: tuple[tuple[str, WorkflowContribution, tuple[str, ...]], ...]
    outputs: tuple[_OutputPort, ...]
    inputs: tuple[_InputPort, ...]
    scan_order: tuple[_InputPort, ...]
    inputs_of_step: dict[str, tuple[_InputPort, ...]]
    outputs_of_step: dict[str, tuple[_OutputPort, ...]]
    outputs_of_type: dict[ArtifactType, tuple[_OutputPort, ...]]
    readers_of_type: dict[ArtifactType, tuple[_InputPort, ...]]

    def candidates(self, port: _InputPort) -> tuple[_OutputPort, ...]:
        """The outputs this port could take, whatever has been wired."""
        return tuple(
            output for output in self.outputs_of_type.get(port.type, ())
            if output.step_id != port.step_id
        )


class _TakesType(Enum):
    """Whether a step's dependency takes a type, with room for "cannot tell yet"."""

    YES = "yes"
    NO = "no"
    UNSETTLED = "unsettled"


class _Role(Enum):
    """What the step writing an output does to the type it writes.

    An ``ENDOFUNCTOR`` takes the very type it writes, so it hands on a result of
    it; a ``PRODUCER`` writes the type without taking it; ``UNKNOWN`` means the
    walk up the dependency stopped somewhere still open.
    """

    PRODUCER = "producer"
    ENDOFUNCTOR = "endofunctor"
    UNKNOWN = "unknown"


class _Wiring:
    """The connections made so far, and the two facts kept beside them."""

    def __init__(self) -> None:
        self._made: list[tuple[_OutputPort, _InputPort]] = []
        self._feeders: dict[_InputPort, _OutputPort] = {}
        self._readers: dict[_OutputPort, list[_InputPort]] = {}
        self._reaches: dict[str, set[str]] = {}
        self._roles: dict[_OutputPort, _Role] = {}

    def connect(self, output: _OutputPort, port: _InputPort) -> None:
        """Record one connection and update the derived reachability."""
        if port in self._feeders:
            raise AssemblyError(f"{port} is already fed by {self._feeders[port]}")
        self._made.append((output, port))
        self._feeders[port] = output
        self._readers.setdefault(output, []).append(port)
        self._extend(output.step_id, port.step_id)
        self._roles.clear()

    def _extend(self, writer: str, reader: str) -> None:
        """Data that reached the writer now reaches the reader and all it reaches."""
        ahead = self._reaches.get(reader, set()) | {reader}
        behind = {writer} | {
            step for step, seen in self._reaches.items() if writer in seen
        }
        for step in behind:
            self._reaches.setdefault(step, set()).update(ahead)

    def feeder(self, port: _InputPort) -> _OutputPort | None:
        """Return the output feeding an input, if any."""
        return self._feeders.get(port)

    def is_fed(self, port: _InputPort) -> bool:
        """Return whether an input has a feeder."""
        return port in self._feeders

    def is_read(self, output: _OutputPort) -> bool:
        """Return whether an output has a reader."""
        return bool(self._readers.get(output))

    def closes_cycle(self, writer: str, reader: str) -> bool:
        """Would this connection complete a round trip?"""
        return writer == reader or writer in self._reaches.get(reader, set())

    def cached_role(self, output: _OutputPort) -> _Role | None:
        """Return the cached role of an output, if any."""
        return self._roles.get(output)

    def remember_role(self, output: _OutputPort, role: _Role) -> None:
        """Cache what one output's step does to its type."""
        self._roles[output] = role

    def snapshot(self) -> tuple[tuple[_OutputPort, _InputPort], ...]:
        """Return the connections made so far in order."""
        return tuple(self._made)


def _is_pattern(artifact_type: ArtifactType) -> bool:
    """Internal helper for is pattern."""
    return "*" in artifact_type.namespace or "*" in artifact_type.name


def _matched_types(
    declared: Input, available: Sequence[ArtifactType],
) -> tuple[ArtifactType, ...]:
    """The types one declared input is answered with.

    A pattern is answered with each type it finds in the build, and may find
    none. A name without a pattern is answered with the one type it names
    whether or not anything writes it, so a type nobody produces is reported
    rather than quietly dropped.
    """
    if not _is_pattern(declared.type):
        return (declared.type,)
    return tuple(
        artifact_type for artifact_type in available
        if type_matches(declared.type, artifact_type)
    )


def _validate_modules(contributions: Sequence[WorkflowContribution]) -> None:
    """Internal helper for validate modules."""
    module_ids = {
        contribution.module.reference.module_id for contribution in contributions
    }
    if len(module_ids) != len(contributions):
        raise AssemblyError("workflow module IDs must be unique")


def _declare_steps(
    contributions: Sequence[WorkflowContribution],
) -> tuple[tuple[_DeclaredStep, ...], dict[str, tuple[str, ...]]]:
    """Give every step its module-local name and whole-workflow identity once."""
    declared: list[_DeclaredStep] = []
    names_by_module: dict[str, tuple[str, ...]] = {}
    for contribution in contributions:
        module_id = contribution.module.reference.module_id
        names: list[str] = []
        seen: set[str] = set()
        for position, step in enumerate(contribution.steps):
            name = step_name(step, position)
            if name in seen:
                raise AssemblyError(
                    f"module {module_id!r} declares step {name!r} twice"
                )
            seen.add(name)
            names.append(name)
            declared.append(_DeclaredStep(step_identity(module_id, name), step))
        names_by_module[module_id] = tuple(names)
    return tuple(declared), names_by_module


def _build_outputs(
    declared: Sequence[_DeclaredStep], ranks: dict[str, int],
) -> tuple[
    tuple[_OutputPort, ...],
    dict[str, tuple[_OutputPort, ...]],
    tuple[ArtifactType, ...],
]:
    """Turn every declared output or publication into one concrete port."""
    outputs: list[_OutputPort] = []
    outputs_of_step: dict[str, list[_OutputPort]] = {}
    available: list[ArtifactType] = []
    for item in declared:
        names: set[str] = set()
        for given in item.step.outputs:
            name = output_name(given)
            if name in names:
                raise AssemblyError(f"step {item.identity} gives out {name!r} twice")
            if _is_pattern(given.type):
                raise AssemblyError(
                    f"step {item.identity} gives out {name!r} as a pattern; a value "
                    "given out is one type, only a value taken may be a question"
                )
            names.add(name)
            port = _OutputPort(
                sequence=len(outputs),
                step_id=item.identity,
                name=name,
                type=given.type,
                rank=ranks[item.identity],
                must_read=isinstance(given, Output),
            )
            outputs.append(port)
            outputs_of_step.setdefault(item.identity, []).append(port)
            if given.type not in available:
                available.append(given.type)
    return (
        tuple(outputs),
        {key: tuple(value) for key, value in outputs_of_step.items()},
        tuple(available),
    )


def _build_inputs(
    declared: Sequence[_DeclaredStep],
    ranks: dict[str, int],
    available: Sequence[ArtifactType],
    sequence_offset: int,
) -> tuple[tuple[_InputPort, ...], dict[str, tuple[_InputPort, ...]]]:
    """Expand every declared input into one port per type it is answered with."""
    inputs: list[_InputPort] = []
    inputs_of_step: dict[str, list[_InputPort]] = {}
    for item in declared:
        names: set[str] = set()
        for declared_input in item.step.inputs:
            taken = input_name(declared_input)
            open_input = _is_pattern(declared_input.type)
            for artifact_type in _matched_types(declared_input, available):
                name = (
                    expanded_input_name(taken, artifact_type)
                    if open_input else taken
                )
                if name in names:
                    raise AssemblyError(
                        f"step {item.identity} takes {name!r} twice; a step names "
                        "each opening it takes once"
                    )
                names.add(name)
                port = _InputPort(
                    sequence=sequence_offset + len(inputs),
                    step_id=item.identity,
                    name=name,
                    input_name=taken,
                    type=artifact_type,
                    rank=ranks[item.identity],
                )
                inputs.append(port)
                inputs_of_step.setdefault(item.identity, []).append(port)
    return (
        tuple(inputs),
        {key: tuple(value) for key, value in inputs_of_step.items()},
    )


def _index_ports(
    outputs: Sequence[_OutputPort], ports: Sequence[_InputPort],
) -> tuple[
    dict[ArtifactType, tuple[_OutputPort, ...]],
    dict[ArtifactType, tuple[_InputPort, ...]],
    tuple[_InputPort, ...],
]:
    """Internal helper for index ports."""
    by_output_type: dict[ArtifactType, list[_OutputPort]] = {}
    for output in outputs:
        by_output_type.setdefault(output.type, []).append(output)
    by_input_type: dict[ArtifactType, list[_InputPort]] = {}
    for port in ports:
        by_input_type.setdefault(port.type, []).append(port)
    scan_order = tuple(sorted(ports, key=lambda port: (-port.rank, port.sequence)))
    return (
        {key: tuple(value) for key, value in by_output_type.items()},
        {key: tuple(value) for key, value in by_input_type.items()},
        scan_order,
    )


def expand(contributions: Sequence[WorkflowContribution]) -> _Expansion:
    """Turn every declared opening into a numbered port, and refuse a muddled declaration."""
    _validate_modules(contributions)
    declared, names_by_module = _declare_steps(contributions)
    ranks = derive_ranks(contributions)
    outputs, outputs_of_step, available = _build_outputs(declared, ranks)
    inputs, inputs_of_step = _build_inputs(
        declared, ranks, available, sequence_offset=len(outputs),
    )
    outputs_of_type, readers_of_type, scan_order = _index_ports(outputs, inputs)
    groups = tuple(
        (
            contribution.module.reference.module_id,
            contribution,
            names_by_module[contribution.module.reference.module_id],
        )
        for contribution in contributions
    )
    return _Expansion(
        contributions=groups,
        outputs=outputs,
        inputs=inputs,
        scan_order=scan_order,
        inputs_of_step=inputs_of_step,
        outputs_of_step=outputs_of_step,
        outputs_of_type=outputs_of_type,
        readers_of_type=readers_of_type,
    )


def derive_ranks(contributions: Sequence[WorkflowContribution]) -> dict[str, int]:
    """One integer per step, the greater running earlier.

    A module contributed first runs before one contributed later, within a module
    an eager step runs before a deferred one, and last comes the order the module
    contributed its steps in.
    """
    placed: list[tuple[int, int, int, str]] = []
    for module_index, contribution in enumerate(contributions):
        module_id = contribution.module.reference.module_id
        for position, step in enumerate(contribution.steps):
            placed.append((
                module_index,
                0 if step.assembly_preference == "eager" else 1,
                position,
                step_identity(module_id, step_name(step, position)),
            ))
    placed.sort()
    total = len(placed)
    return {
        identity: total - index
        for index, (_, _, _, identity) in enumerate(placed)
    }


def _takes_type(
    expansion: _Expansion,
    wiring: _Wiring,
    step_id: str,
    artifact_type: ArtifactType,
) -> _TakesType:
    """Does this step, or anything ahead of it, take this type?

    Ahead means every step whose output feeds into it, however far back. A
    declared input counts whether or not anything feeds it, so a step that takes
    what it also writes is seen before any connection exists. An input with
    nothing feeding it leaves the answer unsettled.
    """
    pending = [step_id]
    seen: set[str] = set()
    unsettled = False
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        for port in expansion.inputs_of_step.get(current, ()):
            if port.type == artifact_type:
                return _TakesType.YES
            feeder = wiring.feeder(port)
            if feeder is None:
                unsettled = True
            else:
                pending.append(feeder.step_id)
    return _TakesType.UNSETTLED if unsettled else _TakesType.NO


def _role(
    expansion: _Expansion, wiring: _Wiring, output: _OutputPort,
) -> _Role:
    """What the step writing this output does to the type it writes."""
    remembered = wiring.cached_role(output)
    if remembered is not None:
        return remembered
    role = {
        _TakesType.YES: _Role.ENDOFUNCTOR,
        _TakesType.UNSETTLED: _Role.UNKNOWN,
        _TakesType.NO: _Role.PRODUCER,
    }[_takes_type(expansion, wiring, output.step_id, output.type)]
    wiring.remember_role(output, role)
    return role


def _admissible(
    expansion: _Expansion, wiring: _Wiring, port: _InputPort,
) -> tuple[_OutputPort, ...]:
    """The outputs this input may still be fed by, given the wiring so far."""
    return tuple(
        output for output in expansion.candidates(port)
        if not wiring.closes_cycle(output.step_id, port.step_id)
    )


def _open_readers(
    expansion: _Expansion, wiring: _Wiring, output: _OutputPort,
) -> tuple[_InputPort, ...]:
    """The unfed inputs this output could still feed."""
    return tuple(
        port for port in expansion.readers_of_type.get(output.type, ())
        if port.step_id != output.step_id
        and not wiring.is_fed(port)
        and not wiring.closes_cycle(output.step_id, port.step_id)
    )


@dataclass(frozen=True, slots=True)
class _Answer:
    """A connection the rules justify, and the plain reason they justify it."""

    output: _OutputPort
    port: _InputPort
    ground: str


@dataclass(frozen=True, slots=True)
class _Refusal:
    """Why no connection is justified for one input right now."""

    port: _InputPort
    reason: str


def _type_text(port_type: ArtifactType) -> str:
    """Internal helper for type text."""
    return f"{port_type.namespace}/{port_type.name}"


def _conclude(
    expansion: _Expansion, wiring: _Wiring, port: _InputPort,
) -> _Answer | _Refusal:
    """The connection this input justifies, or why there is none.

    Each earlier answer changes what the next one sees, so order matters. An
    output that would loop back is not an option. An output that may still turn
    out to take the type it writes settles nothing until the steps ahead of it
    are known. A step that takes the type it writes hands on the freshest such
    result, the one that ran last before this input. A step that only writes the
    type answers it when nothing else can.
    """
    candidates = expansion.candidates(port)
    asked = _type_text(port.type)
    if not candidates:
        return _Refusal(port, f"{port} takes {asked}, which no other step writes")
    admissible = _admissible(expansion, wiring, port)
    if not admissible:
        rivals = ", ".join(str(output) for output in candidates)
        return _Refusal(
            port, f"{port} would loop back to every writer of {asked}: {rivals}",
        )
    roles = {output: _role(expansion, wiring, output) for output in admissible}
    waiting = ", ".join(
        str(output) for output, role in roles.items() if role is _Role.UNKNOWN
    )
    if waiting:
        return _Refusal(
            port,
            f"{port} waits on whether {waiting} takes or only writes {asked}",
        )
    earlier = sorted(
        (
            output for output, role in roles.items()
            if role is _Role.ENDOFUNCTOR and output.rank > port.rank
        ),
        key=lambda output: (output.rank, output.sequence),
    )
    if earlier:
        return _Answer(earlier[0], port, "the freshest result of this type")
    writers = [output for output, role in roles.items() if role is _Role.PRODUCER]
    if len(writers) > 1:
        rivals = ", ".join(str(output) for output in writers)
        return _Refusal(
            port,
            f"{port} could be fed by {rivals}, which differ by nothing the "
            "declaration states",
        )
    if writers:
        return _Answer(writers[0], port, "the only producer of this type")
    return _Refusal(
        port, f"{port} has no writer of {asked} that runs before it",
    )


def _next_unavoidable(
    expansion: _Expansion, wiring: _Wiring,
) -> _Answer | None:
    """The next connection every valid wiring contains, if there is one."""
    for port in expansion.scan_order:
        if wiring.is_fed(port):
            continue
        writers = _admissible(expansion, wiring, port)
        if len(writers) == 1:
            return _Answer(writers[0], port, "its only writer")
    for output in expansion.outputs:
        if not output.must_read or wiring.is_read(output):
            continue
        readers = _open_readers(expansion, wiring, output)
        if len(readers) == 1:
            return _Answer(output, readers[0], "its only reader")
    return None


def _next_justified(
    expansion: _Expansion, wiring: _Wiring,
) -> _Answer | None:
    """The next connection the rules justify, from the earliest input that has one."""
    for port in expansion.scan_order:
        if wiring.is_fed(port):
            continue
        answer = _conclude(expansion, wiring, port)
        if isinstance(answer, _Answer):
            return answer
    return None


def _complete(expansion: _Expansion, wiring: _Wiring) -> bool:
    """Whether every input is fed and every output that must be read is read."""
    return (
        all(wiring.is_fed(port) for port in expansion.inputs)
        and all(
            wiring.is_read(output)
            for output in expansion.outputs if output.must_read
        )
    )


def _explain(expansion: _Expansion, wiring: _Wiring) -> str:
    """Every reason the wiring stopped short, in the order the rules met them."""
    lines: list[str] = []
    for port in expansion.scan_order:
        if wiring.is_fed(port):
            continue
        answer = _conclude(expansion, wiring, port)
        if isinstance(answer, _Refusal):
            lines.append(answer.reason)
    unread = [
        str(output) for output in expansion.outputs
        if output.must_read and not wiring.is_read(output)
    ]
    if unread:
        lines.append("nothing reads " + ", ".join(unread))
    return "workflow cannot be assembled:\n  " + "\n  ".join(lines)


def assemble_workflow(
    contributions: Sequence[WorkflowContribution],
) -> WorkflowDefinition:
    """Work out the connections the contributed steps imply, and define the workflow.

    Raises :class:`AssemblyError` when the steps have no wiring that feeds every
    input and reads every output, naming each input it could not settle and why.
    """
    expansion = expand(contributions)
    wiring = _Wiring()

    while (forced := _next_unavoidable(expansion, wiring)) is not None:
        wiring.connect(forced.output, forced.port)
    while (justified := _next_justified(expansion, wiring)) is not None:
        wiring.connect(justified.output, justified.port)

    if not _complete(expansion, wiring):
        raise AssemblyError(_explain(expansion, wiring))
    return _define(expansion, wiring)


def _define(
    expansion: _Expansion, wiring: _Wiring,
) -> WorkflowDefinition:
    """Build the definition from the expansion and the wiring, in contribution order."""
    defined: list[DefinedContribution] = []
    for module_id, contribution, names in expansion.contributions:
        steps: list[DefinedStep] = []
        for position, step in enumerate(contribution.steps):
            identity = step_identity(module_id, names[position])
            steps.append(DefinedStep(
                name=names[position],
                inputs=tuple(
                    TakenInput(
                        type=port.type,
                        name=port.name,
                        input_name=port.input_name,
                    )
                    for port in expansion.inputs_of_step.get(identity, ())
                ),
                outputs=tuple(
                    _resolved(given, output_name(given)) for given in step.outputs
                ),
            ))
        defined.append(DefinedContribution(
            module=contribution.module,
            steps=tuple(steps),
            variables=contribution.variables,
        ))
    connections = tuple(
        Connection(
            input_id=opening_identity(port.step_id, port.name),
            output_id=opening_identity(output.step_id, output.name),
        )
        for output, port in wiring.snapshot()
    )
    return WorkflowDefinition(
        contributions=tuple(defined), connections=connections,
    )


def _resolved(given: Output | Publication, name: str) -> Output | Publication:
    """The declared opening with its name settled, so a definition holds no optionals."""
    return given if given.name is not None else type(given)(type=given.type, name=name)


__all__ = ["AssemblyError", "assemble_workflow"]
