"""HTTP and WebSocket surface over one workspace.

Thin by design: every route is a translation between the contract in
``studio/docs/API.md`` and a :class:`studio_backend.workspace.Workspace` method. The
workspace owns the pipeline and the threading; this module only marshals.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..catalog import (
    data_files,
    infer_target_options,
    module_catalogue,
    operator_catalogue,
    type_catalogue,
    vocabulary,
)
from ..infer_contract import infer_shape
from ..ir.document import ProjectDocument
from ..ir.names import declaration_name, suggest_id
from ..ir.store import DocumentStore, RevisionConflict
from ..workspace import DocumentRejected, Workspace

_TAKEN_SECTIONS = {
    "table": "tables",
    "struct": "structs",
    "projection": "projections",
    "component": "components",
    "binding": "bindings",
    "source": "sources",
    "annotation_type": "annotation_types",
}


class DocumentPut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision: int | None = None
    document: dict[str, Any]


class WorkspaceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    package: str = Field(min_length=1)
    name: str = Field(min_length=1)
    #: The served workspace is fixed at startup, so this is only checked against it.
    project_root: str | None = None


class NameSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section: str
    label: str
    kind: str = "node"
    tier: str = "concrete"
    group: bool = False


class InferRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    location: str
    mode: str = "table"
    layout: str | None = None
    relation: str | None = None
    override: dict[str, dict[str, Any]] | None = None
    request_id: str | None = None


def create_app(workspace: Workspace) -> FastAPI:
    app = FastAPI(title="KG Studio", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/state")
    def state() -> dict[str, Any]:
        return workspace.state_snapshot()

    @app.get("/api/document")
    def get_document() -> dict[str, Any]:
        document = workspace.document
        return {"revision": document.revision, "document": document.model_dump(mode="json")}

    @app.put("/api/document")
    def put_document(payload: DocumentPut) -> JSONResponse:
        try:
            document = ProjectDocument.model_validate(payload.document)
        except ValidationError as error:
            return JSONResponse(
                status_code=422,
                content={"reason": "the document does not match the IR schema", "errors": error.errors(include_url=False)},
            )
        try:
            committed = workspace.apply_document(document, expected_revision=payload.revision)
        except RevisionConflict as conflict:
            return JSONResponse(
                status_code=409,
                content={
                    "reason": str(conflict),
                    "revision": conflict.actual,
                    "document": conflict.document.model_dump(mode="json"),
                },
            )
        except DocumentRejected as rejected:
            return JSONResponse(
                status_code=422,
                content={"reason": "the change was rejected", "errors": rejected.problems},
            )
        return JSONResponse(
            {
                "revision": committed.revision,
                "document": committed.model_dump(mode="json"),
                # Only the tier this request can answer for. Generation, blueprint and
                # pyright results for the new revision are still being computed on the
                # pipeline thread, so a snapshot here would be the previous revision's
                # and would overwrite what the events already delivered.
                "problems": [
                    problem
                    for problem in workspace.problems()
                    if problem.get("tier") == "document"
                ],
            }
        )

    @app.post("/api/workspace")
    def create_workspace(payload: WorkspaceCreate) -> dict[str, Any]:
        if payload.project_root and Path(payload.project_root).resolve() != workspace.project_root:
            return JSONResponse(
                status_code=422,
                content={
                    "reason": (
                        f"this studio serves {workspace.project_root}, not {payload.project_root}; "
                        "start it with --project pointing at the directory you mean"
                    )
                },
            )
        document = workspace.initialize_project(package=payload.package, name=payload.name)
        return {"revision": document.revision, "document": document.model_dump(mode="json")}

    @app.get("/api/catalog")
    def catalog() -> dict[str, Any]:
        return {
            "modules": [entry.as_json() for entry in module_catalogue()],
            "units": type_catalogue(),
            "operators": operator_catalogue(),
            "vocabulary": vocabulary(),
            "targets": infer_target_options(workspace.document),
        }

    @app.get("/api/index")
    def index() -> dict[str, Any]:
        try:
            return workspace.index()
        except Exception as error:  # noqa: BLE001 - an index failure must not take the tab down
            return {"selectable": [], "components": [], "operators": operator_catalogue(), "error": str(error)}

    @app.get("/api/diagnostics")
    def diagnostics() -> dict[str, Any]:
        return {"problems": workspace.problems(), "pyright": {"state": workspace.diagnostics.state}}

    @app.get("/api/plan")
    def plan(refresh: bool = Query(default=False)) -> dict[str, Any]:
        result = workspace.plan(refresh=refresh)
        # The fingerprint belongs on the envelope as well: the plan node list can be
        # large and the header only needs to know which compile it came from.
        plan_body = result.get("plan") or {}
        return {**result, "fingerprint": plan_body.get("fingerprint") if isinstance(plan_body, dict) else None}

    @app.get("/api/blueprint")
    def blueprint(refresh: bool = Query(default=False)) -> dict[str, Any]:
        return workspace.blueprint(refresh=refresh)

    @app.post("/api/build")
    def run_build() -> dict[str, Any]:
        return workspace.build()

    @app.get("/api/source")
    def source(ref: str = Query(min_length=1)) -> JSONResponse:
        result = workspace.source_for_ref(ref)
        if result is None:
            return JSONResponse(status_code=404, content={"reason": f"nothing generated for {ref!r}"})
        return JSONResponse(result)

    @app.post("/api/names/suggest")
    def names(payload: NameSuggestion) -> dict[str, Any]:
        document = workspace.document
        section = _TAKEN_SECTIONS.get(payload.section)
        if section is None:
            return JSONResponse(status_code=422, content={"reason": f"unknown section {payload.section!r}"})
        existing = {item.id for item in getattr(document, section)}
        desired = suggest_id(payload.label, set())
        identifier = suggest_id(payload.label, existing)
        generated = declaration_name(
            payload.label,
            "component" if payload.section == "component" else payload.section,
            tier=payload.tier,
            kind=payload.kind,
            group=payload.group,
        )
        return {
            "id": identifier,
            "declaration_name": generated,
            "python_name": identifier,
            # Whether the obvious id was already used, so the UI can say
            # "sites exists — this will be sites_2" rather than silently renaming.
            "taken": desired in existing,
        }

    @app.get("/api/data/files")
    def files() -> dict[str, Any]:
        return {"files": data_files(workspace.document, workspace.project_root)}

    @app.post("/api/infer")
    async def infer(payload: InferRequest) -> JSONResponse:
        document = workspace.document
        try:
            shape = await infer_shape(
                project_root=workspace.project_root,
                package=document.project.package,
                location=payload.location,
                mode=payload.mode,
                layout=payload.layout,
                relation=payload.relation,
                override=payload.override,
                request_id=payload.request_id,
            )
        except Exception as error:  # noqa: BLE001 - inference reads arbitrary user data
            return JSONResponse(status_code=422, content={"reason": f"could not infer a contract: {error}"})
        return JSONResponse(
            {
                "tables": [table.model_dump(mode="json") for table in shape.tables],
                "structs": [struct.model_dump(mode="json") for struct in shape.structs],
                "sources": [source.model_dump(mode="json") for source in shape.sources],
                "notes": list(shape.notes),
            }
        )

    @app.websocket("/ws")
    async def socket(websocket: WebSocket) -> None:
        await websocket.accept()
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=256)
        loop = asyncio.get_running_loop()

        def deliver(event: dict[str, Any]) -> None:
            def offer() -> None:
                if queue.full():
                    # A client that cannot keep up is told to resync rather than being
                    # fed an unbounded backlog or silently dropped: it can rebuild the
                    # whole state from /api/state, and a stale subscription is worse
                    # than a visible gap.
                    queue.get_nowait()
                    queue.put_nowait({"type": "resync"})
                queue.put_nowait(event)

            loop.call_soon_threadsafe(offer)

        unsubscribe = workspace.subscribe(deliver)

        async def pump() -> None:
            while True:
                event = await queue.get()
                try:
                    await websocket.send_json(event)
                except (TypeError, ValueError) as error:
                    # One unserialisable payload must not kill the socket: a dead pump is
                    # invisible to the UI, which would keep showing a stale, quiet world.
                    kind = event.get("type")
                    await websocket.send_json(
                        {
                            "type": "log",
                            "level": "error",
                            "text": f"dropped the {kind} event: {error}",
                        }
                    )
                    await websocket.send_json({"type": "resync"})

        pumping = asyncio.create_task(pump())
        try:
            await websocket.send_json({"type": "hello", **workspace.state_snapshot()})
            while True:
                message = await websocket.receive_text()
                if not message:
                    continue
                try:
                    request = json.loads(message)
                except json.JSONDecodeError:
                    continue
                kind = request.get("type")
                if kind == "resync":
                    await websocket.send_json({"type": "hello", **workspace.state_snapshot()})
                elif kind == "refresh":
                    workspace.request("pipeline")
        except WebSocketDisconnect:
            pass
        finally:
            pumping.cancel()
            unsubscribe()

    return app
