"""Store revisions, structural validation, naming and plan projection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from studio_backend.ir.document import (
    Binding,
    Component,
    DataField,
    Module,
    Project,
    ProjectDocument,
    Property,
    Source,
    Table,
    unit,
)
from studio_backend.ir.names import (
    component_declaration_name,
    data_declaration_name,
    snake,
    suggest_id,
)
from studio_backend.ir.store import (
    DocumentInvalid,
    DocumentStore,
    RevisionConflict,
    content_fingerprint,
)
from studio_backend.ir.validate import validate_document

REPO = Path(__file__).resolve().parents[3]


def _table(identifier: str = "sites", **changes: object) -> Table:
    payload: dict = {
        "id": identifier,
        "declaration_name": f"{identifier.title()}Table",
        "name": identifier,
        "fields": (DataField(name="code", logical_type=unit("str")),),
    }
    payload.update(changes)
    return Table.model_validate(payload)


def _document(**sections: object) -> ProjectDocument:
    payload: dict = {
        "project": Project(name="Demo", package="demo"),
        "tables": [_table()],
        "sources": [
            Source(id="sites", table="sites", location="data/sites.json", format="json")
        ],
    }
    payload.update(sections)
    return ProjectDocument.model_validate(payload)


# -- store -------------------------------------------------------------------


def test_store_initializes_writes_and_bumps_revisions(tmp_path: Path) -> None:
    store = DocumentStore(tmp_path)
    assert not store.exists
    created = store.initialize(_document())
    assert created.revision == 1
    assert store.exists
    assert store.load().project.package == "demo"

    two = created.updated(
        tables=[_table(), _table("other")],
        sources=[*created.sources, Source(id="other", table="other", location="data/other.json", format="json")],
    )
    staged = store.stage(two)
    assert staged.changed
    committed = store.commit(staged)
    assert committed.revision == 2
    assert DocumentStore(tmp_path).load().revision == 2


def test_identical_content_is_not_a_change(tmp_path: Path) -> None:
    store = DocumentStore(tmp_path)
    created = store.initialize(_document())
    staged = store.stage(created.updated(revision=99))
    assert not staged.changed
    assert store.commit(staged).revision == 1


def test_fingerprint_ignores_revision(tmp_path: Path) -> None:
    document = _document()
    assert content_fingerprint(document) == content_fingerprint(document.updated(revision=77))
    assert content_fingerprint(document) != content_fingerprint(
        document.updated(tables=[_table("changed")])
    )


def test_stale_revision_is_rejected_with_the_current_document(tmp_path: Path) -> None:
    store = DocumentStore(tmp_path)
    created = store.initialize(_document())
    two = created.updated(
        tables=[_table(), _table("two")],
        sources=[*created.sources, Source(id="two", table="two", location="data/two.json", format="json")],
    )
    store.commit(store.stage(two))
    with pytest.raises(RevisionConflict) as conflict:
        store.stage(created.updated(tables=[_table("three")]), expected_revision=1)
    assert conflict.value.actual == 2
    assert [table.id for table in conflict.value.document.tables] == ["sites", "two"]


def test_invalid_document_never_reaches_disk(tmp_path: Path) -> None:
    store = DocumentStore(tmp_path)
    created = store.initialize(_document())
    staged = store.stage(created.updated(sources=[Source(id="s", table="ghost", location="data/x.json", format="json")]))
    with pytest.raises(DocumentInvalid):
        store.commit(staged)
    assert [table.id for table in DocumentStore(tmp_path).load().tables] == ["sites"]


def test_external_edit_is_detected(tmp_path: Path) -> None:
    store = DocumentStore(tmp_path)
    created = store.initialize(_document())
    on_disk = tmp_path / ".kg-studio" / "project.ir.json"
    edited = created.updated(project=Project(name="Renamed", package="demo"))
    on_disk.write_text(edited.model_dump_json(indent=2), encoding="utf-8")
    adopted = store.reload_if_changed()
    assert adopted is not None
    assert adopted.project.name == "Renamed"
    assert store.reload_if_changed() is None


# -- validation --------------------------------------------------------------


def test_a_table_without_a_source_is_reported() -> None:
    issues = validate_document(_document(sources=[]))
    assert any("no physical source" in issue.message for issue in issues)


def test_group_source_requires_a_layout_template() -> None:
    document = _document(
        tables=[
            _table("publications", declaration_name="PublicationsTableGroup", members=[{"python_name": "clinical", "ref": "clinical"}]),
            _table("clinical", declaration_name="ClinicalTable", group="publications"),
        ],
        sources=[Source(id="publications", table="publications", location="data", format="json")],
    )
    issues = validate_document(document)
    assert any("must supply a layout" in issue.message for issue in issues)
    fixed = document.updated(
        sources=[Source(id="publications", table="publications", location="data", format="json", layout="{group_path}/{table_name}.json")]
    )
    assert not [issue for issue in validate_document(fixed) if "layout" in issue.message]


def test_group_member_must_declare_the_same_group() -> None:
    document = _document(
        tables=[
            _table("publications", declaration_name="PublicationsTableGroup", members=[{"python_name": "clinical", "ref": "clinical"}]),
            _table("clinical", declaration_name="ClinicalTable"),
        ],
        sources=[Source(id="publications", table="publications", location="data", format="json", layout="{group_path}/{table_name}.json")],
    )
    assert any("does not declare group" in issue.message for issue in validate_document(document))


def test_binding_target_must_be_concrete_and_kind_matched() -> None:
    components = [
        Component(id="documented", kind="node", tier="category", declaration_name="DocumentedAbstractNode", name="documented",
                  properties=[{"name": "summary", "logical_type": unit("str")}]),
    ]
    binding = Binding(id="broken", kind="node", component="documented",
                      build_key={"kind": "literal", "value": "x", "logical_type": unit("str")})
    issues = validate_document(_document(components=components, bindings=[binding]))
    assert any("not bindable" in issue.message for issue in issues)


def test_unknown_module_is_reported_only_when_the_catalogue_is_supplied() -> None:
    document = _document(modules=[{"id": "invented_module"}])
    assert validate_document(document) == []
    issues = validate_document(document, known_modules={"file"})
    assert any("not a module the backend knows" in issue.message for issue in issues)


# -- naming ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kind", "tier", "name", "expected"),
    [
        ("node", "concrete", "site", "SiteNode"),
        ("node", "category", "documented", "DocumentedAbstractNode"),
        ("node", "template", "provenanced", "ProvenancedNodeTemplate"),
        ("edge", "concrete", "has_unit", "HasUnitEdge"),
        ("edge", "category", "monitored_relation", "MonitoredRelationAbstractEdge"),
        ("edge", "template", "recorded", "RecordedEdgeTemplate"),
    ],
)
def test_component_names_round_trip_through_the_frameworks_suffix_rules(
    kind: str, tier: str, name: str, expected: str
) -> None:
    from kg_build_system._support.naming import declaration_name

    assert component_declaration_name(kind, tier, name) == expected
    # The framework strips the tier suffix back to the document's logical name.
    suffixes = {
        "node": ("AbstractNode", "NodeTemplate", "Node"),
        "edge": ("AbstractEdge", "EdgeTemplate", "Edge"),
    }[kind]
    assert declaration_name(expected, suffixes=suffixes) == name


def test_data_declaration_names_and_snake_case() -> None:
    assert data_declaration_name("table", "readings", group=True) == "ReadingsTableGroup"
    assert data_declaration_name("struct", "premises_contact") == "PremisesContactStruct"
    assert snake("hasUnit") == "has_unit"
    assert snake("HTTPServer2") == "http_server_2"


def test_suggested_ids_never_keep_a_tier_suffix() -> None:
    assert suggest_id("SiteNode", set()) == "site"
    assert suggest_id("ProvenancedNodeTemplate", set()) == "provenanced"
    assert suggest_id("MonitoredRelationAbstractEdge", set()) == "monitored_relation"
    assert suggest_id("site", {"site"}) == "site_2"


# -- plan projection ---------------------------------------------------------

CONTRACT = REPO / "reference_project" / "build" / "workflow_contract.json"


@pytest.mark.skipif(not CONTRACT.is_file(), reason="run reference_project/build.py first")
def test_a_real_workflow_contract_projects_into_a_positioned_graph() -> None:
    from kg_build_system.workflow.ir import WorkflowContractIR

    from studio_backend.plan import project_plan

    contract = WorkflowContractIR.model_validate_json(CONTRACT.read_text(encoding="utf-8"))
    plan = project_plan(contract)

    assert plan["nodes"], "the reference contract has steps"
    assert len(plan["nodes"]) == len(contract.workflow.steps)
    assert all(edge["to_step"] and edge["from_step"] for edge in plan["edges"])
    assert all(edge["from_step"] in {node["id"] for node in plan["nodes"]} for edge in plan["edges"])

    kinds = {node["kind"] for node in plan["nodes"]}
    assert {"table", "binding", "aggregate", "operator", "publish"} <= kinds

    aggregates = [node for node in plan["nodes"] if node["kind"] == "aggregate"]
    assert all(node["component"] and node["component"].startswith("component:") for node in aggregates)

    with_sql = [node for node in plan["nodes"] if node["sql"]]
    assert with_sql, "binding steps carry lowered SQL worth inspecting"
    assert all("SELECT" in (node["sql"] or "").upper() for node in with_sql)

    roles = {module["role"] for module in plan["modules"]}
    assert {"core", "target"} <= roles


@pytest.mark.skipif(not CONTRACT.is_file(), reason="run reference_project/build.py first")
def test_plan_projection_is_deterministic() -> None:
    from kg_build_system.workflow.ir import WorkflowContractIR

    from studio_backend.plan import project_plan

    contract = WorkflowContractIR.model_validate_json(CONTRACT.read_text(encoding="utf-8"))
    first = json.dumps(project_plan(contract), sort_keys=True)
    second = json.dumps(project_plan(contract), sort_keys=True)
    assert first == second
