/**
 * Workbench contract.
 *
 * One frame owns snapshot loading, one geometry, one document tab strip and the
 * transient inspection of the canonical graph. The side bar exposes Topology
 * and Detail as collapsible sections; neither is a mode.
 */

import type { ViewerIndex, ViewerSnapshot } from "@/lib/types";

export type SubjectKind =
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

/** A subject the viewer can open or inspect. There is no graph subject. */
export interface SubjectSelection {
  kind?: SubjectKind;
  name?: string;
  component?: string;
  property?: string;
  level?: DetailLevel;
  stepId?: [string, string];
}

export type WorkbenchDocument =
  | { kind: "graph" }
  | { kind: "subject"; selection: SubjectSelection };

export interface WorkbenchTab {
  id: string;
  document: WorkbenchDocument;
  /** The canonical graph tab is always available. */
  pinned?: boolean;
}

export interface WorkbenchLayout {
  sidebarWidth: number;
  bottomHeight: number;
}

export interface WorkbenchState {
  snapshot: ViewerSnapshot;
  index: ViewerIndex;
  /** Geometry is one workbench value, shared by every document. */
  layout: WorkbenchLayout;
  tabs: WorkbenchTab[];
  activeTabId: string;
  /** Transient graph inspection; it never becomes a document by itself. */
  inspection?: SubjectSelection;
  history: string[];
  historyIndex: number;
}

export interface OpenTabInput {
  selection: SubjectSelection;
}

export interface WorkbenchActions {
  setSelection(selection: SubjectSelection): void;
  inspect(selection: SubjectSelection | undefined): void;
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

export function activeDocument(state: WorkbenchState): WorkbenchDocument {
  return activeTab(state)?.document ?? { kind: "graph" };
}

export function documentSelection(
  document: WorkbenchDocument,
): SubjectSelection | undefined {
  return document.kind === "subject" ? document.selection : undefined;
}

/** The Graph document uses transient inspection; a subject uses itself. */
export function lensSelection(state: WorkbenchState): SubjectSelection | undefined {
  const document = activeDocument(state);
  return document.kind === "graph" ? state.inspection : document.selection;
}

export function subjectTitle(selection: SubjectSelection): string {
  if (selection.kind === "property" && selection.component && selection.property) {
    return `${selection.component}.${selection.property}`;
  }
  if (selection.component) return selection.component;
  if (selection.name) return selection.name;
  return "Detail";
}

export function documentTitle(document: WorkbenchDocument): string {
  return document.kind === "graph" ? "Graph" : subjectTitle(document.selection);
}

export const DEFAULT_LAYOUT: WorkbenchLayout = {
  sidebarWidth: 300,
  bottomHeight: 240,
};

export const MIN_SIDEBAR = 220;
export const MAX_SIDEBAR = 520;
export const MIN_BOTTOM = 120;
export const MAX_BOTTOM = 480;
