"""Blueprint-tier problems: framework validation text, mapped onto IR refs.

``create_blueprint(...)`` and ``compile(...)`` do not report structured errors —
they raise ``ValueError``/``TypeError`` whose text names the declarations that
broke (``studio/docs/AUTHORING_IR_CONTRACT.md`` §"Binding-level rules", and
``kg_build_system/binding/factories.py``, ``kg_build_system/compile/validation.py``
and ``kg_build_system/types/validation.py`` for the exact wording). The message is
the only evidence, so this module is a table of those wordings.

Each rule contributes:

``code``
    A stable name for the violated framework rule (``property_type_mismatch`` and
    friends). API.md asks for "framework error class" here; every one of these is a
    plain ``ValueError``/``TypeError``, so the class carries no information worth
    grouping or filtering on, while the rule does.

``ref`` / ``ref_trusted == "name"``
    Resolved from the names the message states, through the same name index the
    types tier uses — including the ``binding:node:<component>:<fingerprint>``
    symbol ids the compiler embeds, whose middle field is the component's logical
    name.

``hint``
    What to change in the editor, in terms of the user's own objects. The raw
    message stays in ``message``, so the hint never repeats it.

Positions are absent by nature: a framework validation error has no file, so
``file``/``line``/``column`` stay ``None`` and the UI shows these in the problems
panel against their ref.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

from ..ir import refs
from ..ir.document import ProjectDocument
from .mapping import NameIndex, build_name_index, ref_description
from .problem import Problem, make_problem

__all__ = ["BLUEPRINT_TIER", "map_blueprint_error"]

BLUEPRINT_TIER: Final = "blueprint"

#: ``binding:<kind>:<component>:<fingerprint>`` — the compiler's binding symbol.
_BINDING_SYMBOL: Final = re.compile(r"binding:(?:node|edge):([A-Za-z_][A-Za-z0-9_]*)(?::[0-9a-f]+)?")
#: A physical source symbol, ``source:<table name>``.
_SOURCE_SYMBOL: Final = re.compile(r"source:([A-Za-z_][A-Za-z0-9_]*)")
_SINGLE_QUOTED: Final = re.compile(r"'([A-Za-z_][A-Za-z0-9_.]*)'")
_DOUBLE_QUOTED: Final = re.compile(r"\"([A-Za-z_][A-Za-z0-9_.]*)\"")
_DOTTED: Final = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\b")
_WORD: Final = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")


@dataclass(frozen=True, slots=True)
class _Rule:
    """One framework message, its rule code, and the sentence for the editor."""

    code: str
    pattern: re.Pattern[str]
    hint: str


def _rule(code: str, pattern: str, hint: str) -> _Rule:
    return _Rule(code=code, pattern=re.compile(pattern), hint=hint)


#: Ordered most-specific first: the first pattern whose ``search`` matches wins.
_RULES: Final[tuple[_Rule, ...]] = (
    # -- binding property slots (factories._require_properties) --------------
    _rule(
        "property_type_mismatch",
        r"\b(?P<target>[A-Za-z_]\w*)\.(?P<attr>[A-Za-z_]\w*) expects (?P<expected>.+?), but the expression resolves to (?P<actual>.+)$",
        "{dotted} accepts one type and the bound expression produces another: rebuild the last block of that expression so its type matches the slot, or change the slot's type in the topology editor.",
    ),
    _rule(
        "property_value_missing",
        r"\b(?P<target>[A-Za-z_]\w*)\.(?P<attr>[A-Za-z_]\w*) must be assigned a value selection or expression",
        "{dotted} is a required property of this binding: give the slot an expression, or mark it optional in the topology editor.",
    ),
    _rule(
        "property_value_missing",
        r"\b(?P<target>[A-Za-z_]\w*)\.(?P<attr>[A-Za-z_]\w*) must be a value expression",
        "{dotted} is not filled with an expression: rebuild that property in the binding stack.",
    ),
    _rule(
        "property_incompatible_type",
        r"binding (?P<symbol>'[^']*'|\"[^\"]*\") property (?P<attr>'[^']*'|\"[^\"]*\") has an incompatible logical type",
        "This bound property's type does not agree with the slot it fills: change the expression or the declaration so they match.",
    ),
    _rule(
        "property_not_mapped_once",
        r"binding (?P<symbol>'[^']*'|\"[^\"]*\") must map every declared component property exactly once",
        "This binding does not fill each declared property exactly once: bind the missing properties and drop any repeated one.",
    ),
    _rule(
        "properties_wrong_class",
        r"properties must be an instance of (?P<target>[A-Za-z_]\w*)",
        "{dotted_or_target} builds the property record: construct it with the target component's own class so every slot is present.",
    ),
    # -- build keys (types.validation + factories._require_key) -------------
    _rule(
        "build_key_nullable",
        r"\b(?P<argument>build_key|source_build_key|target_build_key) must not be nullable",
        "{argument} can still be null: unwrap it with 'Keep rows where present' (or 'default_to') so the grain is a definite value.",
    ),
    _rule(
        "build_key_not_scalar",
        r"\b(?P<argument>build_key|source_build_key|target_build_key) must be a scalar",
        "{argument} is an array or struct: pick the single field that identifies the row, or 'expand' first and key the expanded rows.",
    ),
    _rule(
        "build_key_not_expression",
        r"\b(?P<argument>build_key|source_build_key|target_build_key) must be a value selection or expression",
        "{argument} is not an expression at all: build one in the stack editor and set it as the key.",
    ),
    _rule(
        "binding_keys_invalid",
        r"binding (?P<symbol>'[^']*'|\"[^\"]*\") keys must be non-null scalar expressions",
        "A key of this binding is nullable or not a scalar: unwrap it with 'Keep rows where present' and make sure it is one value per row.",
    ),
    # -- binding targets (factories._require_concrete_component + validation)
    _rule(
        "target_must_be_concrete",
        r"target must be a concrete (?P<kind>node|edge) component, not (?P<target>[A-Za-z_]\w*)",
        "{target} is a category, not a bindable component: choose a concrete {kind} that descends from it as this binding's target.",
    ),
    _rule(
        "target_must_be_concrete",
        r"(?P<kind>node|edge) binding (?P<symbol>'[^']*'|\"[^\"]*\") may not target abstract component (?P<target>'[^']*'|\"[^\"]*\")",
        "This binding targets a category: retarget it to a concrete {kind} under {target}.",
    ),
    _rule(
        "target_incompatible_component",
        r"(?P<kind>node|edge) binding (?P<symbol>'[^']*'|\"[^\"]*\") targets an incompatible component",
        "This binding's target is not a {kind} component: make the binding's kind match the component it targets.",
    ),
    # -- endpoint tokens -----------------------------------------------------
    _rule(
        "endpoint_required",
        r"\b(?P<side>source|target)_node must name the declared endpoint category (?P<target>[A-Za-z_]\w*): pass endpoint",
        "The {side} side of this edge is a category, so the binding must name a concrete component: pass endpoint({target} or something under it).",
    ),
    _rule(
        "endpoint_not_concrete",
        r"\b(?P<side>source|target)_node must name a concrete node component, not (?P<target>[A-Za-z_]\w*)",
        "{target} cannot be used as the {side} endpoint token: pick a concrete node component.",
    ),
    _rule(
        "endpoint_not_concrete",
        r"edge binding (?P<symbol>'[^']*'|\"[^\"]*\") (?P<side>source|target) endpoint (?P<target>'[^']*'|\"[^\"]*\") must name a concrete node component",
        "The {side} endpoint of this edge binding is abstract or unknown: choose a concrete node component for it.",
    ),
    _rule(
        "endpoint_not_descended",
        r"\b(?P<side>source|target)_node (?P<target>[A-Za-z_]\w*) must equal or descend from the declared endpoint category (?P<declared>[A-Za-z_]\w*)",
        "{target} is not under {declared}, which this edge declares as its {side}: pick a component that descends from that category, or widen the declaration.",
    ),
    _rule(
        "endpoint_not_descended",
        r"edge binding (?P<symbol>'[^']*'|\"[^\"]*\") (?P<side>source|target) endpoint (?P<target>'[^']*'|\"[^\"]*\") must equal or descend from the declared endpoint (?P<declared>'[^']*'|\"[^\"]*\")",
        "The {side} endpoint chosen for this binding is not under the category the edge declares ({declared}): change the endpoint or the edge's declaration.",
    ),
    _rule(
        "endpoint_token_required",
        r"\b(?P<side>source|target)_node must be an endpoint\(\.\.\.\) token, not the raw value (?P<value>.+)$",
        "The {side} endpoint must be an endpoint(<component>) token rather than a bare component: wrap it in endpoint(...).",
    ),
    _rule(
        "unknown_endpoint",
        r"edge (?P<edge>'[^']*'|\"[^\"]*\") references an unknown endpoint",
        "This edge names a source or target component that is not in the project: re-point the endpoint at an existing component.",
    ),
    # -- names that collide (validation._unique) -----------------------------
    _rule(
        "duplicate_symbol_ids",
        r"^blueprint symbol IDs must be unique",
        "Two declarations ended up with the same generated symbol: rename one of them in the document.",
    ),
    _rule(
        "duplicate_names",
        r"^(?P<context>.+?) must be unique",
        "{context}: two declarations would generate the same name, so one of them has to be renamed in the document.",
    ),
    _rule(
        "duplicate_module_ids",
        r"^module IDs must be unique",
        "Two configured modules share an id: enable one of them, or give the duplicates different module ids.",
    ),
    # -- logical and physical sources ----------------------------------------
    _rule(
        "unknown_logical_source",
        r"(?P<owner>.+?) references unknown logical source (?P<source>'[^']*'|\"[^\"]*\")",
        "This expression reads from a table or projection that is no longer in the project: re-point its source block at one that exists.",
    ),
    _rule(
        "unknown_field",
        r"(?P<owner>.+?) references unknown field (?P<field>'[^']*'|\"[^\"]*\") on logical source (?P<source>'[^']*'|\"[^\"]*\")",
        "{field} is not a member of {source}: choose a field the contract actually declares.",
    ),
    _rule(
        "unknown_source_table",
        r"^a physical source references an unknown table",
        "A bind_source points at a table that is not in the project: re-point that source at an existing table.",
    ),
    _rule(
        "table_without_source",
        r"^no source bound for: (?P<tables>.+)$",
        "These tables have no physical source bound yet: add a source for each of them ({tables}).",
    ),
    _rule(
        "undiscoverable_sources",
        r"^expressions reference undiscoverable logical sources: (?P<sources>.+)$",
        "These sources are referenced but never declared, so the plan cannot be built: declare them or remove the expressions that use them ({sources}).",
    ),
    # -- topology hierarchy --------------------------------------------------
    _rule(
        "unknown_parent",
        r"component (?P<component>'[^']*'|\"[^\"]*\") references an unknown parent",
        "This component's parent category is not in the project: choose an existing category or clear the parent.",
    ),
    _rule(
        "parent_wrong_kind",
        r"component (?P<component>'[^']*'|\"[^\"]*\") parent must name an abstract (?P<kind>node|edge) component",
        "A {kind} component can only descend from an abstract {kind}: choose a category of the same kind as its parent.",
    ),
    _rule(
        "parent_cycle",
        r"^component parent chain cycle includes (?P<component>'[^']*'|\"[^\"]*\")",
        "The parent chain loops back on itself: break the cycle by choosing a different parent.",
    ),
    _rule(
        "projection_cycle",
        r"^projection dependency cycle includes (?P<projection>'[^']*'|\"[^\"]*\")",
        "This projection depends on itself through another projection: break the cycle by removing one reference.",
    ),
    _rule(
        "node_declares_endpoints",
        r"^node (?P<component>'[^']*'|\"[^\"]*\") may not declare endpoints",
        "Node components have no endpoints: this one should be an edge component, or its endpoint fields should be cleared.",
    ),
    _rule(
        "edge_missing_endpoints",
        r"^edge (?P<component>'[^']*'|\"[^\"]*\") requires source and target components",
        "This edge is missing an endpoint: choose both a source and a target component.",
    ),
    # -- expression shape (validation.validate_expression) -------------------
    _rule(
        "expand_shape",
        r"(?P<owner>.+?) expand operation requires an array argument",
        "Expand is being applied to something that is not an array: put an array-valued field below it, or drop the expand block.",
    ),
    _rule(
        "expand_shape",
        r"(?P<owner>.+?) expand operation requires one argument",
        "This expand block is malformed: an expand takes exactly the array it expands.",
    ),
    _rule(
        "expand_shape",
        r"(?P<owner>.+?) expand operation has an incompatible result type",
        "The type after expand does not match its input's item type: check the blocks stacked directly above the expand.",
    ),
    _rule(
        "empty_blueprint",
        r"^blueprints require at least one graph (?P<requirement>component|binding)",
        "The project has nothing to compile yet: add a component and at least one binding.",
    ),
    _rule(
        "schema_version",
        r"^unsupported blueprint schema version",
        "The installed framework cannot read what was produced: check that studio and kg_build_system are the expected versions.",
    ),
)

#: Group names that never identify a declaration on their own.
_NON_NAME_GROUPS: Final = frozenset(
    {"kind", "argument", "side", "tables", "sources", "value", "requirement"}
)


def map_blueprint_error(error_text: str, document: ProjectDocument) -> Problem:
    """One framework error message, as a blueprint-tier problem.

    The message is stored verbatim (it is the framework's own words and the UI shows
    it), while ``hint`` says what to change. ``ref`` is resolved by looking the
    message's names up in the document; when nothing in the message matches a
    declaration the ref stays ``None`` rather than guessing at the nearest name.
    """
    index = build_name_index(document)
    text = " ".join(error_text.split())
    rule = _match_rule(text)
    ref = _resolve(text, rule, index, document)
    hint = _hint(rule, text, ref, document)
    return make_problem(
        tier=BLUEPRINT_TIER,
        severity="error",
        message=text,
        code=rule.code,
        file=None,
        ref=ref,
        ref_trusted="name" if ref is not None else None,
        hint=hint,
    )


def _match_rule(text: str) -> _Rule:
    for rule in _RULES:
        if rule.pattern.search(text):
            return rule
    return _FALLBACK


_FALLBACK: Final = _rule(
    "blueprint_validation_error",
    r".*",
    "The framework rejected this project during compilation: fix the declaration named above in the editor rather than the generated code.",
)


def _resolve(text: str, rule: _Rule, index: NameIndex, document: ProjectDocument) -> str | None:
    """The ref this message is about, from the names it states."""
    match = rule.pattern.search(text)
    groups = {key: value for key, value in (match.groupdict() if match else {}).items() if value}

    dotted = groups.get("dotted") or _dotted_name(text)
    if dotted is not None:
        head, _, tail = dotted.partition(".")
        member = index.member_ref(head, tail)
        if member is not None:
            return member

    # A binding symbol names its component, which is the most specific anchor the
    # message can carry for a binding-level failure.
    symbol = _symbol_component(text)
    if symbol is not None:
        ref = _binding_ref(document, symbol, groups.get("attr"))
        if ref is not None:
            return ref
        component = index.ref_for(symbol)
        if component is not None:
            return component

    for name in _candidate_names(text, groups):
        ref = index.ref_for(name)
        if ref is not None:
            return ref
    for name in _candidate_names(text, groups):
        ref = index.unique_member_ref(name)
        if ref is not None:
            return ref
    source = _source_symbol(text)
    if source is not None:
        return index.ref_for(source)
    return None


def _candidate_names(text: str, groups: Mapping[str, str]) -> tuple[str, ...]:
    """Names worth looking up, in the order the message states them.

    Regex groups are tried first because the rule knows what each name *is* —
    ``target`` is a declaration in a way that a quoted word later in the sentence is
    not.
    """
    ordered: list[str] = []
    for key, value in groups.items():
        if key in _NON_NAME_GROUPS:
            continue
        ordered.extend(_identifiers(value))
    ordered.extend(_identifiers(text))
    return tuple(dict.fromkeys(ordered))


def _identifiers(value: str) -> tuple[str, ...]:
    """Identifier-shaped names in a fragment: quoted names first, then all words.

    Quoting matters: the framework quotes the thing it is complaining about
    (``'site_binding'``, ``'sites'``) and leaves prose bare.
    """
    quoted = [name.strip("'\"") for name in (*_SINGLE_QUOTED.findall(value), *_DOUBLE_QUOTED.findall(value))]
    dotted_pairs = [(head, tail) for head, tail in _DOTTED.findall(value)]
    heads = [head for head, _ in dotted_pairs]
    words = _WORD.findall(value)
    return tuple(dict.fromkeys([*quoted, *heads, *words]))


def _dotted_name(text: str) -> str | None:
    pairs = _DOTTED.findall(text)
    return f"{pairs[0][0]}.{pairs[0][1]}" if pairs else None


def _symbol_component(text: str) -> str | None:
    match = _BINDING_SYMBOL.search(text)
    return match.group(1) if match else None


def _source_symbol(text: str) -> str | None:
    match = _SOURCE_SYMBOL.search(text)
    return match.group(1) if match else None


def _binding_ref(document: ProjectDocument, component_name: str, property_name: str | None) -> str | None:
    """The binding ref for the component a symbol id names.

    Multiple bindings may share a component, in which case the fingerprint in the
    symbol id is what distinguishes them and the document cannot say which is meant;
    preferring the one that actually fills ``property_name`` is the closest honest
    answer, and ``ref_trusted == "name"`` says as much.
    """
    component = document.components_by_id.get(component_name)
    if component is None:
        component = next((item for item in document.components if item.name == component_name), None)
    if component is None:
        return None
    bindings = document.bindings_for_component(component.id)
    if not bindings:
        return None
    if property_name is not None:
        name = property_name.strip("'\"")
        for binding in bindings:
            if any(item.name == name for item in binding.properties):
                return str(refs.build("binding", binding.id, "property", name))
    if len(bindings) == 1:
        return refs.build("binding", bindings[0].id)
    return str(refs.build("component", component.id))


def _hint(rule: _Rule, text: str, ref: str | None, document: ProjectDocument) -> str:
    """Fill the rule's sentence with the names the user recognises."""
    match = rule.pattern.search(text)
    groups = {key: value for key, value in (match.groupdict() if match else {}).items() if value}
    # Group values stay as the framework wrote them: ``{target}`` in a sentence is a
    # declaration name the user can find in the editor, while ``{entity}`` is the
    # human description of whatever the ref resolved onto.
    values: dict[str, str] = {key: _plain(value) for key, value in groups.items()}
    dotted = _dotted_name(text)
    values["dotted"] = dotted or ""
    values["dotted_or_target"] = dotted or _plain(groups.get("target", ""))
    values["entity"] = ref_description(ref, document) or _plain(groups.get("target", "")) or "this declaration"
    values.setdefault("target", values["entity"])
    return rule.hint.format_map(_SafeDict(values))


class _SafeDict(dict[str, str]):
    """Leaves an unrecognised placeholder visible instead of raising.

    A template quoting a group its rule never captures is a bug in the table above;
    it must not turn a user-facing diagnostic into an exception.
    """

    def __missing__(self, key: str) -> str:
        return f"({key})"


def _plain(value: str) -> str:
    """Strip the framework's quoting so the sentence reads as prose."""
    return value.strip().strip("'\"")
