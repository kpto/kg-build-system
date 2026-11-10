"use client";

/**
 * Workbench state and persistence.
 *
 * One state value owns the loaded snapshot, one global panel geometry, one
 * global editor-tab strip, and the navigation history over that strip. The
 * geometry is never per activity: switching activity changes content, not the
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
import {
  ACTIVITY_ORDER,
  defaultBottomTab,
  isRetiredBottomTab,
} from "./defaults";
import type {
  ActivityId,
  OpenTabInput,
  SelectionKind,
  WorkbenchActions,
  WorkbenchLayout,
  WorkbenchSelection,
  WorkbenchState,
  WorkbenchTab,
} from "./types";
import {
  DEFAULT_LAYOUT,
  MAX_BOTTOM,
  MAX_SIDEBAR,
  MIN_BOTTOM,
  MIN_SIDEBAR,
} from "./types";

export const WORKBENCH_STORAGE_PREFIX = "kg-workbench:v2";

const SELECTION_KINDS = new Set<SelectionKind>([
  "graph",
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

function defaultBottomTabs(): WorkbenchLayout["bottomTabs"] {
  return { topology: "selection", detail: "trace" };
}

function normalizeLayout(value: unknown): WorkbenchLayout {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return { ...DEFAULT_LAYOUT, bottomTabs: defaultBottomTabs() };
  }
  const candidate = value as Record<string, unknown>;
  const rawTabs =
    candidate.bottomTabs &&
    typeof candidate.bottomTabs === "object" &&
    !Array.isArray(candidate.bottomTabs)
      ? (candidate.bottomTabs as Record<string, unknown>)
      : {};
  const bottomTabs: WorkbenchLayout["bottomTabs"] = { ...DEFAULT_LAYOUT.bottomTabs };
  for (const activity of ACTIVITY_ORDER) {
    const tab = rawTabs[activity];
    bottomTabs[activity] =
      typeof tab === "string" && tab && !isRetiredBottomTab(tab)
        ? tab
        : defaultBottomTab(activity);
  }
  return {
    sidebarWidth: clamp(
      numberOr(candidate.sidebarWidth, DEFAULT_LAYOUT.sidebarWidth),
      MIN_SIDEBAR,
      MAX_SIDEBAR,
    ),
    bottomHeight: clamp(
      numberOr(candidate.bottomHeight, DEFAULT_LAYOUT.bottomHeight),
      MIN_BOTTOM,
      MAX_BOTTOM,
    ),
    bottomTabs,
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

function normalizeSelection(value: unknown): WorkbenchSelection {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return { kind: "graph", name: "Graph" };
  }
  const candidate = value as Record<string, unknown>;
  const selection: WorkbenchSelection = {};

  if (
    typeof candidate.kind === "string" &&
    SELECTION_KINDS.has(candidate.kind as SelectionKind)
  ) {
    selection.kind = candidate.kind as SelectionKind;
  }
  for (const field of ["name", "component", "property"] as const) {
    if (typeof candidate[field] === "string") selection[field] = candidate[field];
  }
  if (
    typeof candidate.level === "string" &&
    DETAIL_LEVELS.has(candidate.level)
  ) {
    selection.level = candidate.level as WorkbenchSelection["level"];
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

function selectionSignature(selection: WorkbenchSelection): string {
  return [
    selection.kind ?? "",
    selection.component ?? "",
    selection.name ?? "",
    selection.property ?? "",
    selection.level ?? "",
    selection.stepId?.join("/") ?? "",
  ].join("\u0000");
}

function tabTitle(selection: WorkbenchSelection): string {
  if (selection.kind === "graph") return "Graph";
  if (selection.kind === "property" && selection.component && selection.property) {
    return `${selection.component}.${selection.property}`;
  }
  if (selection.component) return selection.component;
  if (selection.name) return selection.name;
  return "Detail";
}

function tabId(selection: WorkbenchSelection): string {
  if (selection.kind === "graph") return GRAPH_TAB_ID;
  return `document:${selectionSignature(selection)}`;
}

function graphTab(): WorkbenchTab {
  const selection: WorkbenchSelection = { kind: "graph", name: "Graph" };
  return { id: GRAPH_TAB_ID, title: "Graph", selection, pinned: true };
}

export function createWorkbenchState(
  snapshot: ViewerSnapshot,
  index: ViewerIndex,
): WorkbenchState {
  const tab = graphTab();
  return {
    snapshot,
    index,
    layout: normalizeLayout(undefined),
    activity: "topology",
    tabs: [tab],
    activeTabId: tab.id,
    history: [tab.id],
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
  if (selection.kind === "graph") {
    const existing = state.tabs.find((tab) => tab.id === GRAPH_TAB_ID);
    if (existing) return activate(state, existing.id);
    const tab = graphTab();
    return activate({ ...state, tabs: [tab, ...state.tabs] }, tab.id);
  }
  const signature = selectionSignature(selection);
  const existing = state.tabs.find(
    (tab) => selectionSignature(tab.selection) === signature,
  );
  if (existing) return activate(state, existing.id);

  const tab: WorkbenchTab = {
    id: tabId(selection),
    title: input.title ?? tabTitle(selection),
    selection,
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
  | { type: "set-activity"; activity: ActivityId }
  | { type: "set-selection"; selection: WorkbenchSelection }
  | { type: "set-layout"; patch: Partial<Pick<WorkbenchLayout, "sidebarWidth" | "bottomHeight">> }
  | { type: "set-bottom-tab"; activity: ActivityId; tab: string }
  | { type: "open-tab"; input: OpenTabInput }
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

    case "set-activity":
      // The activity is the viewing angle. It never changes the active document.
      return { ...state, activity: action.activity };

    case "set-selection": {
      const tab = state.tabs.find((candidate) => candidate.id === state.activeTabId);
      if (!tab) return state;
      const selection = normalizeSelection(action.selection);
      return {
        ...state,
        tabs: state.tabs.map((candidate) =>
          candidate.id === tab.id
            ? { ...candidate, selection, title: tabTitle(selection) }
            : candidate,
        ),
      };
    }

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
          bottomHeight: clamp(
            numberOr(action.patch.bottomHeight, state.layout.bottomHeight),
            MIN_BOTTOM,
            MAX_BOTTOM,
          ),
        },
      };

    case "set-bottom-tab":
      return {
        ...state,
        layout: {
          ...state.layout,
          bottomTabs: {
            ...state.layout.bottomTabs,
            [action.activity]: action.tab,
          },
        },
      };

    case "open-tab":
      return appendTab(state, action.input);

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
      setActivity: (activity) => dispatch({ type: "set-activity", activity }),
      setSelection: (selection) =>
        dispatch({ type: "set-selection", selection }),
      setLayout: (patch) => dispatch({ type: "set-layout", patch }),
      setBottomTab: (activity, tab) =>
        dispatch({ type: "set-bottom-tab", activity, tab }),
      openTab: (input) => dispatch({ type: "open-tab", input }),
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
    for (const activity of ACTIVITY_ORDER) {
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
