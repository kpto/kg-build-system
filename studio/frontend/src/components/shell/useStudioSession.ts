"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { api, ApiError, BACKEND_ORIGIN } from "@/lib/api";
import { connect } from "@/lib/ws";
import type { StudioSocket } from "@/lib/ws";
import {
  MOCK_CATALOG,
  MOCK_DATA_FILES,
  MOCK_INDEX,
  MOCK_PROBLEMS,
  MOCK_STATUS,
  SAMPLE_DOCUMENT,
} from "@/lib/mock";
import type { WorkspaceRequest } from "@/lib/types";
import { useCatalogStore } from "@/stores/catalogStore";
import { useConnectionStore } from "@/stores/connectionStore";
import { useDocumentStore } from "@/stores/documentStore";
import { useIndexStore } from "@/stores/indexStore";
import { useProblemStore } from "@/stores/problemStore";

/** `?mock=1` — read off the URL rather than `useSearchParams`, which would force a Suspense boundary. */
export function mockModeRequested(): boolean {
  if (typeof window === "undefined") return false;
  return new URLSearchParams(window.location.search).get("mock") === "1";
}

export interface StudioSession {
  /** Tri-state: `null` while loading, `false`/`true` once known. */
  mock: boolean | null;
  ready: boolean;
  /** A fatal load failure (no backend, no workspace); the shell offers a fix. */
  error: string | null;
  reload(): void;
  createProject(request: WorkspaceRequest): Promise<void>;
  /** Force regeneration/plan refresh requests. */
  refreshPlan(): void;
}

/**
 * Owns everything that talks to the backend: initial state, the event socket, the
 * catalogue/index/diagnostics caches. Feature areas never fetch — they read stores.
 */
export function useStudioSession(): StudioSession {
  const [mock, setMock] = useState<boolean | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);
  const socket = useRef<StudioSocket | null>(null);

  const mockLoaded = useRef(false);
  const loadMock = useCallback(() => {
    // StrictMode mounts the effect twice; the notice below would otherwise appear twice.
    if (mockLoaded.current) return;
    mockLoaded.current = true;
    setMock(true);
    const document = useDocumentStore.getState();
    document.reset(SAMPLE_DOCUMENT);
    document.setMock(true);
    useProblemStore.getState().setProblems(MOCK_PROBLEMS);
    useCatalogStore.getState().hydrate(MOCK_CATALOG);
    useIndexStore.getState().hydrate(MOCK_INDEX, SAMPLE_DOCUMENT.revision);
    const connection = useConnectionStore.getState();
    connection.setStatus(MOCK_STATUS);
    connection.setSocket("off");
    connection.notice({
      level: "info",
      text: "Mock project loaded — edits are acknowledged locally and never sent.",
    });
    setReady(true);
    setError(null);
  }, []);

  useEffect(() => {
    if (mockModeRequested()) {
      loadMock();
      return;
    }
    setMock(false);

    let disposed = false;
    const document = useDocumentStore.getState();
    document.setLoading(true);

    const applyState = (state: Awaited<ReturnType<typeof api.getState>>) => {
      if (disposed) return;
      useDocumentStore.getState().adoptState({
        document: state.document,
        revision: state.revision,
        status: state.status,
      });
    };

    void api
      .getState()
      .then((state) => {
        if (disposed) return;
        applyState(state);
        setError(null);
      })
      .catch((cause: unknown) => {
        if (disposed) return;
        const reason =
          cause instanceof ApiError ? cause.reason : cause instanceof Error ? cause.message : String(cause);
        setError(reason);
      })
      .finally(() => {
        if (disposed) return;
        useDocumentStore.getState().setLoading(false);
        setReady(true);
      });

    void useCatalogStore.getState().refresh();
    void useIndexStore.getState().refresh();
    void api
      .getDiagnostics()
      .then((diagnostics) => {
        if (disposed) return;
        useProblemStore.getState().setProblems(diagnostics.problems ?? []);
        useProblemStore.getState().setPyright(diagnostics.pyright ?? null);
      })
      .catch(() => {
        // Diagnostics are optional: pyright may still be starting.
      });

    // The socket resyncs through `GET /api/state` on every (re)connect, which is
    // what guarantees a dropped socket cannot leave a stale revision behind.
    socket.current = connect({
      onResync: (state) => {
        if (disposed || !state.document) return;
        useDocumentStore
          .getState()
          .adoptState({ document: state.document, revision: state.revision ?? 0, status: state.status });
      },
      onEvent: (event) => {
        if (disposed) return;
        const connection = useConnectionStore.getState();
        switch (event.type) {
          case "socket":
            connection.setSocket(event.state === "error" ? "error" : event.state);
            break;
          case "resync":
            connection.noteEvent("hello");
            break;
          case "hello":
            connection.noteEvent("hello");
            if (event.status) connection.setStatus(event.status);
            break;
          case "document":
            connection.noteEvent("document");
            useDocumentStore
              .getState()
              .adoptRemote({ document: event.document, revision: event.revision, origin: event.origin });
            useIndexStore.getState().invalidate();
            break;
          case "generation":
            connection.noteEvent("generation");
            connection.setGeneration(event.state);
            if (event.state === "failed" && event.error) {
              connection.notice({ level: "error", text: `Generation failed: ${event.error}` });
            }
            break;
          case "diagnostics":
            connection.noteEvent("diagnostics");
            useProblemStore.getState().setProblems(event.problems ?? []);
            useProblemStore.getState().setPyright(event.pyright ?? null);
            break;
          case "blueprint":
            connection.noteEvent("blueprint");
            connection.setStatus({
              ...(connection.status ?? {}),
              blueprint: { ok: event.ok ?? true, errors: (event.errors ?? []).length },
            });
            // The pass owns its tier outright: a clean pass must clear the old errors.
            useProblemStore.getState().setTierProblems(["blueprint"], event.errors ?? []);
            break;
          case "plan":
            connection.noteEvent("plan");
            break;
          case "build":
            connection.noteEvent("build");
            connection.setStatus({ ...(connection.status ?? {}), build: { state: event.state } });
            useProblemStore.getState().setTierProblems(["build"], event.problems ?? []);
            break;
          case "log":
            connection.noteEvent("log");
            if (event.level === "error" || event.level === "warn") {
              connection.notice({
                level: event.level === "error" ? "error" : "warn",
                text: event.text ?? "",
              });
            }
            break;
          case "unknown":
            connection.noteEvent("unknown", event.name);
            break;
        }
      },
    });

    return () => {
      disposed = true;
      socket.current?.close();
      socket.current = null;
    };
  }, [loadMock, nonce]);

  // Index follows the document revision: it is derived, so a new revision means a
  // new index. Mock mode already hydrated one.
  const revision = useDocumentStore((state) => state.revision);
  const isMock = useDocumentStore((state) => state.mock);
  useEffect(() => {
    if (isMock || !revision) return;
    useIndexStore.getState().onRevisionChange(revision);
  }, [revision, isMock]);

  const createProject = useCallback(async (request: WorkspaceRequest) => {
    const response = await api.createWorkspace(request);
    useDocumentStore.getState().adoptState({ document: response.document, revision: response.revision });
    setError(null);
    useConnectionStore
      .getState()
      .notice({ level: "info", text: `Project ${request.name} created at ${request.project_root}.` });
    void useCatalogStore.getState().refresh();
    useIndexStore.getState().invalidate();
  }, []);

  const refreshPlan = useCallback(() => {
    void api
      .getPlan(true)
      .then((response) => {
        if (response.errors?.length) useProblemStore.getState().mergeProblems(response.errors);
      })
      .catch(() => undefined);
  }, []);

  return {
    mock,
    ready,
    error,
    reload: () => setNonce((value) => value + 1),
    createProject,
    refreshPlan,
  };
}

/** The backend origin, shown in the disconnected state so the fix is obvious. */
export const backendOrigin = BACKEND_ORIGIN;

/** Data files for the sources picker; live fetch with the mock list as its fallback. */
export async function loadDataFiles(mock: boolean) {
  if (mock) return MOCK_DATA_FILES;
  return api.dataFiles();
}
