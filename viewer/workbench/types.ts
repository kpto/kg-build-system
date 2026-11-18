/**
 * Workbench contract.
 *
 * One frame owns snapshot loading, one geometry, one document tab strip and the
 * transient inspection of the canonical graph. The side bar exposes Control and
 * Explorer as collapsible sections; neither is a mode.
 */

import type { ViewerIndex, ViewerSnapshot } from "@/lib/types";
import { collectionTitle, type CollectionId } from "./collections";

export type SubjectKind =
  | "asset"
  | "relation"
  | "projection"
  | "field"
  | "node"
  | "edge"
  | "property"
  | "binding"
  | "step"
  | "collection";

export type DetailLevel = "property" | "node" | "edge" | "abstract" | "asset";

/** A subject the viewer can open or inspect. There is no graph subject. */
export interface SubjectSelection {
  kind?: SubjectKind;
  name?: string;
  component?: string;
  property?: string;
  level?: DetailLevel;
  stepId?: [string, string];
  /** The binding identity when the subject is a binding document. */
  bindingIndex?: number;
  /** The virtual collection when the subject is a collection document. */
  collection?: CollectionId;
  /** True when the subject is an abstract edge participant. */
  abstract?: boolean;
}

export type WorkbenchDocument =
  | { kind: "graph" }
  | { kind: "workflow" }
  | { kind: "subject"; selection: SubjectSelection };

export interface WorkbenchTab {
  id: string;
  document: WorkbenchDocument;
  /** The canonical Graph and Workflow tabs are always available. */
  pinned?: boolean;
  /** A preview tab is reused by the next single-click navigation. */
  preview?: boolean;
}

export interface WorkbenchLayout {
  sidebarWidth: number;
  /** Share of the side bar height used by the Control section when both are open. */
  sidebarSplit: number;
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
  /** Single-click navigation opens a reusable preview tab. */
  preview?: boolean;
}

export interface WorkbenchActions {
  setSelection(selection: SubjectSelection): void;
  inspect(selection: SubjectSelection | undefined): void;
  setLayout(patch: Partial<WorkbenchLayout>): void;
  openTab(tab: OpenTabInput): void;
  showGraph(selection: SubjectSelection): void;
  showWorkflow(): void;
  pinTab(tabId: string): void;
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
  if (document.kind === "graph") return state.inspection;
  return document.kind === "subject" ? document.selection : undefined;
}

export function subjectTitle(selection: SubjectSelection): string {
  if (selection.kind === "collection") {
    return collectionTitle(
      selection.collection ?? "assets",
      selection.component,
    );
  }
  if (selection.kind === "step") {
    return selection.name ?? selection.component ?? "Step";
  }
  if (selection.kind === "binding") {
    const base =
      selection.name ??
      (selection.bindingIndex !== undefined
        ? `#${selection.bindingIndex}`
        : "Binding");
    return base.toLowerCase().startsWith("binding") ? base : `binding ${base}`;
  }
  if (selection.kind === "property" && selection.component && selection.property) {
    return `${selection.component}.${selection.property}`;
  }
  if (selection.component) return selection.component;
  if (selection.name) return selection.name;
  return "Detail";
}

export function documentTitle(document: WorkbenchDocument): string {
  if (document.kind === "graph") return "Graph";
  if (document.kind === "workflow") return "Workflow";
  return subjectTitle(document.selection);
}

/**
 * The semantic identity of a subject document. Display-only and derived fields
 * are excluded: a node's `name` repeats its `component`, a property's `name`
 * repeats its owner and property, a step's `stepId` repeats its component and
 * name, and a collection's `name` is its display title. Two navigations that
 * reach the same subject therefore open one tab, not two.
 */
export function selectionSignature(selection: SubjectSelection): string {
  switch (selection.kind) {
    case "node":
    case "edge":
    case "asset":
    case "relation":
    case "projection":
      return [
        selection.kind,
        selection.component ?? selection.name ?? "",
        selection.level ?? "",
        selection.abstract ? "abstract" : "",
      ].join("\u0000");
    case "property":
      return [
        "property",
        selection.component ?? "",
        selection.property ?? "",
        selection.level ?? "",
      ].join("\u0000");
    case "field":
      return ["field", selection.component ?? "", selection.name ?? ""].join(
        "\u0000",
      );
    case "binding":
      return [
        "binding",
        selection.bindingIndex?.toString() ??
          `${selection.component ?? ""}:${selection.name ?? ""}`,
        selection.component ?? "",
      ].join("\u0000");
    case "step":
      return [
        "step",
        selection.component ?? selection.stepId?.[0] ?? "",
        selection.name ?? selection.stepId?.[1] ?? "",
      ].join("\u0000");
    case "collection":
      return [
        "collection",
        selection.collection ?? "",
        selection.component ?? "",
      ].join("\u0000");
    default:
      return [
        selection.kind ?? "",
        selection.component ?? "",
        selection.name ?? "",
        selection.property ?? "",
        selection.level ?? "",
        selection.stepId?.join("/") ?? "",
        selection.bindingIndex?.toString() ?? "",
        selection.collection ?? "",
        selection.abstract ? "abstract" : "",
      ].join("\u0000");
  }
}

/** Stable content identity used to remount a pane when a preview replaces it. */
export function documentSignature(document: WorkbenchDocument): string {
  if (document.kind === "graph") return "graph";
  if (document.kind === "workflow") return "workflow";
  return selectionSignature(document.selection);
}

export const DEFAULT_LAYOUT: WorkbenchLayout = {
  sidebarWidth: 300,
  sidebarSplit: 0.5,
};

export const MIN_SIDEBAR = 220;
export const MAX_SIDEBAR = 520;
export const MIN_SIDEBAR_SPLIT = 0.2;
export const MAX_SIDEBAR_SPLIT = 0.8;
