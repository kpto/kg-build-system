"""Anchor-index loading, position resolution and the name fallback.

The anchor fixture here is hand-authored, exactly in the format the generator
publishes, because the generator is written in parallel and nothing in diagnostics
may depend on it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from studio_backend.diagnostics.mapping import (
    Anchor,
    AnchorFormatError,
    Anchors,
    annotate,
    build_name_index,
    load_anchors,
    make_hint,
    ref_description,
    resolve,
    resolve_ref_by_name,
)
from studio_backend.diagnostics.problem import Problem, make_problem
from studio_backend.ir.document import (
    Binding,
    Component,
    DataField,
    FieldExpression,
    LiteralExpression,
    Project,
    ProjectDocument,
    Property,
    PropertyBinding,
    Table,
    unit,
)

BINDING_FILE = "kg_project/bindings/site/__init__.py"
TOPOLOGY_FILE = "kg_project/topology/site/__init__.py"

#: The generated binding as the renderer laid it out. Positions are 1-based; the
#: whole-file entry is what a position outside every range falls back to.
ANCHOR_PAYLOAD: dict[str, Any] = {
    "format_version": 1,
    "revision": 12,
    "document_fingerprint": "sha256-0f0f",
    "files": {
        BINDING_FILE: [
            {"ref": "binding:site_binding", "line": 12, "end_line": 26, "column": 1, "end_column": 2, "node": "call"},
            {
                "ref": "binding:site_binding.property.name",
                "line": 19,
                "end_line": 19,
                "column": 14,
                "end_column": 41,
                "node": "keyword",
            },
            {
                "ref": "binding:site_binding.property.city",
                "line": 20,
                "end_line": 20,
                "column": 14,
                "end_column": 41,
                "node": "keyword",
            },
            {"ref": "binding:site_binding", "line": 1, "end_line": 27, "column": 1, "end_column": 1, "node": "file"},
        ],
        TOPOLOGY_FILE: [
            {"ref": "component:site", "line": 8, "end_line": 14, "column": 1, "end_column": 1, "node": "class_def"},
            {
                "ref": "component:site.property.city",
                "line": 12,
                "end_line": 12,
                "column": 5,
                "end_column": 40,
                "node": "ann_assign",
            },
            {"ref": "component:site", "line": 1, "end_line": 15, "column": 1, "end_column": 1, "node": "file"},
        ],
    },
}


def _document() -> ProjectDocument:
    """The declarations the fixture anchors point at.

    ``city`` is declared ``str`` on the component and filled by the binding from a
    nullable column, which is exactly the shape that produces the mismatch pyright
    reports at the binding call.
    """
    documented = Component(
        id="documented",
        kind="node",
        tier="category",
        declaration_name="DocumentedAbstractNode",
        name="documented",
        properties=(Property(name="summary", logical_type=unit("str")),),
    )
    site = documented.updated(
        id="site",
        tier="concrete",
        declaration_name="SiteNode",
        name="site",
        parent="documented",
        properties=(Property(name="name", logical_type=unit("str")), Property(name="city", logical_type=unit("str"))),
    )
    sites = Table(
        id="sites",
        declaration_name="SitesTable",
        name="sites",
        fields=(
            DataField(name="site_id", logical_type=unit("str", nullable=True)),
            DataField(name="site_name", logical_type=unit("str", nullable=True)),
        ),
    )
    binding = Binding(
        id="site_binding",
        kind="node",
        component="site",
        build_key=FieldExpression(source="sites", path=("site_id",), logical_type=unit("str")),
        properties=(
            PropertyBinding(
                name="name",
                expression=LiteralExpression(value="Unnamed site", logical_type=unit("str")),
            ),
            PropertyBinding(
                name="city",
                expression=FieldExpression(
                    source="sites", path=("site_id",), logical_type=unit("str", nullable=True)
                ),
            ),
        ),
    )
    return ProjectDocument(
        project=Project(name="Monitored estate", package="kg_project"),
        tables=(sites,),
        components=(documented, site),
        bindings=(binding,),
    )


@pytest.fixture
def document() -> ProjectDocument:
    return _document()


@pytest.fixture
def anchors_path(tmp_path: Path) -> Path:
    path = tmp_path / "anchors.json"
    path.write_text(json.dumps(ANCHOR_PAYLOAD), encoding="utf-8")
    return path


@pytest.fixture
def anchors(anchors_path: Path) -> Anchors:
    return load_anchors(anchors_path)


def _types_problem(
    message: str,
    *,
    file: str | None,
    line: int | None,
    column: int | None,
    code: str | None = "reportArgumentType",
) -> Problem:
    return make_problem(
        tier="types",
        severity="error",
        message=message,
        code=code,
        file=file,
        line=line,
        column=column,
        end_line=line,
        end_column=None if column is None else column + 10,
    )


# ------------------------------------------------------------------ load_anchors


def test_load_anchors_reads_the_agreed_format(anchors: Anchors) -> None:
    assert anchors.format_version == 1
    assert anchors.revision == 12
    assert anchors.document_fingerprint == "sha256-0f0f"
    assert anchors.file_count == 2
    entries = anchors.entries(BINDING_FILE)
    assert all(isinstance(entry, Anchor) for entry in entries)
    # Entries are stored innermost-first, which is what makes the resolver's first
    # hit the tightest one.
    assert [entry.node for entry in entries].count("file") == 1
    assert entries[0].span <= entries[-1].span


def test_owner_entry_is_the_whole_file_anchor(anchors: Anchors) -> None:
    owner = anchors.owner(BINDING_FILE)
    assert owner is not None
    assert owner.node == "file"
    assert owner.ref == "binding:site_binding"


def test_missing_anchor_index_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(AnchorFormatError, match="no anchor index"):
        load_anchors(tmp_path / "nothing.json")


def test_unsupported_format_version_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "anchors.json"
    path.write_text(json.dumps({**ANCHOR_PAYLOAD, "format_version": 2}), encoding="utf-8")
    with pytest.raises(AnchorFormatError, match="format_version"):
        load_anchors(path)


def test_entry_missing_a_position_is_rejected(tmp_path: Path) -> None:
    payload = json.loads(json.dumps(ANCHOR_PAYLOAD))
    del payload["files"][BINDING_FILE][0]["end_column"]
    path = tmp_path / "anchors.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(AnchorFormatError, match="end_column"):
        load_anchors(path)


def test_malformed_json_is_an_error(tmp_path: Path) -> None:
    path = tmp_path / "anchors.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(AnchorFormatError, match="readable JSON"):
        load_anchors(path)


# ---------------------------------------------------------------------- resolve


def test_position_resolves_to_the_innermost_range(anchors: Anchors) -> None:
    assert resolve(anchors, BINDING_FILE, 20, 20) == ("binding:site_binding.property.city", "anchor")


def test_innermost_range_wins_over_the_enclosing_call(anchors: Anchors) -> None:
    """Line 19 sits inside the binding call *and* inside its ``name`` keyword."""
    assert resolve(anchors, BINDING_FILE, 19, 30) == ("binding:site_binding.property.name", "anchor")


def test_position_inside_the_call_but_outside_any_slot(anchors: Anchors) -> None:
    assert resolve(anchors, BINDING_FILE, 13, 5) == ("binding:site_binding", "anchor")


def test_position_outside_every_range_falls_back_to_the_file_owner(anchors: Anchors) -> None:
    """The header comment line is inside the file's owner range and nothing else."""
    assert resolve(anchors, BINDING_FILE, 2, 1) == ("binding:site_binding", "file")


def test_column_outside_a_range_on_its_only_line_is_not_a_hit(anchors: Anchors) -> None:
    """The end of line 15 is inside the file and past the class declaration."""
    assert resolve(anchors, TOPOLOGY_FILE, 15, 5) == ("component:site", "file")


def test_line_inside_an_enclosing_range_resolves_to_it(anchors: Anchors) -> None:
    assert resolve(anchors, TOPOLOGY_FILE, 10, 1) == ("component:site", "anchor")


def test_unknown_file_resolves_to_nothing(anchors: Anchors) -> None:
    assert resolve(anchors, "kg_project/build.py", 1, 1) == (None, None)


def test_a_file_with_only_an_owner_entry_reports_the_owner(anchors: Anchors) -> None:
    single = Anchors(
        format_version=1,
        revision=1,
        document_fingerprint="",
        files={"kg_project/sources.py": (Anchor("source:sites_source", 1, 4, 1, 1, "file"),)},
    )
    assert resolve(single, "kg_project/sources.py", 3, 9) == ("source:sites_source", "file")


def test_missing_position_still_returns_the_file_owner(anchors: Anchors) -> None:
    assert resolve(anchors, TOPOLOGY_FILE, None, None) == ("component:site", "file")


def test_anchor_contains_is_inclusive_at_both_ends() -> None:
    anchor = Anchor(ref="component:site", line=10, end_line=12, column=5, end_column=20, node="class_def")
    assert anchor.contains(10, 5)
    assert anchor.contains(11, 1)
    assert anchor.contains(12, 20)
    assert not anchor.contains(10, 4)
    assert not anchor.contains(12, 21)
    assert not anchor.contains(9, 5)


# ------------------------------------------------------------------- by name


def test_dotted_name_in_the_message_resolves_to_the_slot(document: ProjectDocument) -> None:
    assert resolve_ref_by_name(document, "SiteNode.city is unknown") == "binding:site_binding.property.city"


def test_quoted_class_plus_quoted_attribute_resolves(document: ProjectDocument) -> None:
    message = 'Cannot access attribute "city" for class "SiteNode"'
    assert resolve_ref_by_name(document, message) == "binding:site_binding.property.city"


def test_inherited_slot_resolves_to_where_it_is_declared(document: ProjectDocument) -> None:
    """``summary`` belongs to the category; SiteNode only inherits it."""
    assert resolve_ref_by_name(document, '"SiteNode" has no attribute "summary"') == (
        "component:documented.property.summary"
    )


def test_parameter_name_resolves_alongside_its_class(document: ProjectDocument) -> None:
    message = (
        'Argument of type "FieldExpression" cannot be assigned to parameter "city" '
        'of type "PropertySlot[str]" in constructor "SiteNode"'
    )
    assert resolve_ref_by_name(document, message) == "binding:site_binding.property.city"


def test_message_naming_only_a_class_resolves_to_the_class(document: ProjectDocument) -> None:
    assert resolve_ref_by_name(document, '"SitesTable" is not a known symbol') == "table:sites"


def test_quoted_logical_name_is_an_alias(document: ProjectDocument) -> None:
    """The framework quotes what it complains about, and uses the logical name."""
    assert resolve_ref_by_name(document, "site_binding references unknown logical source 'sites'") == "table:sites"


def test_a_module_path_in_prose_is_not_a_declaration(document: ProjectDocument) -> None:
    assert resolve_ref_by_name(document, "no rows arrived from sites") is None


def test_ambiguous_member_name_is_not_guessed(document: ProjectDocument) -> None:
    index = build_name_index(document)
    assert "city" not in index.ambiguous_members
    assert index.unique_member_ref("city") == "binding:site_binding.property.city"

    with_second = document.updated(
        components=(
            *document.components,
            Component(
                id="unit",
                kind="node",
                tier="concrete",
                declaration_name="UnitNode",
                name="unit",
                parent="documented",
                properties=(Property(name="city", logical_type=unit("str")),),
            ),
        )
    )
    shared = build_name_index(with_second)
    assert "city" in shared.ambiguous_members
    assert shared.unique_member_ref("city") is None


def test_message_with_no_known_name_resolves_to_nothing(document: ProjectDocument) -> None:
    assert resolve_ref_by_name(document, 'Import "kg_build_system" could not be resolved') is None


# ----------------------------------------------------------------------- hints


def test_hint_for_a_type_mismatch_names_the_slot_and_what_to_change(document: ProjectDocument) -> None:
    message = 'Argument of type "int" cannot be assigned to parameter "city" of type "str"'
    hint = make_hint(message, "binding:site_binding.property.city", document, "reportArgumentType")
    assert "'city'" in hint
    assert message not in hint
    assert "change" in hint.lower()


def test_hint_for_a_missing_attribute_names_the_owning_declaration(document: ProjectDocument) -> None:
    message = '"SiteNode" has no attribute "city"'
    hint = make_hint(message, "binding:site_binding.property.city", document, "reportAttributeAccessIssue")
    assert "SiteNode" in hint and "city" in hint


def test_hint_for_an_unbound_slot(document: ProjectDocument) -> None:
    message = 'Argument missing for parameter "summary"'
    hint = make_hint(message, "binding:site_binding", document, "reportCallIssue")
    assert "summary" in hint


def test_hint_without_a_rule_code_still_explains_the_resolved_ref(document: ProjectDocument) -> None:
    hint = make_hint(
        'Expression of type "int" is incompatible with declared type "str"',
        "component:site.property.city",
        document,
    )
    assert "city" in hint
    assert "incompatible with declared type" not in hint


def test_hint_when_nothing_resolved_says_so(document: ProjectDocument) -> None:
    hint = make_hint("Something unexpected", None, document, "reportUnknownVariableType")
    assert "no declaration" in hint.lower()


def test_ref_description_uses_the_declaration_name(document: ProjectDocument) -> None:
    assert ref_description("component:site", document) == "component SiteNode"
    assert (
        ref_description("binding:site_binding.property.city", document)
        == "property 'city' of binding site_binding"
    )
    assert ref_description(None, document) is None


# -------------------------------------------------------------------- annotate


def test_annotate_fills_ref_from_an_anchor_hit(anchors: Anchors, document: ProjectDocument) -> None:
    [annotated] = annotate(
        [_types_problem('Argument of type "int" cannot be assigned to parameter "city"', file=BINDING_FILE, line=20, column=20)],
        anchors,
        document,
    )
    assert annotated.ref == "binding:site_binding.property.city"
    assert annotated.ref_trusted == "anchor"
    assert annotated.hint is not None and "'city'" in annotated.hint
    assert annotated.id == _types_problem(
        'Argument of type "int" cannot be assigned to parameter "city"', file=BINDING_FILE, line=20, column=20
    ).id


def test_annotate_falls_back_to_the_file_owner(anchors: Anchors, document: ProjectDocument) -> None:
    [annotated] = annotate(
        [
            _types_problem(
                'Import "kg_project.topology.site" could not be resolved',
                file=TOPOLOGY_FILE,
                line=2,
                column=1,
                code="reportMissingImports",
            )
        ],
        anchors,
        document,
    )
    assert annotated.ref == "component:site"
    assert annotated.ref_trusted == "file"


def test_annotate_prefers_a_name_match_over_the_file_owner(anchors: Anchors, document: ProjectDocument) -> None:
    """An inherited slot on the topology file: the name says more than the owner does."""
    [annotated] = annotate(
        [
            _types_problem(
                '"SiteNode" has no attribute "summary"',
                file=TOPOLOGY_FILE,
                line=2,
                column=1,
                code="reportAttributeAccessIssue",
            )
        ],
        anchors,
        document,
    )
    assert annotated.ref == "component:documented.property.summary"
    assert annotated.ref_trusted == "name"


def test_annotate_leaves_an_unmappable_problem_without_a_ref(anchors: Anchors, document: ProjectDocument) -> None:
    [annotated] = annotate(
        [_types_problem("Module is deprecated", file="kg_project/elsewhere.py", line=1, column=1, code="reportDeprecated")],
        anchors,
        document,
    )
    assert annotated.ref is None
    assert annotated.ref_trusted is None
    assert annotated.hint is not None


def test_annotate_keeps_a_ref_the_caller_supplied(anchors: Anchors, document: ProjectDocument) -> None:
    original = _types_problem("a blueprint message", file=None, line=None, column=None).refilled(
        ref="binding:site_binding", ref_trusted="name", hint=None
    )
    [annotated] = annotate([original], anchors, document)
    assert annotated.ref == "binding:site_binding"
    assert annotated.ref_trusted == "name"
    assert annotated.hint is not None


def test_annotate_keeps_a_hint_the_caller_wrote(anchors: Anchors, document: ProjectDocument) -> None:
    original = _types_problem("blueprint text", file=None, line=None, column=None).refilled(hint="already explained")
    [annotated] = annotate([original], anchors, document)
    assert annotated.hint == "already explained"


def test_annotate_without_anchors_or_document_still_hints(document: ProjectDocument) -> None:
    [annotated] = annotate(
        [_types_problem('"SiteNode" has no attribute "city"', file=None, line=None, column=None)],
        None,
        document,
    )
    assert annotated.ref == "binding:site_binding.property.city"
    assert annotated.ref_trusted == "name"

    [bare] = annotate([_types_problem("anything", file=None, line=None, column=None)], None, None)
    assert bare.ref is None
    assert bare.hint is not None


# ------------------------------------------------------- the payload/object boundary


def test_a_problem_is_a_mapping_over_the_contract_fields(document: ProjectDocument) -> None:
    problem = _types_problem("a message", file="kg_project/build.py", line=1, column=1)
    assert dict(problem) == problem.as_json()
    assert list(problem) == list(problem.as_json())
    assert problem["tier"] == "types"
    assert problem.get("ref") is None
    assert problem.get("nothing", "fallback") == "fallback"
    assert len(problem) == len(problem.as_json())
    with pytest.raises(KeyError):
        problem["not_a_field"]


def test_annotate_accepts_problems_as_json_payloads(anchors: Anchors, document: ProjectDocument) -> None:
    """The workspace holds diagnostics as JSON dicts; annotating those must work."""
    payload = _types_problem(
        'Argument of type "int" cannot be assigned to parameter "city"',
        file=BINDING_FILE,
        line=20,
        column=20,
    ).as_json()
    [annotated] = annotate([payload], anchors, document)
    assert annotated.ref == "binding:site_binding.property.city"
    assert annotated.ref_trusted == "anchor"
    assert annotated.id == payload["id"], "the identity must survive the round trip"


def test_annotate_accepts_a_raw_anchor_payload(anchors_path: Path, document: ProjectDocument) -> None:
    payload = json.loads(anchors_path.read_text(encoding="utf-8"))
    [annotated] = annotate(
        [_types_problem('"SiteNode" has no attribute "city"', file=BINDING_FILE, line=20, column=20)],
        payload,
        document,
    )
    assert annotated.ref == "binding:site_binding.property.city"


def test_a_malformed_raw_anchor_payload_is_rejected(document: ProjectDocument) -> None:
    with pytest.raises(AnchorFormatError, match="format_version"):
        annotate(
            [_types_problem("anything", file=None, line=None, column=None)],
            {"format_version": 99, "files": {}},
            document,
        )


def test_annotate_problems_is_the_same_function() -> None:
    from studio_backend.diagnostics.mapping import annotate_problems

    assert annotate_problems is annotate
