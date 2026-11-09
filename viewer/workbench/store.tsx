"use client";

/**
 * Workbench state and persistence.
 *
 * One state value owns the loaded snapshot, the review sidecar, the active
 * function and the stable per-function layout/selection. The reducer does only
 * layout, selection and review plumbing; feature meaning stays in the feature
 * modules.
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

import type { ReviewSidecar } from "@/lib/reviewTypes";
import type { ViewerIndex, ViewerSnapshot } from "@/lib/types";
import {
  ACTIVITY_ORDER,
  defaultFunctions,
  emptySelection,
} from "./defaults";
import type {
  ActivityId,
  FunctionLayout,
  FunctionState,
  SelectionKind,
  WorkbenchActions,
  WorkbenchSelection,
  WorkbenchState,
} from "./types";
import {
  DEFAULT_LAYOUT,
  MAX_BOTTOM,
  MAX_SIDEBAR,
  MIN_BOTTOM,
  MIN_SIDEBAR,
} from "./types";

export const WORKBENCH_STORAGE_PREFIX = "kg-workbench:v1";

const SELECTION_KINDS = new Set<SelectionKind>([
  "asset",
  "relation",
  "projection",
  "field",
  "node",
  "edge",
  "property",
  "binding",
  "finding",
  "unit",
  "step",
]);

const PROOF_LEVELS = new Set(["property", "node", "edge", "abstract", "asset"]);

export const EMPTY_REVIEW: ReviewSidecar = {
  format: "kg-viewer-review",
  version: 1,
  decisions: [],
};

/** The localStorage key for one snapshot's function layout and selection. */
export function workbenchStorageKey(
  snapshotName: string,
  activity: ActivityId,
): string {
  return `${WORKBENCH_STORAGE_PREFIX}:${snapshotName}:${activity}`;
}

/** The localStorage key for the last active activity of a snapshot. */
export function workbenchActivityKey(snapshotName: string): string {
  return `${WORKBENCH_STORAGE_PREFIX}:${snapshotName}:activity`;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function numberOr(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function stringsOr(value: unknown, fallback: string[]): string[] {
  if (!Array.isArray(value)) return fallback;
  return value.filter((entry): entry is string => typeof entry === "string");
}

function normalizeLayout(
  value: unknown,
  fallback: FunctionLayout,
): FunctionLayout {
  if (!value || typeof value !== "object" || Array.isArray(value)) return fallback;
  const candidate = value as Record<string, unknown>;
  const openTabs = Array.isArray(candidate.openTabs)
    ? stringsOr(candidate.openTabs, fallback.openTabs)
    : fallback.openTabs;
  const rawActive = candidate.activeTab;
  const activeTab =
    rawActive === null
      ? null
      : typeof rawActive === "string"
        ? rawActive
        : fallback.activeTab;

  return {
    sidebarWidth: clamp(
      numberOr(candidate.sidebarWidth, fallback.sidebarWidth),
      MIN_SIDEBAR,
      MAX_SIDEBAR,
    ),
    bottomHeight: clamp(
      numberOr(candidate.bottomHeight, fallback.bottomHeight),
      MIN_BOTTOM,
      MAX_BOTTOM,
    ),
    bottomTab:
      typeof candidate.bottomTab === "string" && candidate.bottomTab
        ? candidate.bottomTab
        : fallback.bottomTab,
    openTabs,
    activeTab,
  };
}

function normalizeSelection(
  value: unknown,
  activity: ActivityId,
): WorkbenchSelection {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return emptySelection(activity);
  }
  const candidate = value as Record<string, unknown>;
  const selection: WorkbenchSelection = { activity };

  if (
    typeof candidate.kind === "string" &&
    SELECTION_KINDS.has(candidate.kind as SelectionKind)
  ) {
    selection.kind = candidate.kind as SelectionKind;
  }
  for (const field of ["name", "component", "property", "findingId", "unitKey"] as const) {
    if (typeof candidate[field] === "string") selection[field] = candidate[field];
  }
  if (
    typeof candidate.level === "string" &&
    PROOF_LEVELS.has(candidate.level)
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

function normalizeFunctionState(
  value: unknown,
  activity: ActivityId,
  fallback: FunctionState,
): FunctionState {
  if (!value || typeof value !== "object" || Array.isArray(value)) return fallback;
  const candidate = value as Record<string, unknown>;
  return {
    layout: normalizeLayout(candidate.layout, fallback.layout),
    selection: normalizeSelection(candidate.selection, activity),
  };
}

function readFunctionState(
  snapshotName: string,
  activity: ActivityId,
  fallback: FunctionState,
): FunctionState {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = window.localStorage.getItem(
      workbenchStorageKey(snapshotName, activity),
    );
    if (!raw) return fallback;
    return normalizeFunctionState(JSON.parse(raw), activity, fallback);
  } catch {
    return fallback;
  }
}

function writeFunctionState(
  snapshotName: string,
  activity: ActivityId,
  value: FunctionState,
): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      workbenchStorageKey(snapshotName, activity),
      JSON.stringify(value),
    );
  } catch {
    // A browser may refuse storage. The workbench still works in memory.
  }
}

function readActivity(snapshotName: string): ActivityId | undefined {
  if (typeof window === "undefined") return undefined;
  try {
    const raw = window.localStorage.getItem(workbenchActivityKey(snapshotName));
    return ACTIVITY_ORDER.includes(raw as ActivityId)
      ? (raw as ActivityId)
      : undefined;
  } catch {
    return undefined;
  }
}

/** Remove every persisted panel value for one snapshot. */
export function clearWorkbenchStorage(snapshotName: string): void {
  if (typeof window === "undefined") return;
  try {
    for (const activity of ACTIVITY_ORDER) {
      window.localStorage.removeItem(
        workbenchStorageKey(snapshotName, activity),
      );
    }
    window.localStorage.removeItem(workbenchActivityKey(snapshotName));
  } catch {
    // Ignore storage failures; reloading still gives the default layout.
  }
}

type Action =
  | { type: "hydrate"; functions: Record<ActivityId, FunctionState>; activity?: ActivityId }
  | { type: "set-activity"; activity: ActivityId }
  | { type: "set-selection"; activity: ActivityId; selection: WorkbenchSelection }
  | { type: "set-layout"; activity: ActivityId; patch: Partial<FunctionLayout> }
  | { type: "update-review"; review: ReviewSidecar }
  | { type: "open-tab"; activity: ActivityId; tab: string }
  | { type: "close-tab"; activity: ActivityId; tab: string }
  | { type: "set-active-tab"; activity: ActivityId; tab: string | null };

function withFunction(
  state: WorkbenchState,
  activity: ActivityId,
  next: FunctionState,
): WorkbenchState {
  return {
    ...state,
    functions: { ...state.functions, [activity]: next },
  };
}

function mergeLayout(
  current: FunctionLayout,
  patch: Partial<FunctionLayout>,
): FunctionLayout {
  return {
    sidebarWidth: clamp(
      numberOr(patch.sidebarWidth, current.sidebarWidth),
      MIN_SIDEBAR,
      MAX_SIDEBAR,
    ),
    bottomHeight: clamp(
      numberOr(patch.bottomHeight, current.bottomHeight),
      MIN_BOTTOM,
      MAX_BOTTOM,
    ),
    bottomTab:
      typeof patch.bottomTab === "string" && patch.bottomTab
        ? patch.bottomTab
        : current.bottomTab,
    openTabs: Array.isArray(patch.openTabs)
      ? stringsOr(patch.openTabs, current.openTabs)
      : current.openTabs,
    activeTab:
      patch.activeTab === null
        ? null
        : typeof patch.activeTab === "string"
          ? patch.activeTab
          : current.activeTab,
  };
}

function reducer(state: WorkbenchState, action: Action): WorkbenchState {
  switch (action.type) {
    case "hydrate":
      return {
        ...state,
        activity: action.activity ?? state.activity,
        functions: action.functions,
      };
    case "set-activity":
      return { ...state, activity: action.activity };
    case "set-selection":
      return withFunction(state, action.activity, {
        ...state.functions[action.activity],
        selection: { ...action.selection, activity: action.activity },
      });
    case "set-layout":
      return withFunction(state, action.activity, {
        ...state.functions[action.activity],
        layout: mergeLayout(state.functions[action.activity].layout, action.patch),
      });
    case "update-review":
      return { ...state, review: action.review };
    case "open-tab": {
      if (!action.tab) return state;
      const current = state.functions[action.activity];
      const openTabs = current.layout.openTabs.includes(action.tab)
        ? current.layout.openTabs
        : [...current.layout.openTabs, action.tab];
      return withFunction(state, action.activity, {
        ...current,
        layout: { ...current.layout, openTabs, activeTab: action.tab },
      });
    }
    case "close-tab": {
      const current = state.functions[action.activity];
      const index = current.layout.openTabs.indexOf(action.tab);
      if (index < 0) return state;
      const openTabs = current.layout.openTabs.filter((tab) => tab !== action.tab);
      const activeTab =
        current.layout.activeTab === action.tab
          ? (openTabs[Math.min(index, openTabs.length - 1)] ?? null)
          : current.layout.activeTab;
      return withFunction(state, action.activity, {
        ...current,
        layout: { ...current.layout, openTabs, activeTab },
      });
    }
    case "set-active-tab": {
      const current = state.functions[action.activity];
      if (action.tab === null) {
        return withFunction(state, action.activity, {
          ...current,
          layout: { ...current.layout, activeTab: null },
        });
      }
      const openTabs = current.layout.openTabs.includes(action.tab)
        ? current.layout.openTabs
        : [...current.layout.openTabs, action.tab];
      return withFunction(state, action.activity, {
        ...current,
        layout: { ...current.layout, openTabs, activeTab: action.tab },
      });
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
  review: ReviewSidecar;
  children: ReactNode;
}

export function WorkbenchProvider({
  snapshot,
  index,
  review,
  children,
}: WorkbenchProviderProps) {
  const [state, dispatch] = useReducer(reducer, undefined, () => ({
    snapshot,
    index,
    review,
    activity: "proof" as ActivityId,
    functions: defaultFunctions(),
  }));
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const name = snapshot.name;
    const fallback = defaultFunctions();
    const functions: Record<ActivityId, FunctionState> = {
      proof: readFunctionState(name, "proof", fallback.proof),
      audit: readFunctionState(name, "audit", fallback.audit),
      semantics: readFunctionState(name, "semantics", fallback.semantics),
      topology: readFunctionState(name, "topology", fallback.topology),
    };
    dispatch({ type: "hydrate", functions, activity: readActivity(name) });
    setHydrated(true);
  }, [snapshot.name]);

  useEffect(() => {
    if (!hydrated) return;
    for (const activity of ACTIVITY_ORDER) {
      writeFunctionState(snapshot.name, activity, state.functions[activity]);
    }
    try {
      window.localStorage.setItem(
        workbenchActivityKey(snapshot.name),
        state.activity,
      );
    } catch {
      // Storage is optional; the in-memory workbench remains correct.
    }
  }, [hydrated, snapshot.name, state.activity, state.functions]);

  const actions = useMemo<WorkbenchActions>(
    () => ({
      setActivity: (activity) => dispatch({ type: "set-activity", activity }),
      setSelection: (activity, selection) =>
        dispatch({ type: "set-selection", activity, selection }),
      setLayout: (activity, patch) =>
        dispatch({ type: "set-layout", activity, patch }),
      updateReview: (next) => dispatch({ type: "update-review", review: next }),
      openTab: (activity, tab) => dispatch({ type: "open-tab", activity, tab }),
      closeTab: (activity, tab) => dispatch({ type: "close-tab", activity, tab }),
      setActiveTab: (activity, tab) =>
        dispatch({ type: "set-active-tab", activity, tab }),
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

export { DEFAULT_LAYOUT };
