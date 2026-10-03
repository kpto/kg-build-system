"""Work out the wiring that a set of step declarations implies.

A library, not a program: it expands declarations into ports and answers one question --
which output port may *legitimately* be connected to which input port?

A :class:`Step` declares what it *needs* and what it *writes*, both name-to-type mappings;
a need is normally one type and a :class:`Dynamic` need spans several, the only way a need
can be open-ended.  Expansion turns these into :class:`Port` objects -- every write an
:class:`OutputPort`, every need one :class:`InputPort` per type it takes -- and after that
the rules speak only of ports, which keeps "what was declared" apart from "what it
implies" in one place.  A step carries a rank, and **a greater rank means the step runs
earlier**.  Rank is the only ordering the rules may use and it refuses nothing: it enters
one rule, to say *which* writer a reader takes -- of the endofunctors over a type, the one
whose result the reader would have freshest in hand -- so the ranking function steers the
assembly and never gates it.

:class:`Declaration` is immutable and :class:`Links` holds the one mutable thing, the
connections made so far, so every rule is a pure function of the two.  :func:`assemble`
runs two phases: first the connections every valid graph must contain, until none is left,
then one forward pass taking the earliest unfilled input that has something legitimate to
connect.  No backtracking, no repair stage -- a connection is either forced or it is what
the rules said at that moment, and nothing later reopens it.

The run is best effort.  The answer it reports is only whether the graph came out
complete; everything else -- which input no rule could settle, and why -- is said in the
record, where each entry names the ground it was written on.  The report hands back the two
halves the rules worked from, the declaration and the final wiring, so a result can be
interrogated with those same rules instead of only read as prose.

The whole of it, end to end::

    expand                one InputPort per type a need takes, one OutputPort per write;
                          a dynamic need is named "need:type"; sequence breaks rank ties

    phase one, repeated   an unfed input with exactly one admissible writer -> connect it
                          an unread output with one admissible unfilled reader -> connect it

    phase two, restarting for each unfed input, earliest step first:
                            admissible = candidates - those that would close a cycle
                            none          -> no writer, ever
                            any unknown   -> conclude nothing
                            endofunctors  -> the one that ran last before the reader
                            producers     -> two or more: indeterminate; one: connect
                            otherwise     -> conclude nothing
                          connect the first input that concludes, then scan again from the
                          top; a scan that concludes nothing ends the run

    is_complete           every input fed and every output read
    outcome               ASSEMBLED or NOT_ASSEMBLED -- explain_stop writes the reasons
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import TypeVar

__all__ = [
    "AssemblyReport", "Category", "Connect", "Decision", "DecisionKind", "Declaration",
    "DeclarationError", "Dynamic", "InputPort", "InputVerdict", "Link", "Links", "NoConnection",
    "Outcome", "OutputPort", "Port", "Ranking", "Step", "TakesType", "admissible_writers",
    "assemble", "dependency_takes_type", "explain_stop", "expand_declaration",
    "is_complete", "legitimate_connection", "next_connection_to_make",
    "next_unavoidable_connection", "output_category", "rank_from", "would_close_cycle",
]

# -- the declaration, and the ports it expands into ----------------------------------


@dataclass(frozen=True)
class Dynamic:
    """A need that spans types rather than naming one.

    ``accepts`` lists the types it will take; empty means every type written anywhere in
    the build.  It is the declaration-level way to say "give me whatever produces this",
    and expansion pays for it by making one port per type, so every rule afterwards can
    stay single-typed.
    """

    accepts: tuple[str, ...] = ()


@dataclass(frozen=True)
class Step:
    """A declared unit of work: what it needs, and what it writes.

    ``needs`` maps a need name to a type or a :class:`Dynamic`; ``writes`` maps a port
    name to the one type it writes.  These are the only two verbs at declaration level,
    and everything else here is a consequence of them.
    """

    step_id: str
    needs: Mapping[str, str | Dynamic]
    writes: Mapping[str, str]


@dataclass(frozen=True)
class Port:
    """One named, typed opening on a step.

    ``sequence`` is where the port came out during expansion, so a tie in rank breaks by
    declaration order rather than by dict or set iteration.  ``rank`` is the owning
    step's rank: rules compare ports by age but always want the step's age, so the port
    carries it.  Ports are equal and hashed by value, so :class:`Links` can index them.
    """

    sequence: int
    step_id: str
    name: str
    port_type: str
    rank: int

    def __str__(self) -> str:
        return f"{self.step_id}.{self.name}"

    @property
    def label(self) -> str:
        """The name with its type on the end, unless the type is already there."""
        suffix = f":{self.port_type}"
        return self.name if self.name.endswith(suffix) else f"{self.name}{suffix}"


@dataclass(frozen=True)
class InputPort(Port):
    """A need, after expansion.

    ``from_dynamic`` says whether expansion grew this port out of a :class:`Dynamic`
    need.  No rule branches on it -- a fed input is fed, whatever its origin -- but a
    reader of a finished graph needs to know which ports were invented, not declared.
    """

    from_dynamic: bool = False


@dataclass(frozen=True)
class OutputPort(Port):
    """A write, after expansion.  Nothing about a write is dynamic."""


@dataclass(frozen=True)
class Link:
    """A connection: one output port feeding one input port."""

    output: OutputPort
    input: InputPort

    def __str__(self) -> str:
        return f"{self.output} -> {self.input}"


Ranking = Callable[[Step], int]
"""A step's age.  **A greater rank means the step runs earlier.**"""


def rank_from(table: Mapping[str, int]) -> Ranking:
    """Build a :data:`Ranking` from a step-id-to-rank table.

    A missing step is a mistake in the caller's table, not something to guess at: rank
    decides which writer is freshest, so inventing one invents a graph.
    """

    def ranking(step: Step) -> int:
        try:
            return table[step.step_id]
        except KeyError as error:
            raise DeclarationError(f"no rank given for step {step.step_id!r}") from error

    return ranking


# -- the fixed words the rules answer in ----------------------------------------------


class Category(Enum):
    """What an output port's step does to the type the port writes.

    ``ENDOFUNCTOR``: the step's dependency takes that very type, so the step consumes what
    it also writes.  ``PRODUCER``: the dependency was examined throughout
    and nothing in it takes the type, so the type enters here.  ``UNKNOWN``: the
    examination stopped at a need with nothing feeding it, so the port may still turn out
    to be either of the above.
    """

    ENDOFUNCTOR = "endofunctor"
    PRODUCER = "producer"
    UNKNOWN = "unknown"


class TakesType(Enum):
    """Three-valued answer to "does this dependency take this type?".

    ``NOT_YET`` is not a hedge between the other two: the walk could not finish, which is
    a different fact from finishing and finding nothing.
    """

    YES = "yes"
    NO = "no"
    NOT_YET = "not yet"


class Outcome(Enum):
    """Whether the declaration produced a complete graph.

    Two answers, because those are the only two the caller can act on.  A graph that came
    out complete is used; one that did not is read about in the record, which carries the
    reasons the enum used to hold.
    """

    ASSEMBLED = "assembled"
    NOT_ASSEMBLED = "not assembled"


class DecisionKind(Enum):
    """The ground a connection was made on, or that a run stopped on."""

    ONLY_POSSIBLE_WRITER = "unavoidable, its only writer"
    ONLY_POSSIBLE_READER = "unavoidable, its only reader"
    FRESHEST_ENDOFUNCTOR = "the endofunctor that ran last before the type was wanted"
    SOLE_PRODUCER = "the only producer of the type"
    STOPPED = "the run stopped"


# -- the immutable half, and the one mutable half -------------------------------------


class DeclarationError(ValueError):
    """The declarations cannot be expanded into ports at all."""


@dataclass(frozen=True)
class Declaration:
    """Everything a run may read: once expanded, never changed.

    ``declared_needs`` holds the grouping the dependency walk needs: per step, per
    *declared* need, the ports that need grew into.  The walk asks two things of a need,
    "does it take this type" and "is anything feeding it", and answers both from those
    ports alone -- expansion made exactly one port per type the need takes.

    The four indexes are those same ports sorted by the questions asked of them, so a
    question about one port costs what its own type or step holds rather than what the whole
    declaration holds.  ``_asked_writers`` and ``_asked_readers`` memoise the two answers a
    run wants thousands of times; both depend on the declaration alone, which is exactly
    what makes the first answer the last one.
    """

    steps: tuple[Step, ...]
    available_types: tuple[str, ...]
    rank_by_step: Mapping[str, int]
    output_ports: tuple[OutputPort, ...]
    input_ports: tuple[InputPort, ...]
    declared_needs: Mapping[str, Mapping[str, tuple[InputPort, ...]]]
    inputs_in_scan_order: tuple[InputPort, ...]
    outputs_by_type: Mapping[str, tuple[OutputPort, ...]]
    inputs_by_type: Mapping[str, tuple[InputPort, ...]]
    outputs_by_step: Mapping[str, tuple[OutputPort, ...]]
    _asked_writers: dict[InputPort, tuple[OutputPort, ...]] = field(
        default_factory=dict, repr=False, compare=False
    )
    _asked_readers: dict[OutputPort, tuple[InputPort, ...]] = field(
        default_factory=dict, repr=False, compare=False
    )

    def needs_of(self, step_id: str) -> Mapping[str, tuple[InputPort, ...]]:
        return self.declared_needs[step_id]

    def outputs_of(self, step_id: str) -> tuple[OutputPort, ...]:
        return self.outputs_by_step.get(step_id, ())

    def candidates_of(self, input_port: InputPort) -> tuple[OutputPort, ...]:
        """The outputs this input could be fed by: same type, different step.

        Blind to the current wiring by design, which is what makes a candidate set stable
        for a whole run: an output stays a candidate after being read, since it may feed
        several inputs, and a fed input has lost nothing -- it is just no longer unfilled.
        """
        asked = self._asked_writers.get(input_port)
        if asked is None:
            asked = tuple(
                p for p in self.outputs_by_type.get(input_port.port_type, ())
                if p.step_id != input_port.step_id
            )
            self._asked_writers[input_port] = asked
        return asked

    def possible_readers_of(self, output_port: OutputPort) -> tuple[InputPort, ...]:
        """The inputs that could read this output -- the same test, same type and another
        step, read from the other end, so it cannot disagree with :meth:`candidates_of`."""
        asked = self._asked_readers.get(output_port)
        if asked is None:
            asked = tuple(
                p for p in self.inputs_by_type.get(output_port.port_type, ())
                if p.step_id != output_port.step_id
            )
            self._asked_readers[output_port] = asked
        return asked


def expand_declaration(steps: Sequence[Step], ranking: Ranking) -> Declaration:
    """Turn declarations into numbered ports.

    Available types are the values of every ``writes``, in first appearance order,
    because that order fixes the order a dynamic need expands into.  Output ports come
    first (step order, then the order inside each step's writes), then input ports (step
    order, then the order inside each step's needs, then available-type order inside a
    dynamic need), one counter across both so ``sequence`` records exactly that order.

    A repeated ``step_id``, and the same port name twice in one direction on one step,
    are refused: every explanation here names a port by those two strings, and the second
    can arise purely from expansion, when a dynamic need invents a name already used.
    """
    rank_by_step: dict[str, int] = {}
    for step in steps:
        if step.step_id in rank_by_step:
            raise DeclarationError(f"step_id {step.step_id!r} is declared twice")
        rank_by_step[step.step_id] = ranking(step)

    available_types = _available_types(steps)
    output_ports: list[OutputPort] = []
    for step in steps:
        _reject_repeated_names(step.writes.keys(), step.step_id, "output")
        for name, port_type in step.writes.items():
            output_ports.append(
                OutputPort(
                    sequence=len(output_ports), step_id=step.step_id, name=name,
                    port_type=port_type, rank=rank_by_step[step.step_id],
                )
            )

    input_ports: list[InputPort] = []
    declared_needs: dict[str, dict[str, tuple[InputPort, ...]]] = {}
    for step in steps:
        # One step's input ports are staged before any is kept, so a step with a name
        # clash is refused instead of contributing half of its needs.
        staged: list[InputPort] = []
        needs: dict[str, tuple[InputPort, ...]] = {}
        for need_name, need in step.needs.items():
            dynamic = isinstance(need, Dynamic)
            rank, start = rank_by_step[step.step_id], len(output_ports) + len(input_ports)
            ports = tuple(
                InputPort(
                    sequence=start + len(staged) + offset, step_id=step.step_id,
                    name=f"{need_name}:{port_type}" if dynamic else need_name,
                    port_type=port_type, rank=rank, from_dynamic=dynamic,
                )
                for offset, port_type in enumerate(_types_taken_by(need, available_types))
            )
            needs[need_name] = ports
            staged.extend(ports)
        _reject_repeated_names((p.name for p in staged), step.step_id, "input")
        declared_needs[step.step_id] = needs
        input_ports.extend(staged)

    outputs, inputs = tuple(output_ports), tuple(input_ports)
    return Declaration(
        steps=tuple(steps), available_types=available_types, rank_by_step=rank_by_step,
        output_ports=outputs, input_ports=inputs, declared_needs=declared_needs,
        inputs_in_scan_order=tuple(sorted(inputs, key=lambda p: (-p.rank, p.sequence))),
        outputs_by_type=_grouped_by(outputs, lambda p: p.port_type),
        inputs_by_type=_grouped_by(inputs, lambda p: p.port_type),
        outputs_by_step=_grouped_by(outputs, lambda p: p.step_id),
    )


P = TypeVar("P", bound=Port)
"""Either kind of port, so one grouping serves both."""


def _grouped_by(ports: Sequence[P], key: Callable[[P], str]) -> dict[str, tuple[P, ...]]:
    """Sort ports under the value they share, each group keeping the order it came out in."""
    groups: dict[str, list[P]] = {}
    for port in ports:
        groups.setdefault(key(port), []).append(port)
    return {name: tuple(group) for name, group in groups.items()}


def _available_types(steps: Sequence[Step]) -> tuple[str, ...]:
    """The types written anywhere, in first appearance order."""
    types: dict[str, None] = {}
    for step in steps:
        for port_type in step.writes.values():
            types.setdefault(port_type, None)
    return tuple(types)


def _types_taken_by(need: str | Dynamic, available_types: tuple[str, ...]) -> tuple[str, ...]:
    """The available types a declared need takes.

    A plain need takes exactly the type it names, whether or not anything writes it:
    needing a type nobody writes is a real complaint the run must be able to report, so
    such a need still gets a port.  A dynamic need takes every available type it accepts,
    in available-type order.
    """
    if isinstance(need, Dynamic):
        return tuple(t for t in available_types if not need.accepts or t in need.accepts)
    return (need,)


def _reject_repeated_names(names: Iterable[str], step_id: str, direction: str) -> None:
    """Refuse a step that ends up with one port name twice in one direction."""
    seen: set[str] = set()
    for name in names:
        if name in seen:
            raise DeclarationError(
                f"step {step_id!r} declares {direction} port {name!r} twice"
            )
        seen.add(name)


class Links:
    """The links made so far -- the only thing a run mutates.

    An input has one feeder and an output any number of readers; both ends are indexed
    because the rules ask from both -- a dependency walk needs the feeder of an input, a
    cycle test the readers of an output.

    Two derived facts are kept beside the links because they are facts *about* the links and
    a run asks them thousands of times.  ``_reachable`` is the closure of "data written by
    this step arrives at that one", extended when a link joins two steps rather than walked
    again from scratch.  ``_categories`` holds the categories worked out for the wiring as it
    stands and is dropped the moment a link is added, since a new feeder can turn a producer
    into an endofunctor.  Both answers would be the same without them: they are caches, and
    every rule reads like a pure function of a declaration and a wiring still.
    """

    def __init__(self) -> None:
        self._made: list[Link] = []
        self._feeders: dict[InputPort, OutputPort] = {}
        self._readers: dict[OutputPort, list[InputPort]] = {}
        self._reachable: dict[str, set[str]] = {}
        self._categories: dict[OutputPort, Category] = {}

    def connect(self, output_port: OutputPort, input_port: InputPort) -> Link:
        """Record that ``output_port`` feeds ``input_port``.

        An input takes one feeder: it asks for one thing, and two writers for one need is
        the ambiguity these rules exist to settle, not something to keep.
        """
        if input_port in self._feeders:
            raise ValueError(f"{input_port} is already fed by {self._feeders[input_port]}")
        link = Link(output=output_port, input=input_port)
        self._made.append(link)
        self._feeders[input_port] = output_port
        self._readers.setdefault(output_port, []).append(input_port)
        self._extend_closure(output_port.step_id, input_port.step_id)
        self._categories.clear()
        return link

    def _extend_closure(self, writer: str, reader: str) -> None:
        """Every step that reached the writer now reaches the reader and all it reaches.

        One new edge adds exactly that rectangle of pairs and no others, so the closure is
        extended in place.  Should the edge close a cycle the rectangle wraps around itself,
        and the closure is rebuilt from the links instead -- which only a hand-built
        :class:`Links` can ask for, since a run filters cycle-closing links out beforehand.
        """
        ahead = self._reachable.get(reader, set()) | {reader}
        if writer in ahead:
            self._rebuild_closure()
            return
        behind = {writer} | {
            step for step, reached in self._reachable.items() if writer in reached
        }
        for step in behind:
            self._reachable.setdefault(step, set()).update(ahead)

    def _rebuild_closure(self) -> None:
        """Work the closure out again from ``_made``, the way an empty one starts."""
        edges: dict[str, set[str]] = {}
        for link in self._made:
            edges.setdefault(link.output.step_id, set()).add(link.input.step_id)
        closure: dict[str, set[str]] = {}
        for writer in edges:
            reached: set[str] = set()
            pending = list(edges[writer])
            while pending:
                step = pending.pop()
                if step not in reached:
                    reached.add(step)
                    pending.extend(edges.get(step, ()))
            closure[writer] = reached
        self._reachable = closure

    def snapshot(self) -> tuple[Link, ...]:
        return tuple(self._made)

    def feeder_of(self, input_port: InputPort) -> OutputPort | None:
        return self._feeders.get(input_port)

    def readers_of(self, output_port: OutputPort) -> tuple[InputPort, ...]:
        return tuple(self._readers.get(output_port, ()))

    def is_fed(self, input_port: InputPort) -> bool:
        return input_port in self._feeders

    def is_read(self, output_port: OutputPort) -> bool:
        return bool(self._readers.get(output_port))

    def data_reaches(self, from_step_id: str, to_step_id: str) -> bool:
        """Can data written by ``from_step_id`` get to ``to_step_id`` as things stand?"""
        return to_step_id in self._reachable.get(from_step_id, ())

    def cached_category(self, output_port: OutputPort) -> Category | None:
        """The category already worked out for this port, if the wiring has not changed."""
        return self._categories.get(output_port)

    def remember_category(self, output_port: OutputPort, category: Category) -> None:
        self._categories[output_port] = category


# -- the central question, and the category that falls out of it ----------------------


def would_close_cycle(
    links: Links, output_port: OutputPort, input_port: InputPort
) -> bool:
    """Would connecting these two ports make a cycle?

    A link sends data from the output's step to the input's step, so it closes a cycle
    exactly when the reader already reaches the writer -- or when the two ports are on one
    step, which is a cycle of one.  It is asked before any preference because a connection
    that cannot be made is not a candidate, and dropping one is how two apparent rivals
    collapse into a single writer.  The answer comes from the closure :class:`Links` keeps,
    so it costs a set lookup however long the chain between the two steps is.
    """
    return output_port.step_id == input_port.step_id or links.data_reaches(
        input_port.step_id, output_port.step_id
    )


def admissible_writers(
    declaration: Declaration, links: Links, input_port: InputPort
) -> tuple[OutputPort, ...]:
    """The outputs this input may still be fed by, given the wiring so far.

    The candidate set with the cycle filter applied.  A connection that would close a
    cycle is never made, so such an output is simply not an option -- a filter, which is
    also how two apparent rivals collapse into the one writer that remains.
    """
    return tuple(
        p for p in declaration.candidates_of(input_port)
        if not would_close_cycle(links, p, input_port)
    )


def dependency_takes_type(
    declaration: Declaration, links: Links, step_id: str, port_type: str
) -> TakesType:
    """Does the dependency of ``step_id`` take ``port_type``?

    A step's dependency is the step itself plus every step chained ahead of it, the chain
    running from each need of a step to whatever feeds that need.  The answers are not
    symmetric:

    * ``YES`` -- some need in the dependency takes ``port_type``.  A need *declared* on a
      visited step counts whether or not anything feeds it, so a step needing what it
      writes is caught before any connection exists and nothing later undoes it.
    * ``NOT_YET`` -- the walk reached a need with nothing feeding it, so what lies ahead
      is unknowable and the walk cannot promise the type goes unconsumed further on.
    * ``NO`` -- the walk finished and found no such need.

    ``YES`` outranks whatever lies above it, because a consumed type stays consumed: found
    means return.  That is the only precedence here, and it keeps the recursion plain.
    """

    def examine(current: str, visited: frozenset[str]) -> TakesType:
        answer = TakesType.NO
        for need_ports in declaration.needs_of(current).values():
            if any(p.port_type == port_type for p in need_ports):
                return TakesType.YES
            feeders = [f for p in need_ports if (f := links.feeder_of(p)) is not None]
            if not feeders:
                answer = TakesType.NOT_YET
                continue
            for feeder in feeders:
                if feeder.step_id not in visited:
                    nested = examine(feeder.step_id, visited | {feeder.step_id})
                    if nested is TakesType.YES:
                        return TakesType.YES
                    if nested is TakesType.NOT_YET:
                        answer = TakesType.NOT_YET
        return answer

    return examine(step_id, frozenset({step_id}))


def output_category(
    declaration: Declaration, links: Links, output_port: OutputPort
) -> Category:
    """What ``output_port``'s step does to the type it writes.  Nothing beyond the
    question above: taking it makes the step an endofunctor over it, a finished walk that
    did not find it means the type starts here, an unfinished walk means we do not know yet.

    The walk is the expensive half of the whole algorithm and the answer belongs to the
    wiring, so it is remembered until the next link arrives.
    """
    remembered = links.cached_category(output_port)
    if remembered is not None:
        return remembered
    answer = dependency_takes_type(
        declaration, links, output_port.step_id, output_port.port_type
    )
    category = {
        TakesType.YES: Category.ENDOFUNCTOR,
        TakesType.NOT_YET: Category.UNKNOWN,
        TakesType.NO: Category.PRODUCER,
    }[answer]
    links.remember_category(output_port, category)
    return category


# -- what one input port may legitimately be fed by -----------------------------------


@dataclass(frozen=True)
class Connect:
    """A connection the rules justify, and the ground they justify it on.

    Both ends are named so an answer is actionable on its own, whether a deduction produced
    it or the ranking did -- the input arrives as the scan's loop variable and would
    otherwise have to be carried alongside.
    """

    input: InputPort
    output: OutputPort
    kind: DecisionKind


@dataclass(frozen=True)
class NoConnection:
    """No connection is justified for this input right now, and why, in plain words.

    One type covers every refusal because the run treats them alike: it moves on and asks
    again later, since a link made elsewhere can turn an unknown candidate into an
    endofunctor or a producer.  A refusal that never resolves -- a type nobody writes, a
    rival that never becomes distinguishable -- simply stays unfilled, and its reason is
    what the record ends up saying.
    """

    why: str


InputVerdict = Connect | NoConnection
"""What the rules concluded about one input port: a connection to make, or why not."""


def legitimate_connection(
    declaration: Declaration, links: Links, input_port: InputPort
) -> InputVerdict:
    """The legitimate connection for one input port, or the reason there is none.

    Five steps, in this order, because each earlier one changes what the later ones see:

    1. Drop every candidate that would close a cycle.  If none is left, or none was ever
       there, this input can never be fed and no complete graph exists.
    2. If anything left is unknown, conclude nothing.
    3. Otherwise, if a candidate is an endofunctor over the type that ran before this input,
       take the one that ran last: of the results this input could have in hand, that is the
       freshest.
    4. Otherwise the producers qualify.  Two or more cannot be told apart, so the
       declaration is indeterminate; exactly one is the answer.
    5. Otherwise there is nothing legitimate to connect yet.

    Rank appears only in step 3, only to say *which* of the available writers is chosen, and
    nothing here stops on account of a rank: an endofunctor that ran after its reader simply
    is not that reader's freshest result, and the rule moves on to the producers.  Every
    refusal names the step it stopped at, since the record is the only place a reader learns
    why a graph came out incomplete.
    """
    candidates = declaration.candidates_of(input_port)
    if not candidates:
        return NoConnection(
            f"{input_port} takes {input_port.port_type}, which no other step writes"
        )

    admissible = admissible_writers(declaration, links, input_port)
    if not admissible:
        return NoConnection(
            f"{input_port} would close a cycle with every writer of "
            f"{input_port.port_type}: {_names(candidates)}"
        )

    categories = {p: output_category(declaration, links, p) for p in admissible}
    unknown = tuple(p for p, c in categories.items() if c is Category.UNKNOWN)
    if unknown:
        return NoConnection(
            f"{input_port} waits on whether {_names(unknown)} is an endofunctor over "
            f"or a producer of {input_port.port_type}"
        )

    freshest = sorted(
        (p for p, c in categories.items()
         if c is Category.ENDOFUNCTOR and p.rank > input_port.rank),
        key=lambda p: (p.rank, p.sequence),
    )
    if freshest:
        return Connect(
            input=input_port, output=freshest[0],
            kind=DecisionKind.FRESHEST_ENDOFUNCTOR,
        )

    producers = tuple(p for p, c in categories.items() if c is Category.PRODUCER)
    if len(producers) > 1:
        return NoConnection(
            f"{input_port} could be fed by {_names(producers)}, which are producers of "
            f"{input_port.port_type} and differ by nothing in the declaration"
        )
    if producers:
        return Connect(
            input=input_port, output=producers[0], kind=DecisionKind.SOLE_PRODUCER
        )
    return NoConnection(
        f"{input_port} has no writer that is both an endofunctor over "
        f"{input_port.port_type} and earlier than it"
    )


# -- what the run asks of the rules ---------------------------------------------------


def next_unavoidable_connection(
    declaration: Declaration, links: Links
) -> Connect | None:
    """What must be connected next regardless of preference, if anything.

    Two deductions hold of every valid graph: an input with exactly one admissible writer
    has to be fed by it, and an output with no reader that exactly one still-open input can
    admissibly read has to reach that input, because every output must be read by
    something.  Both count *admissible* options, so a deduction can never propose a link
    that would close a cycle -- the filter has already removed it, and a port left with
    nothing to connect is a reason for the record, an error to raise.  A run asks this,
    applies the answer and asks again, so each answer is true of the wiring at the moment
    it is used.

    Only the first answer comes back -- writers before readers, inputs earliest step
    first, outputs in declaration order.  One at a time keeps the second deduction honest:
    committing an input removes it from the open readers of the next output, which a batch
    would hide.
    """
    for input_port in declaration.inputs_in_scan_order:
        if not links.is_fed(input_port):
            writers = admissible_writers(declaration, links, input_port)
            if len(writers) == 1:
                return Connect(input_port, writers[0], DecisionKind.ONLY_POSSIBLE_WRITER)

    for output_port in declaration.output_ports:
        if not links.is_read(output_port):
            readers = tuple(
                p for p in declaration.possible_readers_of(output_port)
                if not links.is_fed(p)
                and not would_close_cycle(links, output_port, p)
            )
            if len(readers) == 1:
                return Connect(readers[0], output_port, DecisionKind.ONLY_POSSIBLE_READER)

    return None


def next_connection_to_make(declaration: Declaration, links: Links) -> Connect | None:
    """The next connection the rules justify, taken from the earliest input that has one.

    Unfilled inputs are scanned earliest step first and any without a connection is passed
    over, because one new link can resolve another input's unknown while a reason that
    never resolves leaves its input for the record to explain.  The scan runs from the top
    after every connection, which is what "earliest unfilled input" means at each moment.
    """
    for input_port in declaration.inputs_in_scan_order:
        if not links.is_fed(input_port):
            verdict = legitimate_connection(declaration, links, input_port)
            if isinstance(verdict, Connect):
                return verdict
    return None


def is_complete(declaration: Declaration, links: Links) -> bool:
    """Does the wiring satisfy everything a graph has to satisfy?

    Two conditions are already guaranteed by the way links get made -- a connection never
    closes a cycle and never joins a step to itself -- so the two a run can still fall
    short of are these: every input fed, every output read.
    """
    return all(links.is_fed(p) for p in declaration.input_ports) and all(
        links.is_read(p) for p in declaration.output_ports
    )


def explain_stop(declaration: Declaration, links: Links) -> str:
    """Why the run went no further, read off the rules one final time.

    Nothing has changed since the scan that found no connection to make, so asking again
    returns what each unfilled input said then, in scan order, with any output nobody reads
    named last.  This is where the whole vocabulary of failure lives, because the outcome
    itself only answers yes or no.
    """
    reasons: list[str] = []
    for input_port in declaration.inputs_in_scan_order:
        if not links.is_fed(input_port):
            verdict = legitimate_connection(declaration, links, input_port)
            if isinstance(verdict, NoConnection):
                reasons.append(verdict.why)
    unread = tuple(p for p in declaration.output_ports if not links.is_read(p))
    if unread:
        reasons.append(f"nothing reads {_names(unread)}")
    return "\n".join(reasons)


def _names(ports: Sequence[Port]) -> str:
    """A readable list of ports for an explanation."""
    return ", ".join(f"{port} ({port.label})" for port in ports)


# -- the report, and the run that produces it -----------------------------------------


@dataclass(frozen=True)
class Decision:
    """One line of the record: a connection made on a stated ground, or the closing note.

    The graph is the answer; the record is how it was arrived at, in order, ending with
    whatever the rules had to say about the ports they left alone.
    """

    kind: DecisionKind
    subject: str
    link: Link | None = None

    def __str__(self) -> str:
        return f"{self.kind.value}: {self.subject}"


@dataclass(frozen=True)
class AssemblyReport:
    """The state a run ended in, plus the record of how it got there.

    The declaration and the wiring travel with the answer so a result is debuggable rather
    than merely readable: with those two, the same queries the rules used can be asked of a
    finished run -- which inputs are unfed, which outputs unread, what the admissible
    writers and the categories of a refusal were -- and :func:`explain_stop` can be
    recomputed and cross-checked against the closing entry of ``decisions``.  ``wiring`` is
    the run's final state; treat it as read-only, since the record is the history.

    ``links`` is the graph in the order the connections were made, which is also proof that
    nothing was revisited: each link appears once, under one ground.
    """

    outcome: Outcome
    declaration: Declaration
    wiring: Links
    decisions: tuple[Decision, ...]

    @property
    def links(self) -> tuple[Link, ...]:
        return self.wiring.snapshot()


def assemble(steps: Sequence[Step], ranking: Ranking) -> AssemblyReport:
    """Work out the connections a declaration implies, as far as they can be worked out.

    Two phases, and their order is not cosmetic.  The unavoidable connections come first
    because they hold of every valid graph, so no preference has anything to say about them
    even when the input they settle had several candidates; deferring them would let a
    preference commit an input that was never in doubt.  Only once no deduction is left does
    the forward pass weigh rank, and its scan starts over from the top after each connection
    because that connection can resolve an unknown candidate for every other input.

    Each phase stops when it can go no further, and a refusal is never an error: the run
    goes on wiring whatever it can and reports only whether the graph came out whole.  The
    record is kept here, locally -- the rules are pure queries, so the only thing threaded
    through the loop is the loop's own notebook.
    """
    declaration = expand_declaration(steps, ranking)
    links = Links()
    decisions: list[Decision] = []

    def record(made: Connect) -> None:
        link = links.connect(made.output, made.input)
        decisions.append(Decision(kind=made.kind, subject=str(link), link=link))

    def report(outcome: Outcome) -> AssemblyReport:
        return AssemblyReport(
            outcome=outcome, declaration=declaration, wiring=links,
            decisions=tuple(decisions),
        )

    while (forced := next_unavoidable_connection(declaration, links)) is not None:
        record(forced)

    while (justified := next_connection_to_make(declaration, links)) is not None:
        record(justified)

    if is_complete(declaration, links):
        return report(Outcome.ASSEMBLED)

    decisions.append(
        Decision(kind=DecisionKind.STOPPED, subject=explain_stop(declaration, links))
    )
    return report(Outcome.NOT_ASSEMBLED)
