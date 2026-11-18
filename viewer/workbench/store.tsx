"use client";

/**
 * Workbench state and persistence.
 *
 * One state value owns the loaded snapshot, one global panel geometry, one
 * global editor-tab strip, and the view history behind back and forward. The
 * history stores documents, not tab ids, so a closed view can be reopened. The
 * geometry is never per document: switching document changes content, not the
 * shape of the workbench.
 */

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  useState,
  type ReactNode,
} from "react";

import type { ViewerIndex, ViewerSnapshot } from "@/lib/types";

import { documentSignature, selectionSignature } from "./types";
import type {
  OpenTabInput,
  SubjectKind,
  WorkbenchActions,
  WorkbenchDocument,
  WorkbenchLayout,
  SubjectSelection,
  WorkbenchState,
  WorkbenchTab,
  activeDocument,
  documentTitle,
  subjectTitle,
} from "./types";
import {
  DEFAULT_LAYOUT,
  MAX_SIDEBAR,
  MAX_SIDEBAR_SPLIT,
  MIN_SIDEBAR,
  MIN_SIDEBAR_SPLIT,
} from "./types";

export const WORKBENCH_STORAGE_PREFIX = "kg-workbench:v2";

const SUBJECT_KINDS = new Set<SubjectKind>([
  "asset",
  "relation",
  "projection",
  "field",
  "node",
  "edge",
  "property",
  "binding",
  "step",
  "collection",
]);

const DETAIL_LEVELS = new Set(["property", "node", "edge", "abstract", "asset"]);

const GRAPH_TAB_ID = "graph";
const WORKFLOW_TAB_ID = "workflow";

/** The one persisted value for a snapshot: its workbench geometry. */
export function workbenchStorageKey(snapshotName: string): string {
  return `${WORKBENCH_STORAGE_PREFIX}:${snapshotName}:layout`;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function numberOr(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function normalizeLayout(value: unknown): WorkbenchLayout {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return { ...DEFAULT_LAYOUT };
  }
  const candidate = value as Record<string, unknown>;
  return {
    sidebarWidth: clamp(
      numberOr(candidate.sidebarWidth, DEFAULT_LAYOUT.sidebarWidth),
      MIN_SIDEBAR,
      MAX_SIDEBAR,
    ),
    sidebarSplit: clamp(
      numberOr(candidate.sidebarSplit, DEFAULT_LAYOUT.sidebarSplit),
      MIN_SIDEBAR_SPLIT,
      MAX_SIDEBAR_SPLIT,
    ),
  };
}

function readLayout(snapshotName: string): WorkbenchLayout {
  if (typeof window === "undefined") return normalizeLayout(undefined);
  try {
    const raw = window.localStorage.getItem(workbenchStorageKey(snapshotName));
    return raw ? normalizeLayout(JSON.parse(raw)) : normalizeLayout(undefined);
  } catch {
    return normalizeLayout(undefined);
  }
}

function writeLayout(snapshotName: string, layout: WorkbenchLayout): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      workbenchStorageKey(snapshotName),
      JSON.stringify(layout),
    );
  } catch {
    // A browser may refuse storage. The workbench still works in memory.
  }
}

function normalizeSelection(value: unknown): SubjectSelection | undefined {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return undefined;
  }
  const candidate = value as Record<string, unknown>;
  const selection: SubjectSelection = {};

  if (
    typeof candidate.kind === "string" &&
    SUBJECT_KINDS.has(candidate.kind as SubjectKind)
  ) {
    selection.kind = candidate.kind as SubjectKind;
  }
  for (const field of ["name", "component", "property"] as const) {
    if (typeof candidate[field] === "string") selection[field] = candidate[field];
  }
  if (typeof candidate.collection === "string") {
    selection.collection = candidate.collection as SubjectSelection["collection"];
  }
  if (candidate.abstract === true) selection.abstract = true;
  if (
    typeof candidate.level === "string" &&
    DETAIL_LEVELS.has(candidate.level)
  ) {
    selection.level = candidate.level as SubjectSelection["level"];
  }
  if (
    typeof candidate.bindingIndex === "number" &&
    Number.isInteger(candidate.bindingIndex) &&
    candidate.bindingIndex >= 0
  ) {
    selection.bindingIndex = candidate.bindingIndex;
  }
  if (
    Array.isArray(candidate.stepId) &&
    candidate.stepId.length >= 2 &&
    typeof candidate.stepId[0] === "string" &&
    typeof candidate.stepId[1] === "string"
  ) {
    selection.stepId = [candidate.stepId[0], candidate.stepId[1]];
  }
  return selection;
}

function subjectId(selection: SubjectSelection): string {
  return `document:${selectionSignature(selection)}`;
}

function previewId(selection: SubjectSelection): string {
  return `preview:${selectionSignature(selection)}`;
}

function graphTab(): WorkbenchTab {
  return { id: GRAPH_TAB_ID, document: { kind: "graph" }, pinned: true };
}

function workflowTab(): WorkbenchTab {
  return { id: WORKFLOW_TAB_ID, document: { kind: "workflow" }, pinned: true };
}

export function createWorkbenchState(
  snapshot: ViewerSnapshot,
  index: ViewerIndex,
): WorkbenchState {
  const graph = graphTab();
  const workflow = workflowTab();
  return {
    snapshot,
    index,
    layout: normalizeLayout(undefined),
    tabs: [graph, workflow],
    activeTabId: graph.id,
    history: [graph.document],
    historyIndex: 0,
  };
}

function pushHistory(
  state: WorkbenchState,
  document: WorkbenchDocument,
): Pick<WorkbenchState, "history" | "historyIndex"> {
  const history = state.history.slice(0, state.historyIndex + 1);
  const signature = documentSignature(document);
  if (
    !history.length ||
    documentSignature(history[history.length - 1]) !== signature
  ) {
    history.push(document);
  }
  return { history, historyIndex: history.length - 1 };
}

function activate(
  state: WorkbenchState,
  tabIdValue: string,
  record = true,
): WorkbenchState {
  const tab = state.tabs.find((candidate) => candidate.id === tabIdValue);
  if (!tab) return state;
  return {
    ...state,
    activeTabId: tab.id,
    ...(record ? pushHistory(state, tab.document) : {}),
  };
}

function tabForDocument(
  document: WorkbenchDocument,
  preview = false,
): WorkbenchTab {
  if (document.kind === "graph") return graphTab();
  if (document.kind === "workflow") return workflowTab();
  return {
    id: preview ? previewId(document.selection) : subjectId(document.selection),
    document,
    ...(preview ? { preview: true } : {}),
  };
}

function appendTab(
  state: WorkbenchState,
  input: OpenTabInput,
): WorkbenchState {
  const selection = normalizeSelection(input.selection);
  if (!selection || !selection.kind) return state;
  const signature = selectionSignature(selection);
  // A background open is always permanent and never takes the visible preview
  // slot; it appends the tab without changing the active view.
  const preview = Boolean(input.preview) && !input.background;
  const existing = state.tabs.find(
    (tab) =>
      tab.document.kind === "subject" &&
      selectionSignature(tab.document.selection) === signature,
  );
  if (existing) {
    // Opening a subject explicitly promotes a preview tab to permanent.
    const tabs =
      !preview && existing.preview
        ? state.tabs.map((tab) =>
            tab.id === existing.id ? { ...tab, preview: undefined } : tab,
          )
        : state.tabs;
    if (input.background) {
      return tabs === state.tabs ? state : { ...state, tabs };
    }
    return activate({ ...state, tabs }, existing.id);
  }

  if (preview) {
    const previewTab = state.tabs.find((tab) => tab.preview && !tab.pinned);
    if (previewTab) {
      // Reuse one preview tab, like a browser or VS Code. The id tracks the
      // shown selection so a later permanent document cannot collide with it.
      const nextId = previewId(selection);
      const document: WorkbenchDocument = { kind: "subject", selection };
      const tabs = state.tabs.map((tab) =>
        tab.id === previewTab.id
          ? { ...tab, id: nextId, document }
          : tab,
      );
      const activeTabId =
        state.activeTabId === previewTab.id ? nextId : state.activeTabId;
      return activate({ ...state, tabs, activeTabId }, nextId);
    }
  }

  const tab = tabForDocument({ kind: "subject", selection }, preview);
  const tabs = [...state.tabs, tab];
  if (input.background) return { ...state, tabs };
  return activate({ ...state, tabs }, tab.id);
}

/**
 * Activate one history view. The view is a document, not a tab: when its tab
 * was closed, reopen it in the reusable preview slot, not as a permanent tab.
 * The history index moves to the view without recording a new navigation.
 */
function restoreView(state: WorkbenchState, index: number): WorkbenchState {
  const document = state.history[index];
  if (!document) return state;
  const signature = documentSignature(document);
  const existing = state.tabs.find(
    (tab) => documentSignature(tab.document) === signature,
  );
  if (existing) {
    return { ...state, activeTabId: existing.id, historyIndex: index };
  }
  if (document.kind === "subject") {
    const previewTab = state.tabs.find((tab) => tab.preview && !tab.pinned);
    if (previewTab) {
      const nextId = previewId(document.selection);
      const tabs = state.tabs.map((tab) =>
        tab.id === previewTab.id
          ? { ...tab, id: nextId, document }
          : tab,
      );
      return {
        ...state,
        tabs,
        activeTabId: nextId,
        historyIndex: index,
      };
    }
    const tab = tabForDocument(document, true);
    return {
      ...state,
      tabs: [...state.tabs, tab],
      activeTabId: tab.id,
      historyIndex: index,
    };
  }
  const tab = tabForDocument(document);
  return {
    ...state,
    tabs: [...state.tabs, tab],
    activeTabId: tab.id,
    historyIndex: index,
  };
}

function nextActiveAfterClose(
  state: WorkbenchState,
  closedId: string,
): WorkbenchTab | undefined {
  const index = state.tabs.findIndex((tab) => tab.id === closedId);
  if (index < 0) return state.tabs.find((tab) => tab.id === state.activeTabId);
  const remaining = state.tabs.filter((tab) => tab.id !== closedId);
  return remaining[Math.min(index, remaining.length - 1)] ?? remaining[0];
}

export type WorkbenchAction =
  | { type: "hydrate"; layout: WorkbenchLayout }
  | { type: "set-selection"; selection: SubjectSelection }
  | { type: "inspect"; selection: SubjectSelection | undefined }
  | { type: "set-layout"; patch: Partial<WorkbenchLayout> }
  | { type: "open-tab"; input: OpenTabInput }
  | { type: "show-graph"; selection: SubjectSelection }
  | { type: "show-workflow" }
  | { type: "pin-tab"; tabId: string }
  | { type: "close-tab"; tabId: string }
  | { type: "activate-tab"; tabId: string }
  | { type: "back" }
  | { type: "forward" };

export function workbenchReducer(
  state: WorkbenchState,
  action: WorkbenchAction,
): WorkbenchState {
  switch (action.type) {
    case "hydrate":
      return { ...state, layout: action.layout };

    case "set-selection": {
      const tab = state.tabs.find((candidate) => candidate.id === state.activeTabId);
      if (!tab) return state;
      const selection = normalizeSelection(action.selection);
      if (!selection) return state;
      if (tab.document.kind === "graph") {
        return { ...state, inspection: selection };
      }
      if (tab.document.kind === "workflow") return state;
      const document: WorkbenchDocument = { kind: "subject", selection };
      const history = state.history.slice();
      if (history[state.historyIndex]) {
        history[state.historyIndex] = document;
      } else {
        history.push(document);
      }
      return {
        ...state,
        tabs: state.tabs.map((candidate) =>
          candidate.id === tab.id ? { ...candidate, document } : candidate,
        ),
        history,
        historyIndex: history.length - 1,
      };
    }

    case "inspect":
      return { ...state, inspection: normalizeSelection(action.selection) };

    case "set-layout":
      return {
        ...state,
        layout: {
          ...state.layout,
          sidebarWidth: clamp(
            numberOr(action.patch.sidebarWidth, state.layout.sidebarWidth),
            MIN_SIDEBAR,
            MAX_SIDEBAR,
          ),
          sidebarSplit: clamp(
            numberOr(action.patch.sidebarSplit, state.layout.sidebarSplit),
            MIN_SIDEBAR_SPLIT,
            MAX_SIDEBAR_SPLIT,
          ),
        },
      };

    case "open-tab":
      return appendTab(state, action.input);

    case "show-graph": {
      const graphTab = state.tabs.find((tab) => tab.document.kind === "graph");
      if (!graphTab) return state;
      const selection = normalizeSelection(action.selection);
      const next = activate(state, graphTab.id);
      return selection ? { ...next, inspection: selection } : next;
    }

    case "show-workflow": {
      const workflowTab = state.tabs.find(
        (tab) => tab.document.kind === "workflow",
      );
      return workflowTab ? activate(state, workflowTab.id) : state;
    }

    case "pin-tab":
      return {
        ...state,
        tabs: state.tabs.map((tab) =>
          tab.id === action.tabId ? { ...tab, preview: undefined } : tab,
        ),
      };

    case "close-tab": {
      const tab = state.tabs.find((candidate) => candidate.id === action.tabId);
      if (!tab || tab.pinned) return state;
      const remaining = state.tabs.filter(
        (candidate) => candidate.id !== action.tabId,
      );
      if (!remaining.length) return state;
      const nextActive = nextActiveAfterClose(state, action.tabId);
      if (!nextActive) return state;
      if (nextActive.id === state.activeTabId) {
        // A closed background tab did not change the current view. Its view
        // stays in history, so Back or Forward can reopen it.
        return { ...state, tabs: remaining };
      }
      const next = { ...state, tabs: remaining, activeTabId: nextActive.id };
      return { ...next, ...pushHistory(next, nextActive.document) };
    }

    case "activate-tab":
      return activate(state, action.tabId);

    case "back":
      return state.historyIndex > 0
        ? restoreView(state, state.historyIndex - 1)
        : state;

    case "forward":
      return state.historyIndex < state.history.length - 1
        ? restoreView(state, state.historyIndex + 1)
        : state;

    default:
      return state;
  }
}

interface WorkbenchContextValue {
  state: WorkbenchState;
  actions: WorkbenchActions;
}

const WorkbenchContext = createContext<WorkbenchContextValue | null>(null);

export interface WorkbenchProviderProps {
  snapshot: ViewerSnapshot;
  index: ViewerIndex;
  children: ReactNode;
}

export function WorkbenchProvider({
  snapshot,
  index,
  children,
}: WorkbenchProviderProps) {
  const [state, dispatch] = useReducer(workbenchReducer, undefined, () =>
    createWorkbenchState(snapshot, index),
  );
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    dispatch({ type: "hydrate", layout: readLayout(snapshot.name) });
    setHydrated(true);
  }, [snapshot.name]);

  useEffect(() => {
    if (!hydrated) return;
    writeLayout(snapshot.name, state.layout);
  }, [hydrated, snapshot.name, state.layout]);

  const actions = useMemo<WorkbenchActions>(
    () => ({
      setSelection: (selection) =>
        dispatch({ type: "set-selection", selection }),
      inspect: (selection) => dispatch({ type: "inspect", selection }),
      setLayout: (patch) => dispatch({ type: "set-layout", patch }),
      openTab: (input) => dispatch({ type: "open-tab", input }),
      showGraph: (selection) => dispatch({ type: "show-graph", selection }),
      showWorkflow: () => dispatch({ type: "show-workflow" }),
      pinTab: (tabId) => dispatch({ type: "pin-tab", tabId }),
      closeTab: (tabId) => dispatch({ type: "close-tab", tabId }),
      activateTab: (tabId) => dispatch({ type: "activate-tab", tabId }),
      back: () => dispatch({ type: "back" }),
      forward: () => dispatch({ type: "forward" }),
    }),
    [],
  );

  const value = useMemo(() => ({ state, actions }), [state, actions]);

  return (
    <WorkbenchContext.Provider value={value}>
      {children}
    </WorkbenchContext.Provider>
  );
}

export function useWorkbench(): WorkbenchContextValue {
  const value = useContext(WorkbenchContext);
  if (!value) {
    throw new Error("useWorkbench must be used inside a WorkbenchProvider");
  }
  return value;
}

/** Remove every persisted workbench value for one snapshot. */
export function clearWorkbenchStorage(snapshotName: string): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(workbenchStorageKey(snapshotName));
    // Remove the v1 per-activity layout and last-activity keys.
    for (const activity of ["topology", "detail"]) {
      window.localStorage.removeItem(
        `kg-workbench:v1:${snapshotName}:${activity}`,
      );
    }
    window.localStorage.removeItem(`kg-workbench:v1:${snapshotName}:activity`);
  } catch {
    // Ignore storage failures; reloading still gives the default layout.
  }
}

export { DEFAULT_LAYOUT };
