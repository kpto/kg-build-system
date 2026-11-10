/**
 * Workbench contract.
 *
 * One frame owns snapshot loading, one geometry, one document tab strip and the
 * transient inspection of the canonical graph. The side bar exposes the
 * Topology and Detail sections; neither is a mode and neither changes a tab.
 */

import type { ViewerIndex, ViewerSnapshot } from "@/lib/types";

export type SelectionKind =
  | "graph"
  | "asset"
  | "relation"
  | "projection"
  | "field"
  | "node"
  | "edge"
  | "property"
  | "binding"
  | "step";

export type DetailLevel = "property" | "node" | "edge" | "abstract" | "asset";

export type TabView = "graph" | "subject";

export interface WorkbenchSelection {
  kind?: SelectionKind;
  name?: string;
  component?: string;
  property?: string;
  level?: DetailLevel;
  stepId?: [string, string];
}

export interface WorkbenchLayout {
  sidebarWidth: number;
  bottomHeight: number;
}

export interface WorkbenchTab {
  id: string;
  title: string;
  selection: WorkbenchSelection;
  /** The canonical graph tab is always available. */
  pinned?: boolean;
}

export interface WorkbenchState {
  snapshot: ViewerSnapshot;
  index: ViewerIndex;
  /** Geometry is one workbench value, shared by every document. */
  layout: WorkbenchLayout;
  tabs: WorkbenchTab[];
  activeTabId: string;
  /** Transient graph inspection; it never becomes a document by itself. */
  inspection: WorkbenchSelection;
  history: string[];
  historyIndex: number;
}

export interface OpenTabInput {
  selection: WorkbenchSelection;
  title?: string;
}

export interface WorkbenchActions {
  setSelection(selection: WorkbenchSelection): void;
  inspect(selection: WorkbenchSelection): void;
  setLayout(patch: Partial<Pick<WorkbenchLayout, "sidebarWidth" | "bottomHeight">>): void;
  openTab(tab: OpenTabInput): void;
  closeTab(tabId: string): void;
  activateTab(tabId: string): void;
  back(): void;
  forward(): void;
}

export interface WorkspaceProps {
  state: WorkbenchState;
  actions: WorkbenchActions;
}

export function activeTab(state: WorkbenchState): WorkbenchTab | undefined {
  return state.tabs.find((tab) => tab.id === state.activeTabId);
}

export function currentSelection(state: WorkbenchState): WorkbenchSelection {
  return activeTab(state)?.selection ?? { kind: "graph", name: "Graph" };
}

export function tabView(selection: WorkbenchSelection): TabView {
  return selection.kind === "graph" ? "graph" : "subject";
}

/** The Graph document uses transient inspection; a subject uses itself. */
export function currentLensSelection(state: WorkbenchState): WorkbenchSelection {
  const selection = currentSelection(state);
  return selection.kind === "graph" ? state.inspection : selection;
}

export const DEFAULT_LAYOUT: WorkbenchLayout = {
  sidebarWidth: 300,
  bottomHeight: 240,
};

export const MIN_SIDEBAR = 220;
export const MAX_SIDEBAR = 520;
export const MIN_BOTTOM = 120;
export const MAX_BOTTOM = 480;
