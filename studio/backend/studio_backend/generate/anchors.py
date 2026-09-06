"""The anchor index: a position in generated Python back to the IR that made it.

The index is built by parsing the rendered files with libcst rather than by trusting
the renderer's intent, so it describes the code as it actually is: the file is parsed
once, every node's position is resolved, and the hints a renderer returned with the
file say which IR ref each construct belongs to. Anything a renderer did not label —
an import line, a blank — is covered by the file's own node, which spans the whole
file and carries its owner ref. A file shared by several declarations, such as a
package ``__init__.py``, is given no owner ref at all: a diagnostic in it is then
reported unmapped instead of being blamed on whichever member happened to sort first.

Positions are 1-based lines and 1-based columns, which is pyright's convention:
libcst reports 1-based lines with 0-based columns, so every column is shifted once,
here, and nowhere else.

.. code-block:: json

    {"format_version": 1, "revision": 12, "document_fingerprint": "sha256…",
     "files": {"kg_project/bindings/site/__init__.py": [
       {"ref": "binding:site_binding", "line": 12, "end_line": 26, "column": 1,
        "end_column": 2, "node": "file"},
       {"ref": "binding:site_binding.property.city", "line": 20, "end_line": 20,
        "column": 14, "end_column": 41, "node": "keyword"}]}}
"""

from __future__ import annotations

from typing import Any, Final

import libcst as cst
from libcst.metadata import CodePosition, CodeRange, PositionProvider

from ..ir.document import ProjectDocument
from .render import AnchorHint, GenerationError, RenderedFile, validate_source

ANCHOR_FORMAT_VERSION: Final = 1
ANCHOR_FILENAME: Final = "anchors.json"

#: The kinds of construct a hint can point at, and the node label the index records.
NODE_LABELS: Final = {
    "class": "class",
    "member": "member",
    "property": "member",
    "assignment": "call",
    "expression": "expression",
    "keyword": "keyword",
}


class AnchorIndexError(Exception):
    """A rendered file whose own hints do not describe it, which is a generator bug."""


def build_anchor_index(
    document: ProjectDocument,
    files: list[RenderedFile],
    *,
    fingerprint: str,
    revision: int | None = None,
) -> dict[str, Any]:
    """The whole ``anchors.json`` payload for one rendering of one document."""
    payload: dict[str, Any] = {
        "format_version": ANCHOR_FORMAT_VERSION,
        "revision": document.revision if revision is None else revision,
        "document_fingerprint": fingerprint,
        "files": {},
    }
    index: dict[str, list[dict[str, Any]]] = {}
    for rendered in sorted(files, key=lambda item: item.path):
        if not rendered.path.endswith(".py"):
            continue
        index[rendered.path] = anchors_for(rendered)
    payload["files"] = index
    return payload


def anchors_for(rendered: RenderedFile) -> list[dict[str, Any]]:
    """Every anchor of one owned Python file, file node first."""
    validate_source(rendered.content, path=rendered.path)
    wrapper = cst.MetadataWrapper(cst.parse_module(rendered.content))
    positions: dict[cst.CSTNode, CodeRange] = wrapper.resolve(PositionProvider)
    module = wrapper.module

    def located(node: cst.CSTNode, ref: str, kind: str) -> dict[str, Any]:
        span = positions.get(node)
        if span is None:
            raise AnchorIndexError(f"{rendered.path}: no position for {ref!r}")
        return _anchor(ref, span, NODE_LABELS.get(kind, kind))

    anchors: list[dict[str, Any]] = []
    if rendered.owner_ref:
        # A shared package marker names no single declaration, so it carries no file
        # node: a diagnostic there is reported unmapped rather than blamed on a member.
        anchors.append(_anchor(rendered.owner_ref, _file_span(rendered.content), "file"))
    classes = _classes(module)
    assignments = _module_assignments(module)

    for hint in rendered.anchors:
        node = _resolve(hint, classes, assignments, rendered.path)
        if node is None:
            raise AnchorIndexError(
                f"{rendered.path}: nothing declares {hint.name!r} "
                f"({hint.kind}) for {hint.ref!r}"
            )
        anchors.append(located(node, hint.ref, hint.kind))
        if hint.kind == "expression":
            # A stack is where a type error lands mid-chain, so each call in it gets
            # its own anchor; a declaration's inner calls are already labelled.
            anchors.extend(_nested_calls(node, hint.ref, positions, located))
    return _ordered(anchors)


# ------------------------------------------------------------------- construction


def _anchor(ref: str, span: CodeRange, node: str) -> dict[str, Any]:
    return {
        "ref": ref,
        "line": span.start.line,
        "end_line": span.end.line,
        "column": span.start.column + 1,
        "end_column": span.end.column + 1,
        "node": node,
    }


def _file_span(content: str) -> CodeRange:
    """The whole file, so a position on an import line still resolves to a ref.

    Measured from the text rather than from the module node: libcst's module range
    covers the statements, and the generated header above them is part of the file.
    """
    lines = content.splitlines() or [""]
    return CodeRange(
        start=CodePosition(line=1, column=0),
        end=CodePosition(line=len(lines), column=len(lines[-1])),
    )


def _ordered(anchors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """File node first, then innermost-first so a lookup can take the last hit."""
    file_nodes = [item for item in anchors if item["node"] == "file"]
    rest = [item for item in anchors if item["node"] != "file"]
    rest.sort(key=lambda item: (item["line"], item["column"], -item["end_line"], -item["end_column"], item["ref"]))
    return [*file_nodes, *rest]


def _nested_calls(
    node: cst.CSTNode,
    ref: str,
    positions: dict[cst.CSTNode, CodeRange],
    located: Any,
) -> list[dict[str, Any]]:
    """Each call inside one labelled construct, so a stack's middle resolves too."""
    found: list[dict[str, Any]] = []
    for inner in _walk(node):
        if isinstance(inner, cst.Call) and inner is not node:
            found.append(located(inner, ref, "expression"))
    return found


def _walk(node: cst.CSTNode) -> list[cst.CSTNode]:
    collector = _Gatherer()
    node.visit(collector)
    return collector.nodes


class _Gatherer(cst.CSTVisitor):
    """Every descendant node of a subtree, in source order."""

    def __init__(self) -> None:
        self.nodes: list[cst.CSTNode] = []

    def on_visit(self, node: cst.CSTNode) -> bool:
        self.nodes.append(node)
        return True


# ------------------------------------------------------------------ hint resolution


def _classes(module: cst.Module) -> dict[str, cst.ClassDef]:
    found: dict[str, cst.ClassDef] = {}
    for statement in module.body:
        for node in _statement_nodes(statement):
            if isinstance(node, cst.ClassDef) and node.name.value not in found:
                found[node.name.value] = node
    return found


def _module_assignments(module: cst.Module) -> dict[str, cst.CSTNode]:
    """Every module-level name the file assigns, mapped to its assignment node."""
    found: dict[str, cst.CSTNode] = {}
    for statement in module.body:
        if not isinstance(statement, cst.SimpleStatementLine):
            continue
        for node in statement.body:
            for name in _assigned_names(node):
                found.setdefault(name, node)
    return found


def _resolve(
    hint: AnchorHint,
    classes: dict[str, cst.ClassDef],
    assignments: dict[str, cst.BaseAssign],
    path: str,
) -> cst.CSTNode | None:
    if hint.kind == "class":
        return classes.get(hint.name)
    if hint.kind in {"member", "property"}:
        class_name, _, attribute = hint.name.partition(".")
        holder = classes.get(class_name)
        if holder is None:
            return None
        return _class_member(holder, attribute)
    if hint.kind in {"assignment", "expression"}:
        return assignments.get(hint.name)
    if hint.kind == "keyword":
        holder = assignments.get(hint.name)
        if holder is None:
            return None
        return _keyword(holder, hint.keyword, path)
    return None


def _class_member(holder: cst.ClassDef, attribute: str) -> cst.CSTNode | None:
    for statement in holder.body.body:
        if attribute in _assignment_targets(statement):
            return statement
    return None


def _keyword(holder: cst.CSTNode, keyword: str | None, path: str) -> cst.CSTNode | None:
    if keyword is None:
        return holder
    matches = [
        argument
        for argument in _keywords(holder)
        if isinstance(argument.keyword, cst.Name) and argument.keyword.value == keyword
    ]
    if not matches:
        return None
    if len(matches) > 1:
        # Two slots of one binding cannot share a name, so this is a generator bug.
        raise GenerationError(
            f"{path}: {keyword!r} appears twice in one binding call, so the anchor "
            "index cannot say which one a position belongs to"
        )
    return matches[0]


def _keywords(node: cst.CSTNode) -> list[cst.Arg]:
    return [
        item
        for item in _walk(node)
        if isinstance(item, cst.Arg) and isinstance(item.keyword, cst.Name)
    ]


def _statement_nodes(statement: cst.BaseStatement | cst.BaseSuite) -> list[cst.CSTNode]:
    return [item for item in _walk(statement) if isinstance(item, (cst.ClassDef, cst.FunctionDef))]


def _assignment_targets(statement: cst.BaseNode) -> list[str]:
    """The names one statement assigns to, in source order."""
    names: list[str] = []
    for node in _walk(statement):
        names.extend(_assigned_names(node))
    return names


def _assigned_names(node: cst.CSTNode) -> list[str]:
    if isinstance(node, cst.AnnAssign):
        return _targets(node.target)
    if isinstance(node, cst.Assign):
        return [name for element in node.targets for name in _targets(element.target)]
    return []


def _targets(target: cst.BaseAssignTargetExpression) -> list[str]:
    if isinstance(target, cst.Name):
        return [target.value]
    if isinstance(target, cst.Tuple):
        return [name for element in target.elements for name in _targets(element.value)]
    return []
