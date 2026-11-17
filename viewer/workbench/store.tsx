"use client";

/**
 * Workbench state and persistence.
 *
 * One state value owns the loaded snapshot, one global panel geometry, one
 * global editor-tab strip, and the navigation history over that strip. The
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

import type {
  OpenTabInput,
  SubjectKind,
  WorkbenchActions,
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

function selectionSignature(selection: SubjectSelection): string {
  return [
    selection.kind ?? "",
    selection.component ?? "",
    selection.name ?? "",
    selection.property ?? "",
    selection.level ?? "",
    selection.stepId?.join("/") ?? "",
    selection.bindingIndex?.toString() ?? "",
  ].join("\u0000");
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
    history: [graph.id],
    historyIndex: 0,
  };
}

function pushHistory(
  state: WorkbenchState,
  tabIdValue: string,
): Pick<WorkbenchState, "history" | "historyIndex"> {
  const history = state.history.slice(0, state.historyIndex + 1);
  if (history[history.length - 1] !== tabIdValue) history.push(tabIdValue);
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
    ...(record ? pushHistory(state, tab.id) : {}),
  };
}

function appendTab(
  state: WorkbenchState,
  input: OpenTabInput,
): WorkbenchState {
  const selection = normalizeSelection(input.selection);
  if (!selection || !selection.kind) return state;
  const signature = selectionSignature(selection);
  const existing = state.tabs.find(
    (tab) =>
      tab.document.kind === "subject" &&
      selectionSignature(tab.document.selection) === signature,
  );
  if (existing) {
    // Opening a subject explicitly promotes a preview tab to permanent.
    if (!input.preview && existing.preview) {
      return activate(
        {
          ...state,
          tabs: state.tabs.map((tab) =>
            tab.id === existing.id ? { ...tab, preview: undefined } : tab,
          ),
        },
        existing.id,
      );
    }
    return activate(state, existing.id);
  }

  if (input.preview) {
    const preview = state.tabs.find((tab) => tab.preview && !tab.pinned);
    if (preview) {
      // Reuse one preview tab, like a browser or VS Code. The id tracks the
      // shown selection so a later permanent document cannot collide with it.
      const nextId = previewId(selection);
      const tabs = state.tabs.map((tab) =>
        tab.id === preview.id
          ? {
              ...tab,
              id: nextId,
              document: { kind: "subject" as const, selection },
            }
          : tab,
      );
      const history = state.history.map((id) =>
        id === preview.id ? nextId : id,
      );
      const activeTabId =
        state.activeTabId === preview.id ? nextId : state.activeTabId;
      return activate({ ...state, tabs, history, activeTabId }, nextId);
    }
  }

  const tab: WorkbenchTab = {
    id: input.preview ? previewId(selection) : subjectId(selection),
    document: { kind: "subject", selection },
    ...(input.preview ? { preview: true } : {}),
  };
  return activate({ ...state, tabs: [...state.tabs, tab] }, tab.id);
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
      return {
        ...state,
        tabs: state.tabs.map((candidate) =>
          candidate.id === tab.id
            ? { ...candidate, document: { kind: "subject", selection } }
            : candidate,
        ),
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
      let history = state.history.filter((id) => id !== action.tabId);
      let historyIndex = Math.min(state.historyIndex, history.length - 1);
      if (nextActive.id !== state.activeTabId) {
        history = history.slice(0, Math.max(0, historyIndex) + 1);
        if (history[history.length - 1] !== nextActive.id) {
          history.push(nextActive.id);
        }
        historyIndex = history.length - 1;
      }
      return {
        ...state,
        tabs: remaining,
        activeTabId: nextActive.id,
        history,
        historyIndex: Math.max(0, historyIndex),
      };
    }

    case "activate-tab":
      return activate(state, action.tabId);

    case "back": {
      for (let index = state.historyIndex - 1; index >= 0; index -= 1) {
        const id = state.history[index];
        if (state.tabs.some((tab) => tab.id === id)) {
          const tab = state.tabs.find((candidate) => candidate.id === id);
          if (!tab) return state;
          return {
            ...state,
            activeTabId: tab.id,
            historyIndex: index,
          };
        }
      }
      return state;
    }

    case "forward": {
      for (let index = state.historyIndex + 1; index < state.history.length; index += 1) {
        const id = state.history[index];
        if (state.tabs.some((tab) => tab.id === id)) {
          const tab = state.tabs.find((candidate) => candidate.id === id);
          if (!tab) return state;
          return {
            ...state,
            activeTabId: tab.id,
            historyIndex: index,
          };
        }
      }
      return state;
    }

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
