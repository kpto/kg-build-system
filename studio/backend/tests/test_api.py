"""The HTTP + WebSocket contract, exercised against a real workspace.

These tests pin what ``studio/docs/API.md`` promises: status codes for a stale
revision and a rejected edit, the shapes the frontend depends on, and the event
stream the shell resyncs from. They use the in-process workspace; the compile
passes are covered separately because they shell out to a subprocess.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

import pytest
from fastapi.testclient import TestClient
from studio_backend.api.app import create_app
from studio_backend.ir.document import (
    DataField,
    Module,
    Project,
    ProjectDocument,
    Source,
    Table,
    unit,
)
from studio_backend.ir.store import DocumentStore
from studio_backend.workspace import Workspace

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


def _document(package: str = "demo_project") -> ProjectDocument:
    return ProjectDocument(
        project=Project(name="Demo", package=package),
        tables=[
            Table(
                id="sites",
                declaration_name="SitesTable",
                name="sites",
                fields=[
                    DataField(name="site_id", logical_type=unit("str", nullable=True)),
                    DataField(name="site_name", logical_type=unit("str", nullable=True)),
                ],
            )
        ],
        sources=[
            Source(id="sites", table="sites", location="data/sites.json", format="json")
        ],
    )


@pytest.fixture
def workspace(tmp_path: Path) -> Iterator[Workspace]:
    project_root = tmp_path / "demo"
    project_root.mkdir()
    (project_root / "data").mkdir()
    (project_root / "data" / "sites.json").write_text('[{"site_id": "a"}]', encoding="utf-8")
    # Seed a real document rather than an empty one, so the assertions below describe
    # a project with content instead of a freshly created workspace.
    DocumentStore(project_root).initialize(_document())
    instance = Workspace(project_root, enable_diagnostics=False)
    yield instance
    instance.stop()


@pytest.fixture
def client(workspace: Workspace) -> Iterator[TestClient]:
    with TestClient(create_app(workspace)) as test_client:
        yield test_client


def _put(client: TestClient, document: dict[str, Any], revision: int | None) -> Any:
    return client.put("/api/document", json={"document": document, "revision": revision})


def test_state_reports_the_document_and_status(client: TestClient, workspace: Workspace) -> None:
    body = client.get("/api/state").json()
    assert body["revision"] == 1
    assert body["document"]["project"]["package"] == "demo_project"
    assert set(body["status"]) >= {"revision", "generation", "blueprint", "types", "build", "project_root"}


def test_creating_a_table_round_trips_and_bumps_the_revision(client: TestClient) -> None:
    document = client.get("/api/document").json()["document"]
    document["tables"].append(
        {
            "id": "readings",
            "declaration_name": "ReadingsTable",
            "name": "readings",
            "fields": [{"name": "value", "logical_type": {"kind": "unit", "name": "float"}}],
        }
    )
    document["sources"].append(
        {"id": "readings", "table": "readings", "location": "data/readings.json", "format": "json"}
    )
    response = _put(client, document, revision=1)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["revision"] == 2
    assert {table["id"] for table in body["document"]["tables"]} == {"sites", "readings"}
    assert client.get("/api/document").json()["revision"] == 2


def test_an_editing_noop_is_accepted_without_bumping_the_revision(client: TestClient) -> None:
    """Re-sending the current document is not a change, and must not look like one.

    The frontend coalesces keystrokes, so this path runs constantly; it used to raise
    because the "nothing changed" branch returned an undefined value.
    """
    body = client.get("/api/document").json()
    response = _put(client, body["document"], revision=body["revision"])
    assert response.status_code == 200, response.text
    assert response.json()["revision"] == body["revision"]


def test_a_stale_revision_is_refused_with_the_current_document(client: TestClient) -> None:
    document = client.get("/api/document").json()["document"]
    document["project"]["name"] = "First"
    assert _put(client, document, revision=1).status_code == 200

    stale = dict(document, project={**document["project"], "name": "Second"})
    refused = _put(client, stale, revision=1)
    assert refused.status_code == 409
    body = refused.json()
    assert body["revision"] == 2
    assert body["document"]["project"]["name"] == "First"
    assert "reason" in body


def test_a_dangling_reference_is_rejected_without_writing(client: TestClient) -> None:
    document = client.get("/api/document").json()["document"]
    document["sources"] = [{"id": "s", "table": "ghost", "location": "data/x.json", "format": "json"}]
    response = _put(client, document, revision=1)
    assert response.status_code == 422
    assert "unknown table" in json.dumps(response.json())
    assert client.get("/api/document").json()["revision"] == 1


def test_an_unparseable_body_is_a_schema_error(client: TestClient) -> None:
    document = client.get("/api/document").json()["document"]
    document["tables"][0]["fields"][0]["logical_type"] = {"kind": "wat"}
    response = _put(client, document, revision=1)
    assert response.status_code in (422,)
    assert response.json().get("reason")


def test_the_backend_owns_expression_types(client: TestClient) -> None:
    """A client cannot smuggle a wrong ``logical_type`` into the stored document."""
    document = client.get("/api/document").json()["document"]
    document["tables"][0]["fields"][0]["logical_type"] = {
        "kind": "nullable",
        "value": {"kind": "unit", "name": "int"},
    }
    # Add a projection whose field claims a bogus type for a nullable string column.
    document["projections"] = [
        {
            "id": "site_names",
            "declaration_name": "SiteNameProjection",
            "name": "site_names",
            "fields": [
                {
                    "name": "site_id",
                    "expression": {
                        "kind": "field",
                        "source": "sites",
                        "path": ["site_id"],
                        "logical_type": {"kind": "unit", "name": "bool"},
                    },
                }
            ],
        }
    ]
    body = _put(client, document, revision=1).json()
    stored = body["document"]["projections"][0]["fields"][0]["expression"]["logical_type"]
    assert stored == {"kind": "nullable", "value": {"kind": "unit", "name": "int"}}


def test_the_save_ack_carries_only_the_document_tier(client: TestClient, workspace: Workspace) -> None:
    """The ack cannot speak for the passes still running on the pipeline thread.

    A snapshot of every tier here would be the previous revision's, and a client that
    adopted it would erase the blueprint error its event had just delivered.
    """
    workspace._blueprint_error = {  # noqa: SLF001 - forcing the failed-compile state
        "type": "TypeError",
        "message": "TargetNode.symbol expects UnitType(name='str')",
    }
    workspace.status.blueprint = {"state": "failed", "ok": False, "errors": 1}
    document = client.get("/api/document").json()["document"]
    document["project"] = {**document["project"], "description": "an edit"}

    acknowledged = _put(client, document, revision=document["revision"]).json()
    assert {problem["tier"] for problem in acknowledged["problems"]} <= {"document"}

    # The full set is still where a client goes to read every tier.
    everything = client.get("/api/diagnostics").json()["problems"]
    assert "blueprint" in {problem["tier"] for problem in everything}


def test_a_failing_compile_reports_problems_as_plain_json(client: TestClient, workspace: Workspace) -> None:
    """A blueprint-tier failure must reach the wire as JSON, not as a domain object.

    ``map_blueprint_error`` returns a ``Problem`` mapping; if it leaked into a response
    json.dumps would raise and the UI would see a 500 instead of the error it needs.
    """
    workspace._blueprint_error = {  # noqa: SLF001 - forcing the failed-compile state
        "type": "TypeError",
        "message": "TargetNode.symbol expects UnitType(name='str'), but the expression resolves to NullableType(value=UnitType(name='str'))",
    }
    workspace.status.blueprint = {"state": "failed", "ok": False, "errors": 1}
    response = client.get("/api/diagnostics")
    assert response.status_code == 200
    problems = response.json()["problems"]
    blueprint_problem = next(problem for problem in problems if problem["tier"] == "blueprint")
    assert "TargetNode.symbol expects" in blueprint_problem["message"]
    assert blueprint_problem["severity"] == "error"
    # This minimal project declares no components, so nothing in the message resolves;
    # an unmappable problem still has to appear, with no invented ref.
    assert blueprint_problem["ref"] is None
    assert set(blueprint_problem) >= {
        "id", "tier", "severity", "message", "code", "file", "line", "column", "ref", "ref_trusted", "hint"
    }


def test_the_backend_refuses_an_expression_it_cannot_type(client: TestClient) -> None:
    document = client.get("/api/document").json()["document"]
    document["projections"] = [
        {
            "id": "bad",
            "declaration_name": "BadProjection",
            "name": "bad",
            "fields": [
                {
                    "name": "sum",
                    "expression": {
                        "kind": "operation",
                        "operator": "add",
                        "arguments": [
                            {"kind": "field", "source": "sites", "path": ["site_id"], "logical_type": {"kind": "unit", "name": "str"}}
                        ],
                        "parameters": {},
                        "logical_type": {"kind": "unit", "name": "int"},
                    },
                }
            ],
        }
    ]
    response = _put(client, document, revision=1)
    assert response.status_code == 422
    assert "errors" in response.json()


def test_the_catalogue_describes_the_modules_the_backend_can_run(client: TestClient) -> None:
    body = client.get("/api/catalog").json()
    ids = {module["id"] for module in body["modules"]}
    assert {"file", "meta_graph", "neo4j", "collapse_exact_duplicates"} <= ids
    file_module = next(item for item in body["modules"] if item["id"] == "file")
    assert "relative_path" in file_module["configuration_schema"]["properties"]
    assert "relative_path" in file_module["configuration_schema"]["required"]
    assert {unit["name"] for unit in body["units"]} == {
        "bool", "int", "float", "str", "date", "time", "timestamp", "uuid"
    }
    assert body["targets"] == [{"id": "sites", "label": "sites (table)", "is_group": "false"}]


def test_a_module_with_nothing_to_configure_offers_no_default(client: TestClient) -> None:
    """A configuration schema with no properties presents a null default, not ``{}``.

    The empty object was what the add button seeded into the document, which the
    generator then rendered as an argument-less call to the module's private
    configuration class. With ``default_configuration`` null the frontend stores null
    and the module registers bare; ``configuration_schema`` keeps its empty
    ``properties`` so the UI still knows there is nothing to configure.
    """
    collapse = next(
        item for item in client.get("/api/catalog").json()["modules"]
        if item["id"] == "collapse_exact_duplicates"
    )
    assert collapse["default_configuration"] is None
    schema = collapse["configuration_schema"]
    assert schema["properties"] == {} and schema["type"] == "object"
    # A module that does configure something still offers its defaults.
    meta_graph = next(
        item for item in client.get("/api/catalog").json()["modules"]
        if item["id"] == "meta_graph"
    )
    assert meta_graph["default_configuration"] == {
        "relative_path": "meta_graph.json",
        "example_limit": 3,
        "include_html": True,
        "html_relative_path": "meta_graph.html",
    }


def test_a_refused_module_configuration_is_reported_not_raised(
    client: TestClient, workspace: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A configuration studio cannot render must reach the UI, not kill the pipeline.

    Guard 2 raises ``GenerationError`` while rendering ``build.py``. The pipeline must
    swallow it into ``status.generation`` exactly like every other generation failure —
    the watcher survives and the message reaches ``GET /api/state`` — and it must not
    leave a generated file importing the module's private configuration class.
    """
    import dataclasses

    import kg_build_system.modules as modules_package
    from kg_build_system.modules import Module as WorkflowModule
    from kg_build_system.modules import ModuleRegistrationConfiguration

    @dataclasses.dataclass(frozen=True)
    class _Secret(ModuleRegistrationConfiguration):
        limit: int

    class SecretModule(WorkflowModule):
        ID = "secret"
        VERSION = "1"
        CONFIGURATION_TYPE = _Secret

        @classmethod
        async def create_compiler(cls, context: Any) -> Any: ...

        @classmethod
        def create_executor(cls, context: Any) -> Any: ...

    monkeypatch.setattr(modules_package, "SecretModule", SecretModule, raising=False)
    monkeypatch.setattr(
        modules_package, "__all__", [*modules_package.__all__, "SecretModule"]
    )
    # Make "secret" a known module so it clears the document tier and reaches generation.
    monkeypatch.setattr(workspace, "known_module_ids", lambda: {"file", "secret"})

    document = client.get("/api/document").json()["document"]
    document["modules"] = [{"id": "secret", "configuration": {"limit": 3}, "enabled": True}]
    assert _put(client, document, revision=1).status_code == 200

    workspace._pipeline()  # the pipeline pass the worker thread would run; must not raise

    assert workspace.status.generation["state"] == "failed"
    assert "secret" in workspace.status.generation["error"]
    assert "_Secret" in workspace.status.generation["error"]

    body = client.get("/api/state").json()
    assert body["status"]["generation"]["state"] == "failed"

    build = workspace.project_root / "demo_project" / "build.py"
    assert not build.exists() or "_Secret" not in build.read_text(encoding="utf-8")


def test_the_index_flattens_nested_paths_and_lists_operators(client: TestClient) -> None:
    body = client.get("/api/index").json()
    sites = next(item for item in body["selectable"] if item["id"] == "sites")
    assert [path["path"] for path in sites["paths"]] == [["site_id"], ["site_name"]]
    assert {entry["operator"] for entry in body["operators"]} >= {"where_present", "coalesce", "map_items"}


def test_name_suggestions_strip_the_tier_suffix_and_avoid_collisions(client: TestClient) -> None:
    """``Sites Table`` names the logical ``sites`` — and that one is already taken."""
    taken = client.post("/api/names/suggest", json={"section": "table", "label": "Sites Table"}).json()
    assert taken["id"] == "sites_2"
    assert taken["taken"] is True
    assert taken["declaration_name"] == "SitesTable"
    free = client.post("/api/names/suggest", json={"section": "table", "label": "Readings Table"}).json()
    assert free["id"] == "readings"
    assert free["taken"] is False


def test_data_files_are_discovered_but_never_owned(client: TestClient, workspace: Workspace) -> None:
    body = client.get("/api/data/files").json()
    assert [item["location"] for item in body["files"]] == ["data/sites.json"]


def test_source_lookup_returns_the_generated_file_for_a_ref(client: TestClient, workspace: Workspace) -> None:
    workspace.request("pipeline")
    missing = client.get("/api/source", params={"ref": "component:nope"})
    assert missing.status_code == 404


def test_the_workspace_endpoint_is_idempotent(client: TestClient, workspace: Workspace) -> None:
    created = client.post("/api/workspace", json={"package": "other", "name": "Other"})
    assert created.status_code == 200
    assert created.json()["revision"] == workspace.document.revision


def test_the_socket_greets_with_the_full_state(client: TestClient) -> None:
    with client.websocket_connect("/ws") as socket:
        greeting = socket.receive_json()
        assert greeting["type"] == "hello"
        assert greeting["revision"] == 1
        assert greeting["document"]["project"]["package"] == "demo_project"
        socket.send_json({"type": "resync"})
        assert socket.receive_json()["type"] == "hello"


def test_document_edits_are_broadcast_to_subscribers(client: TestClient) -> None:
    with client.websocket_connect("/ws") as socket:
        assert socket.receive_json()["type"] == "hello"
        document = client.get("/api/document").json()["document"]
        document["project"]["name"] = "Renamed"
        _put(client, document, revision=1)
        seen = []
        for _ in range(6):
            event = socket.receive_json()
            seen.append(event["type"])
            if event["type"] == "document":
                assert event["revision"] == 2
                break
        assert "document" in seen


def test_a_blueprint_problem_is_a_plain_dict_before_it_reaches_the_wire(
    workspace: Workspace,
) -> None:
    """A ``Problem`` mapping is not JSON, and a failed ``send_json`` kills the socket.

    The client would not see an error: the pump task would simply stop delivering, so
    every later event — including the fix the author was waiting for — went unheard.
    """
    problems = workspace.blueprint_problems(
        {
            "type": "TypeError",
            "message": "TargetNode.symbol expects UnitType(name='str'), "
            "but the expression resolves to UnitType(name='bool')",
        }
    )
    assert problems, "the message names a property, so it must resolve to a problem"
    assert all(type(problem) is dict for problem in problems)
    json.dumps({"type": "blueprint", "ok": False, "errors": problems})


def test_one_unserialisable_event_costs_one_message_not_the_socket(
    client: TestClient, workspace: Workspace
) -> None:
    with client.websocket_connect("/ws") as socket:
        assert socket.receive_json()["type"] == "hello"
        workspace.emit("blueprint", ok=False, errors=[object()])
        assert socket.receive_json()["level"] == "error"
        assert socket.receive_json()["type"] == "resync"
        # Still alive: the next well-formed event arrives normally.
        workspace.emit("generation", state="running", changed=[], error=None)
        assert socket.receive_json()["type"] == "generation"
