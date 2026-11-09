/**
 * Workbench contract shared by the shell and the three functions.
 *
 * The shell owns snapshot loading and the per-function layout/selection state.
 * A function owns its sidebar, editor and bottom-panel bodies and never resizes
 * the workbench.
 */

import type { LucideIcon } from "lucide-react";

import type { ViewerIndex, ViewerSnapshot } from "@/lib/types";

export type ActivityId = "topology" | "proof" | "meaning";

export type SelectionKind =
  | "asset"
  | "relation"
  | "projection"
  | "field"
  | "node"
  | "edge"
  | "property"
  | "binding"
  | "step";

export type ProofLevel = "property" | "node" | "edge" | "abstract" | "asset";

export interface WorkbenchSelection {
  activity: ActivityId;
  kind?: SelectionKind;
  name?: string;
  component?: string;
  property?: string;
  level?: ProofLevel;
  stepId?: [string, string];
}

export interface FunctionLayout {
  sidebarWidth: number;
  bottomHeight: number;
  bottomTab: string;
  openTabs: string[];
  activeTab: string | null;
}

export interface FunctionState {
  layout: FunctionLayout;
  selection: WorkbenchSelection;
}

export interface WorkbenchState {
  snapshot: ViewerSnapshot;
  index: ViewerIndex;
  activity: ActivityId;
  functions: Record<ActivityId, FunctionState>;
}

export interface WorkbenchActions {
  setActivity(activity: ActivityId): void;
  setSelection(activity: ActivityId, selection: WorkbenchSelection): void;
  setLayout(activity: ActivityId, patch: Partial<FunctionLayout>): void;
  openTab(activity: ActivityId, tab: string): void;
  closeTab(activity: ActivityId, tab: string): void;
  setActiveTab(activity: ActivityId, tab: string | null): void;
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

export const DEFAULT_LAYOUT: FunctionLayout = {
  sidebarWidth: 300,
  bottomHeight: 240,
  bottomTab: "selection",
  openTabs: [],
  activeTab: null,
};

export const MIN_SIDEBAR = 220;
export const MAX_SIDEBAR = 520;
export const MIN_BOTTOM = 120;
export const MAX_BOTTOM = 480;
