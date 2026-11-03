"""Assemble contributed steps into the shared workflow contract.

Compilation owns the assembly algorithm: contributions are ranked by
contribution order, eager before deferred, then declaration order; open inputs
expand to one opening per matching type; publications stay addressable; and a
wiring that closes a cycle is refused. No step, opening or connection is read
from a module's private data.

An instruction is copied from the declared step to the assembled step
unchanged. The assembler never reads its kind or payload.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from fnmatch import fnmatchcase

from pydantic import JsonValue

from .....contract.model.public.dto.contract import (
    ArtifactTypeDTO,
    ConnectionDTO,
    ContributionDTO,
    GivenDTO,
    InputDTO,
    OutputDTO,
    PublicationDTO,
    StepDTO,
    WorkflowContractDTO,
)

DEFAULT_STEP_NAME = "step"
DEFAULT_INPUT_NAME = "input"
DEFAULT_OUTPUT_NAME = "output"


class AssemblyError(ValueError):
    """The contributed steps have no wiring that feeds every input and reads every output."""


def _step_name(step: StepDTO, position: int) -> str:
    return step.name if step.name else f"{DEFAULT_STEP_NAME}{position + 1}"


def _output_name(given: GivenDTO) -> str:
    return given.name if given.name is not None else DEFAULT_OUTPUT_NAME


def _type_text(value: ArtifactTypeDTO) -> str:
    return f"{value.namespace}.{value.name}"


def _expanded_input_name(
    declared_name: str, taken_type: ArtifactTypeDTO,
) -> str:
    return f"{declared_name}:{_type_text(taken_type)}"


def _step_identity(module_id: str, name: str) -> str:
    return f"{module_id}::{name}"


def _opening_identity(identity: str, name: str) -> str:
    return f"{identity}.{name}"


@dataclass(frozen=True, slots=True)
class _DeclaredStep:
    identity: str
    step: StepDTO


@dataclass(frozen=True, slots=True)
class _OutputPort:
    sequence: int
    step_id: str
    name: str
    type: ArtifactTypeDTO
    rank: int
    must_read: bool

    def __str__(self) -> str:
        return f"{self.step_id}.{self.name}"


@dataclass(frozen=True, slots=True)
class _InputPort:
    sequence: int
    step_id: str
    name: str
    input_name: str
    type: ArtifactTypeDTO
    rank: int

    def __str__(self) -> str:
        return f"{self.step_id}.{self.name}"


@dataclass(frozen=True, slots=True)
class _Expansion:
    contributions: tuple[tuple[str, ContributionDTO, tuple[str, ...]], ...]
    outputs: tuple[_OutputPort, ...]
    inputs: tuple[_InputPort, ...]
    scan_order: tuple[_InputPort, ...]
    inputs_of_step: dict[str, tuple[_InputPort, ...]]
    outputs_of_step: dict[str, tuple[_OutputPort, ...]]
    outputs_of_type: dict[ArtifactTypeDTO, tuple[_OutputPort, ...]]
    readers_of_type: dict[ArtifactTypeDTO, tuple[_InputPort, ...]]

    def candidates(self, port: _InputPort) -> tuple[_OutputPort, ...]:
        return tuple(
            output for output in self.outputs_of_type.get(port.type, ())
            if output.step_id != port.step_id
        )


class _TakesType(Enum):
    YES = "yes"
    NO = "no"
    UNSETTLED = "unsettled"


class _Role(Enum):
    PRODUCER = "producer"
    ENDOFUNCTOR = "endofunctor"
    UNKNOWN = "unknown"


class _Wiring:
    def __init__(self) -> None:
        self._made: list[tuple[_OutputPort, _InputPort]] = []
        self._feeders: dict[_InputPort, _OutputPort] = {}
        self._readers: dict[_OutputPort, list[_InputPort]] = {}
        self._reaches: dict[str, set[str]] = {}
        self._roles: dict[_OutputPort, _Role] = {}

    def connect(self, output: _OutputPort, port: _InputPort) -> None:
        if port in self._feeders:
            raise AssemblyError(f"{port} is already fed by {self._feeders[port]}")
        self._made.append((output, port))
        self._feeders[port] = output
        self._readers.setdefault(output, []).append(port)
        self._extend(output.step_id, port.step_id)
        self._roles.clear()

    def _extend(self, writer: str, reader: str) -> None:
        ahead = self._reaches.get(reader, set()) | {reader}
        behind = {writer} | {
            step for step, seen in self._reaches.items() if writer in seen
        }
        for step in behind:
            self._reaches.setdefault(step, set()).update(ahead)

    def feeder(self, port: _InputPort) -> _OutputPort | None:
        return self._feeders.get(port)

    def is_fed(self, port: _InputPort) -> bool:
        return port in self._feeders

    def is_read(self, output: _OutputPort) -> bool:
        return bool(self._readers.get(output))

    def closes_cycle(self, writer: str, reader: str) -> bool:
        return writer == reader or writer in self._reaches.get(reader, set())

    def cached_role(self, output: _OutputPort) -> _Role | None:
        return self._roles.get(output)

    def remember_role(self, output: _OutputPort, role: _Role) -> None:
        self._roles[output] = role

    def snapshot(self) -> tuple[tuple[_OutputPort, _InputPort], ...]:
        return tuple(self._made)


def _is_pattern(artifact_type: ArtifactTypeDTO) -> bool:
    return "*" in artifact_type.namespace or "*" in artifact_type.name


def _type_matches(declared: ArtifactTypeDTO, actual: ArtifactTypeDTO) -> bool:
    return (
        fnmatchcase(actual.namespace, declared.namespace)
        and fnmatchcase(actual.name, declared.name)
    )


def _matched_types(
    declared: ArtifactTypeDTO, available: Sequence[ArtifactTypeDTO],
) -> tuple[ArtifactTypeDTO, ...]:
    if not _is_pattern(declared):
        return (declared,)
    return tuple(
        artifact_type for artifact_type in available
        if _type_matches(declared, artifact_type)
    )


def _validate_modules(contributions: Sequence[ContributionDTO]) -> None:
    module_ids = {
        contribution.module.reference.module_id for contribution in contributions
    }
    if len(module_ids) != len(contributions):
        raise AssemblyError("workflow module IDs must be unique")


def _declare_steps(
    contributions: Sequence[ContributionDTO],
) -> tuple[tuple[_DeclaredStep, ...], dict[str, tuple[str, ...]]]:
    declared: list[_DeclaredStep] = []
    names_by_module: dict[str, tuple[str, ...]] = {}
    for contribution in contributions:
        module_id = contribution.module.reference.module_id
        names: list[str] = []
        seen: set[str] = set()
        for position, step in enumerate(contribution.steps):
            name = _step_name(step, position)
            if name in seen:
                raise AssemblyError(
                    f"module {module_id!r} declares step {name!r} twice"
                )
            seen.add(name)
            names.append(name)
            declared.append(_DeclaredStep(_step_identity(module_id, name), step))
        names_by_module[module_id] = tuple(names)
    return tuple(declared), names_by_module


def _build_outputs(
    declared: Sequence[_DeclaredStep], ranks: dict[str, int],
) -> tuple[
    tuple[_OutputPort, ...],
    dict[str, tuple[_OutputPort, ...]],
    tuple[ArtifactTypeDTO, ...],
]:
    outputs: list[_OutputPort] = []
    outputs_of_step: dict[str, list[_OutputPort]] = {}
    available: list[ArtifactTypeDTO] = []
    for item in declared:
        names: set[str] = set()
        for given in item.step.outputs:
            name = _output_name(given)
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
                must_read=isinstance(given, OutputDTO),
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
    available: Sequence[ArtifactTypeDTO],
    sequence_offset: int,
) -> tuple[tuple[_InputPort, ...], dict[str, tuple[_InputPort, ...]]]:
    inputs: list[_InputPort] = []
    inputs_of_step: dict[str, list[_InputPort]] = {}
    for item in declared:
        names: set[str] = set()
        for declared_input in item.step.inputs:
            taken = declared_input.input_name or DEFAULT_INPUT_NAME
            open_input = _is_pattern(declared_input.type)
            for artifact_type in _matched_types(declared_input.type, available):
                name = (
                    _expanded_input_name(taken, artifact_type)
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
    dict[ArtifactTypeDTO, tuple[_OutputPort, ...]],
    dict[ArtifactTypeDTO, tuple[_InputPort, ...]],
    tuple[_InputPort, ...],
]:
    by_output_type: dict[ArtifactTypeDTO, list[_OutputPort]] = {}
    for output in outputs:
        by_output_type.setdefault(output.type, []).append(output)
    by_input_type: dict[ArtifactTypeDTO, list[_InputPort]] = {}
    for port in ports:
        by_input_type.setdefault(port.type, []).append(port)
    scan_order = tuple(sorted(ports, key=lambda port: (-port.rank, port.sequence)))
    return (
        {key: tuple(value) for key, value in by_output_type.items()},
        {key: tuple(value) for key, value in by_input_type.items()},
        scan_order,
    )


def expand(contributions: Sequence[ContributionDTO]) -> _Expansion:
    """Turn every declared opening into a numbered port."""
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


def derive_ranks(contributions: Sequence[ContributionDTO]) -> dict[str, int]:
    """One integer per step, the greater running earlier."""
    placed: list[tuple[int, int, int, str]] = []
    for module_index, contribution in enumerate(contributions):
        module_id = contribution.module.reference.module_id
        for position, step in enumerate(contribution.steps):
            placed.append((
                module_index,
                0 if step.assembly_preference == "eager" else 1,
                position,
                _step_identity(module_id, _step_name(step, position)),
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
    artifact_type: ArtifactTypeDTO,
) -> _TakesType:
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
    return tuple(
        output for output in expansion.candidates(port)
        if not wiring.closes_cycle(output.step_id, port.step_id)
    )


def _open_readers(
    expansion: _Expansion, wiring: _Wiring, output: _OutputPort,
) -> tuple[_InputPort, ...]:
    return tuple(
        port for port in expansion.readers_of_type.get(output.type, ())
        if port.step_id != output.step_id
        and not wiring.is_fed(port)
        and not wiring.closes_cycle(output.step_id, port.step_id)
    )


@dataclass(frozen=True, slots=True)
class _Answer:
    output: _OutputPort
    port: _InputPort
    ground: str


@dataclass(frozen=True, slots=True)
class _Refusal:
    port: _InputPort
    reason: str


def _conclude(
    expansion: _Expansion, wiring: _Wiring, port: _InputPort,
) -> _Answer | _Refusal:
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
    for port in expansion.scan_order:
        if wiring.is_fed(port):
            continue
        answer = _conclude(expansion, wiring, port)
        if isinstance(answer, _Answer):
            return answer
    return None


def _complete(expansion: _Expansion, wiring: _Wiring) -> bool:
    return (
        all(wiring.is_fed(port) for port in expansion.inputs)
        and all(
            wiring.is_read(output)
            for output in expansion.outputs if output.must_read
        )
    )


def _explain(expansion: _Expansion, wiring: _Wiring) -> str:
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


def _resolved(given: GivenDTO, name: str) -> GivenDTO:
    if isinstance(given, PublicationDTO):
        return PublicationDTO(type=given.type, name=name)
    return OutputDTO(type=given.type, name=name)


def _define(
    expansion: _Expansion, wiring: _Wiring, provenance: JsonValue | None,
) -> WorkflowContractDTO:
    contributions: list[ContributionDTO] = []
    for module_id, contribution, names in expansion.contributions:
        steps: list[StepDTO] = []
        for position, step in enumerate(contribution.steps):
            identity = _step_identity(module_id, names[position])
            steps.append(StepDTO(
                name=names[position],
                inputs=tuple(
                    InputDTO(
                        type=port.type,
                        name=port.name,
                        input_name=port.input_name,
                    )
                    for port in expansion.inputs_of_step.get(identity, ())
                ),
                outputs=tuple(
                    _resolved(given, _output_name(given))
                    for given in step.outputs
                ),
                instruction=step.instruction,
                assembly_preference=step.assembly_preference,
            ))
        contributions.append(ContributionDTO(
            module=contribution.module,
            steps=tuple(steps),
        ))
    connections = tuple(
        ConnectionDTO(
            input_id=_opening_identity(port.step_id, port.name),
            output_id=_opening_identity(output.step_id, output.name),
        )
        for output, port in wiring.snapshot()
    )
    return WorkflowContractDTO(
        contributions=tuple(contributions),
        connections=connections,
        provenance=provenance,
    )


def assemble_contract(
    contributions: Sequence[ContributionDTO],
    provenance: JsonValue | None = None,
) -> WorkflowContractDTO:
    """Assemble declared contributions into a workflow contract.

    Example:
    ```python
    contract = assemble_contract((contribution,))
    assert contract.connections
    ```
    """
    declared = tuple(contributions)
    expansion = expand(declared)
    wiring = _Wiring()
    while (forced := _next_unavoidable(expansion, wiring)) is not None:
        wiring.connect(forced.output, forced.port)
    while (justified := _next_justified(expansion, wiring)) is not None:
        wiring.connect(justified.output, justified.port)
    if not _complete(expansion, wiring):
        raise AssemblyError(_explain(expansion, wiring))
    return _define(expansion, wiring, provenance)


__all__ = ["AssemblyError", "assemble_contract"]
