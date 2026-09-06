/**
 * The document store: the single place the UI's copy of `project.ir.json` lives.
 *
 * Concurrency per API.md: edits are applied locally (optimistic) and the whole
 * document is `PUT` with the revision it last saw. `200` adopts the server's
 * document + revision; `409` adopts the server's document and tells the user
 * someone else changed the project — the document plus its revision *is* the merge
 * strategy, so there is nothing to reconcile beyond adopting.
 *
 * Edits coalesce into one request per `COALESCE_MS` window, which is what keeps
 * dragging a slider or typing in a field from thrashing the server and the
 * regeneration queue behind it.
 */

import { create } from "zustand";

import { api, ApiError } from "@/lib/api";
import { emptyDocument } from "@/lib/ir";
import type { ProjectDocument } from "@/lib/ir";
import type {
  FieldError,
  Problem,
  PutDocumentRequest,
  PutDocumentResponse,
  StatusModel,
} from "@/lib/types";
import { notify, useConnectionStore } from "./connectionStore";
import { useProblemStore } from "./problemStore";

/** Coalescing window for outgoing `PUT`s. */
export const COALESCE_MS = 250;
/** Undo history depth; documents are small and this bounds memory. */
export const HISTORY_LIMIT = 100;

export type PutTransport = (request: PutDocumentRequest) => Promise<PutDocumentResponse>;

export interface DocumentState {
  document: ProjectDocument | null;
  revision: number;
  /** A local edit exists that the server has not acknowledged. */
  dirty: boolean;
  /** A `PUT` is in flight. */
  sending: boolean;
  loading: boolean;
  /** `?mock=1`: edits are acknowledged locally instead of over HTTP. */
  mock: boolean;
  /** The last failed write: `{reason, errors}` from `422`/network. */
  error: { reason: string; errors: FieldError[] } | null;
  /** Documents the user can step back through. */
  past: ProjectDocument[];
  future: ProjectDocument[];

  reset(document?: ProjectDocument | null): void;
  setMock(mock: boolean): void;
  setLoading(loading: boolean): void;
  /** Adopt a whole state from `GET /api/state` (initial load and every resync). */
  adoptState(payload: { document: ProjectDocument; revision: number; status?: StatusModel }): void;
  /** Adopt a `document` WS event; `origin: "self"` is our own write echoed back. */
  adoptRemote(payload: { document?: ProjectDocument; revision?: number; origin?: "remote" | "self" }): void;
  /** A workspace with no project yet: an editable empty IR. */
  startEmpty(name?: string, pkg?: string): void;

  apply(mutate: (draft: ProjectDocument) => ProjectDocument): void;
  undo(): void;
  redo(): void;
  /** Force any coalesced edit out now (Save affordance, unload, key handler). */
  flush(): Promise<void>;
}

/** Replace the outgoing write path — used by mock mode and by tests. */
let put: PutTransport = (request) => api.putDocument(request);

export function setPutTransport(next: PutTransport | null): void {
  put = next ?? ((request) => api.putDocument(request));
}

let timer: ReturnType<typeof setTimeout> | null = null;
let inFlight = false;
/** Set when a write is requested while one is already in flight. */
let queued = false;

function clearTimer(): void {
  if (timer) {
    clearTimeout(timer);
    timer = null;
  }
}

function schedule(): void {
  if (timer) return;
  timer = setTimeout(() => {
    timer = null;
    void useDocumentStore.getState().flush();
  }, COALESCE_MS);
}

function collectErrors(error: unknown): { reason: string; errors: FieldError[] } {
  if (error instanceof ApiError) {
    return { reason: error.reason, errors: error.errors };
  }
  return { reason: error instanceof Error ? error.message : String(error), errors: [] };
}

export const useDocumentStore = create<DocumentState>((set, get) => ({
  document: null,
  revision: 0,
  dirty: false,
  sending: false,
  loading: false,
  mock: false,
  error: null,
  past: [],
  future: [],

  reset(document = null) {
    clearTimer();
    inFlight = false;
    queued = false;
    set({
      document,
      revision: document?.revision ?? 0,
      dirty: false,
      sending: false,
      loading: false,
      error: null,
      past: [],
      future: [],
    });
  },

  setMock(mock) {
    set({ mock });
  },

  setLoading(loading) {
    set({ loading });
  },

  adoptState({ document, revision, status }) {
    clearTimer();
    inFlight = false;
    queued = false;
    set({ document, revision, dirty: false, sending: false, error: null });
    useConnectionStore.getState().setStatus(status ?? null);
  },

  adoptRemote({ document, revision, origin }) {
    // Our own write echoed back is already represented by the acknowledged state.
    if (origin === "self" && !get().dirty) return;
    if (!document) return;
    const previous = get().document;
    set((state) => ({
      document,
      revision: revision ?? document.revision ?? state.revision,
      dirty: false,
      // A remote change is worth being able to step back over.
      past: previous ? [...state.past, previous].slice(-HISTORY_LIMIT) : state.past,
      future: [],
    }));
  },

  startEmpty(name = "project", pkg = "kg_project") {
    get().reset(emptyDocument(name, pkg));
  },

  apply(mutate) {
    const state = get();
    if (!state.document) return;
    const next = mutate(state.document);
    if (next === state.document) return;
    set({
      document: next,
      dirty: true,
      past: [...state.past, state.document].slice(-HISTORY_LIMIT),
      future: [],
    });
    schedule();
  },

  undo() {
    const state = get();
    const previous = state.past[state.past.length - 1];
    if (!previous || !state.document) return;
    set({
      document: previous,
      dirty: true,
      past: state.past.slice(0, -1),
      future: [state.document, ...state.future].slice(0, HISTORY_LIMIT),
    });
    schedule();
  },

  redo() {
    const state = get();
    const next = state.future[0];
    if (!next || !state.document) return;
    set({
      document: next,
      dirty: true,
      past: [...state.past, state.document].slice(-HISTORY_LIMIT),
      future: state.future.slice(1),
    });
    schedule();
  },

  async flush() {
    clearTimer();
    if (inFlight) {
      queued = true;
      return;
    }
    const store = get();
    if (!store.document || !store.dirty) return;

    // The exact document/revision pair that goes on the wire: reconciliation below
    // compares identity, so a newer local edit is never mistaken for acknowledged.
    const document = store.document;
    const baseRevision = store.revision;
    inFlight = true;
    set({ sending: true });

    let response: PutDocumentResponse | null = null;
    try {
      response = store.mock
        ? // Mock mode runs the same control flow, revision bump included, so the
          // optimistic path under ?mock=1 is the real path being exercised.
          { revision: baseRevision + 1, document: { ...document, revision: baseRevision + 1 } }
        : await put({ revision: baseRevision, document });
    } catch (error) {
      inFlight = false;
      if (error instanceof ApiError && error.conflict) {
        // Adopt the winner and say why the local write disappeared.
        set({
          document: error.document ?? null,
          revision: error.revision ?? error.document?.revision ?? baseRevision,
          sending: false,
          dirty: false,
          error: null,
        });
        notify({
          level: "warn",
          text: error.reason || "Someone else changed the project — their version is now shown.",
        });
      } else {
        const failure = collectErrors(error);
        set({ sending: false, error: failure });
        notify({ level: "error", text: `Could not save: ${failure.reason}` });
      }
      if (queued) {
        queued = false;
        schedule();
      }
      return;
    }

    inFlight = false;
    const current = get();
    const acknowledged = current.document === document;
    set({
      document: acknowledged ? response.document : current.document,
      revision: response.revision,
      sending: false,
      dirty: !acknowledged,
      error: null,
    });
    const problems: readonly Problem[] | undefined = response.problems;
    // The ack carries only the document tier; the other tiers arrive on their own
    // events and replacing the whole list here would wipe a pass that already spoke.
    if (problems) useProblemStore.getState().setTierProblems(["document"], problems);
    if (!acknowledged || queued) {
      queued = false;
      schedule();
    }
  },
}));

/* ---------------------------------------------------------------------- selectors */

export const selectDocument = (state: DocumentState): ProjectDocument | null => state.document;
export const selectRevision = (state: DocumentState): number => state.revision;
export const selectCanUndo = (state: DocumentState): boolean => state.past.length > 0;
export const selectCanRedo = (state: DocumentState): boolean => state.future.length > 0;

/** Immediate write, e.g. from a Save affordance or before teardown. */
export function flushDocument(): void {
  void useDocumentStore.getState().flush();
}
