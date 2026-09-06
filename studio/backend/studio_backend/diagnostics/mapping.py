"""Turn a ``file:line:column`` from pyright into an IR reference the UI can highlight.

Two independent routes, used in the order ``studio/docs/API.md`` documents:

1. **anchors** — ``<project_root>/.kg-studio/anchors.json``, written by the
   generator next to the project, records the line/column range of every rendered
   declaration and expression against the IR ref that produced it. A position
   inside a range resolves to the *innermost* containing range, which is the
   difference between highlighting one property slot and highlighting the whole
   binding around it. A position outside every range falls back to the file's
   whole-file entry (DESIGN.md §3: "a diagnostic with no anchor maps to its file's
   owner ref"), reported as ``ref_trusted == "file"``.
2. **declaration names** — for a problem with no usable anchor, the names a message
   quotes (``"SiteNode" has no attribute "city"``,
   ``… cannot be assigned to parameter "city"``) are matched against the document,
   reported as ``ref_trusted == "name"``.

Name matching refuses to guess twice: an unqualified member name is only used when
no two declarations share it, and the document is the only source of names — so a
name that was deleted from the document stops resolving immediately.

Everything here is read-only over the anchor index and the document, so it can run
on every debounce tick without touching either.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Union

from ..ir import refs
from ..ir.document import AnnotationType, Binding, Component, ProjectDocument, Projection, Struct, Table
from .problem import Problem, make_problem

__all__ = [
    "ANCHORS_RELATIVE_PATH",
    "Anchor",
    "AnchorFormatError",
    "Anchors",
    "NameIndex",
    "annotate",
    "annotate_problems",
    "as_anchors",
    "as_problem",
    "build_name_index",
    "load_anchors",
    "make_hint",
    "ref_description",
    "resolve",
    "resolve_ref_by_name",
]

#: Where the generator keeps the index, relative to the project root.
ANCHORS_RELATIVE_PATH: Final = ".kg-studio/anchors.json"

#: The only anchor version this reader understands.
SUPPORTED_FORMAT_VERSION: Final = 1

#: The entry kind that stands for "the whole file".
FILE_NODE: Final = "file"


class AnchorFormatError(ValueError):
    """An anchors.json this reader cannot trust."""


@dataclass(frozen=True, slots=True)
class Anchor:
    """One rendered range plus the IR ref it came from (1-based, both ends inclusive)."""

    ref: str
    line: int
    end_line: int
    column: int
    end_column: int
    node: str

    def contains(self, line: int, column: int) -> bool:
        """True when the 1-based position falls inside this range."""
        if line < self.line or line > self.end_line:
            return False
        if line == self.line and column < self.column:
            return False
        if line == self.end_line and column > self.end_column:
            return False
        return True

    @property
    def span(self) -> tuple[int, int]:
        """Sort key that prefers the tightest range: fewer lines, then fewer columns."""
        return (self.end_line - self.line, self.end_column - self.column)


@dataclass(frozen=True, slots=True)
class Anchors:
    """The whole index, keyed by project-relative POSIX path."""

    format_version: int
    revision: int
    document_fingerprint: str
    files: dict[str, tuple[Anchor, ...]]

    @property
    def file_count(self) -> int:
        return len(self.files)

    def entries(self, file: str | None) -> tuple[Anchor, ...]:
        return () if file is None else self.files.get(file, ())

    def owner(self, file: str | None) -> Anchor | None:
        """The whole-file entry, whose ref is the file's owner in the document."""
        for anchor in self.entries(file):
            if anchor.node == FILE_NODE:
                return anchor
        return None


def load_anchors(path: Path | str) -> Anchors:
    """Read an anchor index.

    Raises :class:`AnchorFormatError` rather than returning a partial index:
    resolving against a truncated one would silently mislabel diagnostics as
    belonging to the wrong component. A missing file is an error too — deciding that
    it means "generation has not run yet" belongs to the caller.
    """
    index_path = Path(path)
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise AnchorFormatError(f"no anchor index at {index_path}") from error
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise AnchorFormatError(f"{index_path} is not readable JSON: {error}") from error
    return parse_anchor_payload(payload, index_path)


def parse_anchor_payload(payload: Any, source: Path | str = "anchors.json") -> Anchors:
    """Validate an already-parsed anchor index.

    Split out from :func:`load_anchors` because the workspace keeps the index in its
    own store and may hand the decoded object straight over.
    """
    origin = Path(source)
    if not isinstance(payload, dict):
        raise AnchorFormatError(f"{origin} does not contain an object")
    version = payload.get("format_version")
    if version != SUPPORTED_FORMAT_VERSION:
        raise AnchorFormatError(
            f"{origin} declares format_version {version!r}; this reader supports "
            f"{SUPPORTED_FORMAT_VERSION!r}"
        )
    files = payload.get("files")
    if not isinstance(files, dict):
        raise AnchorFormatError(f"{origin} has no 'files' object")
    return Anchors(
        format_version=SUPPORTED_FORMAT_VERSION,
        revision=_integer(payload.get("revision"), "revision", origin),
        document_fingerprint=str(payload.get("document_fingerprint") or ""),
        files={name: _entries(value, name, origin) for name, value in files.items()},
    )


def as_anchors(value: Anchors | Mapping[str, Any] | None) -> Anchors | None:
    """An :class:`Anchors` index, from an index or from a decoded anchors.json."""
    if value is None or isinstance(value, Anchors):
        return value
    return parse_anchor_payload(value)


def _integer(value: Any, field_name: str, source: Path) -> int:
    if not isinstance(value, int):
        raise AnchorFormatError(f"{source}: {field_name!r} must be an integer")
    return value


def _entries(value: Any, file_name: str, source: Path) -> tuple[Anchor, ...]:
    if not isinstance(value, list):
        raise AnchorFormatError(f"{source}: files[{file_name!r}] must be a list")
    entries: list[Anchor] = []
    for item in value:
        if not isinstance(item, dict):
            raise AnchorFormatError(f"{source}: files[{file_name!r}] holds a non-object entry")
        missing = {"ref", "line", "end_line", "column", "end_column", "node"} - set(item)
        if missing:
            raise AnchorFormatError(
                f"{source}: files[{file_name!r}] entry for {item.get('ref')!r} lacks {sorted(missing)}"
            )
        entries.append(
            Anchor(
                ref=str(item["ref"]),
                line=int(item["line"]),
                end_line=int(item["end_line"]),
                column=int(item["column"]),
                end_column=int(item["end_column"]),
                node=str(item["node"]),
            )
        )
    # Lookups scan this list, so sorting innermost-first makes "first hit wins" the
    # same thing as "tightest hit" without a second pass.
    entries.sort(key=lambda anchor: (anchor.span, anchor.ref))
    return tuple(entries)


def resolve(anchors: Anchors, file: str | None, line: int | None, column: int | None) -> tuple[str | None, str | None]:
    """Resolve a 1-based position to ``(ref, trusted)``.

    ``(ref, "anchor")`` when a real range contains the position — the innermost one
    wins — and ``(owner, "file")`` when only the whole-file entry is available,
    which covers both a position outside every range and a file whose index holds
    nothing but its owner entry. ``(None, None)`` means the file is not in the index
    at all, and the UI must render that problem ungrouped.
    """
    entries = anchors.entries(file)
    if not entries:
        return (None, None)
    if line is not None and column is not None:
        for anchor in entries:
            if anchor.node != FILE_NODE and anchor.contains(line, column):
                return (anchor.ref, "anchor")
    owner = anchors.owner(file)
    if owner is None:
        return (None, None)
    return (owner.ref, "file")


# ------------------------------------------------------------------- by name

#: A quoted name. Both quote styles, because pyright writes ``"SiteNode"`` and the
#: framework writes ``'site_binding'``. The whole quoted span must be one
#: identifier: ``"kg_project.topology.site"`` is a module path, and splitting it into
#: words would resolve an import error to the component called ``site``.
_QUOTED: Final = re.compile(r"[\"']([A-Za-z_][A-Za-z0-9_]{0,119})[\"']")
_DOTTED: Final = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\b")
_WORD: Final = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
#: A bare word worth treating as a declaration name: pyright writes class names
#: unquoted (``for class SiteNode``) and quotes everything else. Requiring the
#: leading capital is what stops a module path in an import message —
#: ``kg_project.topology.site`` — from resolving to the component ``site``.
_CLASS_WORD: Final = re.compile(r"\b[A-Z][A-Za-z0-9_]*\b")

#: The declarations that own a named list of members, and so can be addressed by
#: ``<declaration name>.<member>`` in error text.
_Record = Union[Struct, Table, Projection, Component, AnnotationType]


@dataclass(frozen=True, slots=True)
class NameIndex:
    """Declaration names and their named parts, read off the document.

    ``members`` is keyed by every alias a declaration answers to — a table answers
    to both ``SitesTable`` and its logical name ``sites`` — so a message can be
    matched whichever spelling the framework used. A member entry points at the most
    editable ref available: for a component property that is the *binding* filling it
    whenever a binding fills it, since that is the generated code pyright was
    complaining about, and the slot's own declaration otherwise.
    """

    declarations: dict[str, str]
    members: dict[str, dict[str, str]]
    #: Member names shared by more than one declaration, excluded from the
    #: unqualified-match step.
    ambiguous_members: frozenset[str]

    @classmethod
    def empty(cls) -> NameIndex:
        return cls(declarations={}, members={}, ambiguous_members=frozenset())

    def ref_for(self, name: str) -> str | None:
        return self.declarations.get(name)

    def member_ref(self, declaration: str, member: str) -> str | None:
        return self.members.get(declaration, {}).get(member)

    def unique_member_ref(self, member: str) -> str | None:
        """The ref of ``member`` when exactly one declaration names it."""
        if member in self.ambiguous_members:
            return None
        for parts in self.members.values():
            ref = parts.get(member)
            if ref is not None:
                return ref
        return None


def build_name_index(document: ProjectDocument) -> NameIndex:
    """Index every name pyright's and the framework's error text can mention."""
    index = _IndexBuilder()

    for struct in document.structs:
        index.record(struct, "struct", "fields")
    for table in document.tables:
        index.record(table, "table", "fields")
    for projection in document.projections:
        index.record(projection, "projection", "fields")
    for annotation_type in document.annotation_types:
        index.record(annotation_type, "annotation_type", "fields")
    for component in document.components:
        index.record(component, "component", "properties")
    index.apply_component_inheritance(document)

    # A binding's generated symbol is its id, and its property arguments are where a
    # slot value is actually written, so they take over the target's member entries.
    for binding in document.bindings:
        index.record_binding(binding, document)

    for source in document.sources:
        index.declare(source.id, refs.build("source", source.id))
    for module in document.modules:
        index.declare(module.id, refs.build("module", module.id))

    return index.finish()


class _IndexBuilder:
    """Mutable accumulator behind :func:`build_name_index`."""

    def __init__(self) -> None:
        self._declarations: dict[str, str] = {}
        # Canonical ref text -> member name -> member ref. Aliasing on top of this in
        # :meth:`finish` keeps the ambiguity count per declaration, not per alias.
        self._members: dict[str, dict[str, str]] = {}

    def declare(self, name: str, ref: str) -> None:
        self._declarations.setdefault(name, ref)

    def record(self, item: _Record, kind: refs.RefKind, member_attr: str) -> None:
        reference = refs.Reference(kind, item.id)
        self.declare(item.declaration_name, str(reference))
        part = "property" if kind == "component" else "field"
        members: dict[str, str] = {}
        for member_item in getattr(item, member_attr):
            members[member_item.name] = str(reference.child(part, member_item.name))
        self._members[str(reference)] = members
        logical = getattr(item, "name", None)
        if isinstance(logical, str) and logical and logical != item.declaration_name:
            self.declare(logical, str(reference))

    def apply_component_inheritance(self, document: ProjectDocument) -> None:
        """Give a component the member entries of the slots it inherits.

        The generated properties dataclass carries one field per *effective* slot
        (own + inherited), so an error naming ``SiteNode.summary`` is real even
        though ``summary`` is declared on the category — without this the name
        fallback would miss every inherited slot.
        """
        inherited: dict[str, dict[str, str]] = {}
        for component in document.components:
            own = self._members.setdefault(str(refs.Reference("component", component.id)), {})
            merged: dict[str, str] = {}
            for ancestor in self._ancestors(document, component):
                for name, ref in self._members.get(str(refs.Reference("component", ancestor)), {}).items():
                    merged.setdefault(name, ref)
            merged.update(own)
            inherited[component.id] = merged
        for component in document.components:
            self._members[str(refs.Reference("component", component.id))] = inherited[component.id]

    @staticmethod
    def _ancestors(document: ProjectDocument, component: Component) -> tuple[str, ...]:
        """Parent chain and mixins, nearest first, each visited once."""
        order: list[str] = []
        seen: set[str] = {component.id}
        queue = [*([] if component.parent is None else [component.parent]), *component.mixins]
        while queue:
            ancestor_id = queue.pop(0)
            if ancestor_id in seen:
                continue
            seen.add(ancestor_id)
            ancestor = document.components_by_id.get(ancestor_id)
            if ancestor is None:
                continue
            order.append(ancestor_id)
            queue.extend([] if ancestor.parent is None else [ancestor.parent])
            queue.extend(ancestor.mixins)
        return tuple(order)

    def record_binding(self, binding: Binding, document: ProjectDocument) -> None:
        reference = refs.Reference("binding", binding.id)
        self.declare(binding.id, str(reference))
        if binding.debug_name:
            self.declare(binding.debug_name, str(reference))
        target = document.components_by_id.get(binding.component)
        if target is None:
            return
        members = self._members.setdefault(str(refs.Reference("component", target.id)), {})
        for property_binding in binding.properties:
            members[property_binding.name] = str(reference.child("property", property_binding.name))

    def finish(self) -> NameIndex:
        members: dict[str, dict[str, str]] = {}
        for name, ref in self._declarations.items():
            parts = self._members.get(ref)
            if parts:
                members.setdefault(name, dict(parts))
        owners: dict[str, set[str]] = {}
        for ref, parts in self._members.items():
            for name in parts:
                owners.setdefault(name, set()).add(ref)
        return NameIndex(
            declarations=dict(self._declarations),
            members=members,
            ambiguous_members=frozenset(name for name, owners_ in owners.items() if len(owners_) > 1),
        )


def message_names(message: str) -> tuple[list[str], list[tuple[str, str]], list[str]]:
    """The identifiers a message mentions.

    Returns ``(quoted_and_dotted_head_names, dotted_pairs, bare_class_words)``.
    Quoted spans contribute only when they are a single identifier (see
    :data:`_QUOTED`), and bare words only when they are capitalised like a class (see
    :data:`_CLASS_WORD`) — together, the two rules that keep prose and module paths
    out of the candidate list.
    """
    pairs = _DOTTED.findall(message)
    quoted = _QUOTED.findall(message)
    return ([head for head, _ in pairs] + quoted, list(pairs), _CLASS_WORD.findall(message))


def resolve_ref_by_name(document: ProjectDocument | NameIndex, message: str) -> str | None:
    """The IR ref a message's own words identify, or ``None``.

    Preference order, most specific first:

    1. a dotted name the message states outright (``SiteNode.city``);
    2. a declaration name plus one of its member names anywhere in the message
       (``"SiteNode" has no attribute "city"``);
    3. a declaration name on its own;
    4. a member name that no two declarations share.
    """
    index = document if isinstance(document, NameIndex) else build_name_index(document)
    heads, pairs, class_words = message_names(message)

    for head, tail in pairs:
        ref = index.member_ref(head, tail)
        if ref is not None:
            return ref
        declaration = index.ref_for(head)
        if declaration is not None:
            return declaration

    # Names are scanned in the order they appear so a message about two declarations
    # resolves to the one it started with, which is the one it is about.
    mentioned = list(dict.fromkeys(heads + class_words))
    for candidate in mentioned:
        declaration = index.ref_for(candidate)
        if declaration is None:
            continue
        for name in mentioned:
            member = index.member_ref(candidate, name)
            if member is not None:
                return member
        return declaration

    for candidate in mentioned:
        ref = index.unique_member_ref(candidate)
        if ref is not None:
            return ref
    return None


# ---------------------------------------------------------------------- hints


@dataclass(frozen=True, slots=True)
class _HintRule:
    """A sentence for one family of pyright diagnostics.

    ``pattern`` is the part of the message the sentence depends on: a rule whose
    template quotes a slot name must not fire on a message that names none. ``None``
    means the rule is keyed on the code alone, and is therefore only usable when the
    diagnostic carries one.

    ``template`` may quote ``{name}`` (a slot name from the message), ``{target}`` (a
    human name for the resolved ref) and ``{entity}`` (a human name for the
    declaration that owns it). It must read as an instruction: the raw message is
    already on screen.
    """

    code: str
    pattern: re.Pattern[str] | None
    template: str


_HINT_RULES: Final[tuple[_HintRule, ...]] = (
    _HintRule(
        "reportAttributeAccessIssue",
        re.compile(r"has no attribute \"(?P<name>[^\"]+)\""),
        "{name!r} is not a property of {entity}: add it in the topology editor, or point the expression at a property that declaration really has.",
    ),
    _HintRule(
        "reportArgumentType",
        re.compile(r"parameter \"(?P<name>[^\"]+)\""),
        "The expression bound to {name!r} produces a type its slot does not accept: change the last block of the stack, or change the slot's declared type.",
    ),
    _HintRule(
        "reportAssignmentType",
        None,
        "What is assigned to {entity} does not match the type the generated declaration asks for: change the expression in the document, not the generated file.",
    ),
    _HintRule(
        "reportCallIssue",
        re.compile(r"Argument missing for parameter \"(?P<name>[^\"]+)\""),
        "Bind {name!r} in this binding, or mark that property optional so the binding may leave it out.",
    ),
    _HintRule(
        "reportOptionalMemberAccess",
        re.compile(r"is possibly \"?None"),
        "Read through the nullable value only after unwrapping it: 'Keep rows where present' filters the rows away, 'default_to' keeps them.",
    ),
    _HintRule(
        "reportOptionalIterable",
        None,
        "A nullable value cannot be iterated as it stands: add 'Keep rows where present' or 'default_to' below the source block.",
    ),
    _HintRule(
        "reportMissingImports",
        None,
        "The generated file cannot import what it references: check the project's package name, and that pyrightconfig.json points at an interpreter with kg_build_system installed.",
    ),
    _HintRule(
        "reportMissingModuleSource",
        None,
        "The imported package has no source the checker can read: install it in the interpreter pyrightconfig.json points at.",
    ),
    _HintRule(
        "reportUnusedImport",
        None,
        "Nothing in this file uses that import, and it is written by the generator: change the document rather than the generated Python.",
    ),
    _HintRule(
        "reportUnusedVariable",
        None,
        "That generated symbol is never used: remove the declaration behind it, since editing the Python would be overwritten on the next generation.",
    ),
    _HintRule(
        "reportIndexIssue",
        None,
        "The value being subscripted does not support that index: check the field path in the source block.",
    ),
    _HintRule(
        "reportOperatorIssue",
        None,
        "These operands do not support that operator: the expression stack is combining types that cannot be combined.",
    ),
    _HintRule(
        "reportGeneralTypeIssues",
        None,
        "The code generated for {entity} does not type-check: re-check each block of the expression against the type the block before it produced.",
    ),
)

#: Sentence used when no rule matched but the problem resolved onto something.
_RESOLVED_FALLBACK: Final = "Fix {target}; this diagnostic was raised in the code generated from it."

#: … and when it resolved onto nothing at all.
_UNRESOLVED_FALLBACK: Final = (
    "No declaration in the project generated this code: check that the project has been regenerated since the last edit."
)

_KIND_LABEL: Final[dict[str, str]] = {
    "table": "table",
    "struct": "struct",
    "projection": "projection",
    "component": "component",
    "binding": "binding",
    "source": "source",
    "module": "module",
    "annotation_type": "annotation type",
}

_PART_LABEL: Final[dict[str, str]] = {
    "property": "property",
    "field": "field",
    "build_key": "build key",
}


def ref_description(ref: str | None, document: ProjectDocument | None = None) -> str | None:
    """A short human name for a ref, e.g. ``property 'city' of SiteNode``.

    Falls back to the ref's own text when it does not resolve: a stale anchor index
    is a reason to be vague, not a reason to say nothing.
    """
    if ref is None:
        return None
    try:
        reference = refs.parse(ref)
    except refs.ReferenceError:
        return repr(ref)
    kind_label = _KIND_LABEL[reference.kind]
    entity: str = reference.id
    if document is not None:
        named = getattr(refs.resolve(document, reference), "declaration_name", None)
        if isinstance(named, str) and named:
            entity = named
    if reference.name is not None:
        part_label = _PART_LABEL.get(reference.part or "", reference.part or "part")
        return f"{part_label} {reference.name!r} of {kind_label} {entity}"
    if reference.part is not None:
        return f"{_PART_LABEL.get(reference.part, reference.part)} of {kind_label} {entity}"
    return f"{kind_label} {entity}"


def make_hint(
    message: str,
    ref: str | None,
    document: ProjectDocument | None = None,
    code: str | None = None,
) -> str:
    """One plain sentence saying what the user should change.

    Never a restatement of ``message``: the rule-matched sentence is used when the
    diagnostic is a known pyright rule, and otherwise the hint names the editable
    declaration the problem landed on. The message is only read for the slot name the
    sentence quotes, so two different errors on the same slot still produce hints that
    differ where they must.
    """
    described = ref_description(ref, document)
    target = described if described is not None else "this declaration"
    entity = owner_description(ref, document) or target
    matched = _matching_rule(code, message)
    if matched is not None:
        return _fill(matched, message, target, entity)
    if described is None:
        return _UNRESOLVED_FALLBACK
    return _RESOLVED_FALLBACK.format(target=target)


def owner_description(ref: str | None, document: ProjectDocument | None = None) -> str | None:
    """A human name for the declaration a ref belongs to.

    For ``binding:site_binding.property.city`` that is the *component* the binding
    targets, because that is the class pyright names in an attribute or constructor
    error; naming the binding instead would describe the wrong thing.
    """
    if ref is None:
        return None
    try:
        reference = refs.parse(ref)
    except refs.ReferenceError:
        return repr(ref)
    if reference.kind == "binding" and document is not None:
        binding = document.bindings_by_id.get(reference.id)
        if binding is not None:
            component = document.components_by_id.get(binding.component)
            if component is not None:
                return f"component {component.declaration_name}"
    return ref_description(str(reference.entity), document)


def _matching_rule(code: str | None, message: str) -> _HintRule | None:
    """The rule for a diagnostic, if one applies.

    With a code the rule must agree with it; without one, only rules that can be
    recognised from the message alone are eligible, since a rule keyed on a code the
    diagnostic does not carry would be a guess.
    """
    for rule in _HINT_RULES:
        if code is not None:
            if rule.code != code:
                continue
        elif rule.pattern is None:
            continue
        if rule.pattern is None or rule.pattern.search(message):
            return rule
    return None


def _fill(rule: _HintRule, message: str, target: str, entity: str) -> str:
    """Substitute a rule template.

    Every template that quotes a name has a pattern that captures exactly that
    name, so no other group can be missing here.
    """
    match = rule.pattern.search(message) if rule.pattern is not None else None
    groups = {key: value for key, value in (match.groupdict() if match else {}).items() if value is not None}
    return rule.template.format(target=target, entity=entity, **groups)


def as_problem(item: Problem | Mapping[str, Any]) -> Problem:
    """A problem object from either a problem object or its JSON payload.

    The workspace holds diagnostics as JSON dicts on its way to the WebSocket, so
    :func:`annotate` accepts both spellings rather than forcing every caller to
    rebuild problems by hand. The id is recomputed, which reproduces the one a payload
    carries whenever it came from :func:`~studio_backend.diagnostics.problem.make_problem`.
    """
    if isinstance(item, Problem):
        return item
    return make_problem(
        tier=item["tier"],  # type: ignore[arg-type]
        severity=item["severity"],  # type: ignore[arg-type]
        message=str(item["message"]),
        code=item.get("code"),
        file=item.get("file"),
        line=item.get("line"),
        column=item.get("column"),
        end_line=item.get("end_line"),
        end_column=item.get("end_column"),
        ref=item.get("ref"),
        ref_trusted=item.get("ref_trusted"),  # type: ignore[arg-type]
        hint=item.get("hint"),
    )


def annotate(
    problems: Iterable[Problem | Mapping[str, Any]],
    anchors: Anchors | Mapping[str, Any] | None,
    document: ProjectDocument | None,
) -> list[Problem]:
    """Fill in ``ref``, ``ref_trusted`` and ``hint`` for every problem.

    Inputs are accepted as problem objects or as the JSON payloads the API serves
    (:func:`as_problem`), and ``anchors`` as an :class:`Anchors` index or as a decoded
    anchors.json object (:func:`as_anchors`), so no caller has to convert either.

    Problems that already carry a ref (the blueprint tier resolves its own) keep it and
    gain only a hint. Resolution order is the documented one: an anchor hit beats a name
    match, and the file's owner entry beats nothing. A problem whose ref the caller set
    but whose ``ref_trusted`` is empty is left alone rather than relabelled as an anchor
    hit it never earned.
    """
    index = build_name_index(document) if document is not None else None
    anchors = as_anchors(anchors)
    annotated: list[Problem] = []
    for raw in problems:
        problem = as_problem(raw)
        ref, trusted = problem.ref, problem.ref_trusted
        if ref is None and anchors is not None:
            anchor_ref, anchor_trusted = resolve(anchors, problem.file, problem.line, problem.column)
            if anchor_trusted == "anchor" and anchor_ref is not None:
                ref, trusted = anchor_ref, anchor_trusted
        if ref is None and index is not None:
            named = resolve_ref_by_name(index, problem.message)
            if named is not None:
                ref, trusted = named, "name"
        if ref is None and anchors is not None:
            owner_ref, owner_trusted = resolve(anchors, problem.file, problem.line, problem.column)
            if owner_ref is not None:
                ref, trusted = owner_ref, owner_trusted
        annotated.append(
            problem.refilled(
                ref=ref,
                ref_trusted=trusted if ref is not None else None,
                hint=problem.hint or make_hint(problem.message, ref, document, problem.code),
            )
        )
    return annotated


#: The name the workspace pipeline imports; identical to :func:`annotate`.
annotate_problems = annotate
