/**
 * Workbench contract shared by the shell and the two angles.
 *
 * The shell owns snapshot loading, one workbench geometry and the global tab strip.
 * A function owns its sidebar, editor and bottom-panel bodies and never resizes
 * the workbench.
 */

import type { LucideIcon } from "lucide-react";

import type { ViewerIndex, ViewerSnapshot } from "@/lib/types";

export type ActivityId = "topology" | "detail";

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
  /** The active bottom tab is content, not geometry, so it stays per activity. */
  bottomTabs: Partial<Record<ActivityId, string>>;
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
  /** Geometry is one workbench value, shared by every activity. */
  layout: WorkbenchLayout;
  activity: ActivityId;
  tabs: WorkbenchTab[];
  activeTabId: string;
  history: string[];
  historyIndex: number;
}

export interface OpenTabInput {
  selection: WorkbenchSelection;
  title?: string;
}

export interface WorkbenchActions {
  setActivity(activity: ActivityId): void;
  setSelection(selection: WorkbenchSelection): void;
  setLayout(patch: Partial<Pick<WorkbenchLayout, "sidebarWidth" | "bottomHeight">>): void;
  setBottomTab(activity: ActivityId, tab: string): void;
  openTab(tab: OpenTabInput): void;
  closeTab(tabId: string): void;
  activateTab(tabId: string): void;
  back(): void;
  forward(): void;
}

export function activeTab(state: WorkbenchState): WorkbenchTab | undefined {
  return state.tabs.find((tab) => tab.id === state.activeTabId);
}

export function currentSelection(state: WorkbenchState): WorkbenchSelection {
  return activeTab(state)?.selection ?? { kind: "graph", name: "Graph" };
}

export interface FeatureProps {
  state: WorkbenchState;
  actions: WorkbenchActions;
  activity: ActivityId;
}

export interface FeatureModule {
  id: ActivityId;
  label: string;
  icon: LucideIcon;
  Sidebar: React.ComponentType<FeatureProps>;
  Editor: React.ComponentType<FeatureProps>;
  Bottom: React.ComponentType<FeatureProps>;
}

export const DEFAULT_LAYOUT: WorkbenchLayout = {
  sidebarWidth: 300,
  bottomHeight: 240,
  bottomTabs: {},
};

export const MIN_SIDEBAR = 220;
export const MAX_SIDEBAR = 520;
export const MIN_BOTTOM = 120;
export const MAX_BOTTOM = 480;
