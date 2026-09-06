"""Naming: the bridge between a document id and the Python name it renders as.

The framework infers a declaration's logical name by snake-casing its class name and
stripping one tier suffix (``InputTable`` → ``input``, ``RecordNode`` → ``record``,
``DocumentedAbstractNode`` → ``documented``). The studio has to pick Python names that
survive that inference unchanged, so a component named ``site`` in the document must
render as ``SiteNode`` and never as ``Site`` or ``NodeSite``. These rules are the
single place that mapping is stated; the generator and the id suggestions both use it.

The snake-casing matches ``kg_build_system._support.naming.snake_case`` — re-implemented
rather than imported because that module is framework-internal.
"""

from __future__ import annotations

import re

#: Tier suffixes per topology kind, in the framework's canonical order.
TOPOLOGY_SUFFIXES: dict[tuple[str, str], str] = {
    ("node", "concrete"): "Node",
    ("node", "category"): "AbstractNode",
    ("node", "template"): "NodeTemplate",
    ("edge", "concrete"): "Edge",
    ("edge", "category"): "AbstractEdge",
    ("edge", "template"): "EdgeTemplate",
}

DATA_SUFFIXES = {
    "table": "Table",
    "group": "TableGroup",
    "struct": "Struct",
    "projection": "Projection",
    "annotation_type": "",
}

_IDENTIFIER_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
_PASCAL_BOUNDARIES = (
    (re.compile(r"([A-Z]+)([A-Z][a-z])"), r"\1_\2"),
    (re.compile(r"([a-z0-9])([A-Z])"), r"\1_\2"),
    (re.compile(r"([A-Za-z])([0-9])"), r"\1_\2"),
    (re.compile(r"([0-9])([A-Za-z])"), r"\1_\2"),
)


def snake(value: str) -> str:
    for pattern, replacement in _PASCAL_BOUNDARIES:
        value = pattern.sub(replacement, value)
    value = re.sub(r"[^a-z0-9]+", "_", value.lower())
    value = value.strip("_")
    return value or "unnamed"


def pascal(value: str) -> str:
    """``has_unit`` → ``HasUnit``; ``site`` → ``Site``; ``id2`` → ``Id2``."""
    return "".join(part[:1].upper() + part[1:] for part in value.split("_") if part)


def component_declaration_name(kind: str, tier: str, name: str) -> str:
    suffix = TOPOLOGY_SUFFIXES.get((kind, tier))
    if suffix is None:
        raise ValueError(f"no topology naming rule for a {tier} {kind}")
    return f"{pascal(name)}{suffix}"


def data_declaration_name(section: str, name: str, *, group: bool = False) -> str:
    if section == "table":
        return f"{pascal(name)}{'TableGroup' if group else 'Table'}"
    suffix = DATA_SUFFIXES.get(section)
    if suffix is None:
        raise ValueError(f"no data naming rule for {section!r}")
    return f"{pascal(name)}{suffix}"


def is_identifier(value: str) -> bool:
    return _IDENTIFIER_PATTERN.match(value) is not None


def suggest_id(label: str, taken: set[str], *, kind: str | None = None) -> str:
    """A free snake_case id for a user-typed label.

    The tier suffix is stripped from the suggestion, because the document stores the
    logical name and the generator re-adds the suffix: proposing ``site_node`` for a
    node called ``SiteNode`` would render as ``SiteNodeNode``.
    """
    stem = snake(label or kind or "item")
    for suffix in ("abstract_node", "node_template", "node", "abstract_edge", "edge_template", "edge",
                   "table_group", "table", "struct", "projection"):
        if stem.endswith(f"_{suffix}"):
            stem = stem[: -len(suffix) - 1]
            break
    stem = stem or "item"
    if stem not in taken:
        return stem
    counter = 2
    while f"{stem}_{counter}" in taken:
        counter += 1
    return f"{stem}_{counter}"


def declaration_name(label: str, section: str, *, tier: str = "concrete", kind: str = "node", group: bool = False) -> str:
    """Suggest a Python class name from free text the user typed."""
    name = suggest_id(label, set())
    if section == "component":
        return component_declaration_name(kind, tier, name)
    return data_declaration_name(section, name, group=group)
