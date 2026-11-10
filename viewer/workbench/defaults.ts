/**
 * Workbench defaults.
 *
 * The shell owns one workbench geometry and the bottom tabs that belong to each
 * activity. Editor tabs are documents: the workbench keeps them in one global
 * strip so switching activity never changes the panel structure.
 */

import type { ActivityId, WorkbenchSelection } from "./types";

export const ACTIVITY_ORDER: ActivityId[] = ["topology", "detail"];

export const ACTIVITY_LABELS: Record<ActivityId, string> = {
  topology: "Topology",
  detail: "Detail",
};

export const ACTIVITY_DESCRIPTIONS: Record<ActivityId, string> = {
  topology: "Canonical design view: entities, relations, properties and meaning.",
  detail: "One subject in full: meaning, properties and provenance.",
};

export const BOTTOM_TABS: Record<ActivityId, string[]> = {
  topology: ["selection"],
  detail: ["trace", "evidence"],
};

export const BOTTOM_TAB_LABELS: Record<string, string> = {
  output: "Output",
  trace: "Trace",
  evidence: "Evidence",
  details: "Details",
  graph: "Graph",
  selection: "Inspect",
};

const RETIRED_BOTTOM_TABS = new Set([
  "data",
  "json",
  "problems",
  "decisions",
  "coverage",
  "details",
  "inspect",
]);

/** A tab from an earlier workbench that is no longer a valid surface. */
export function isRetiredBottomTab(tab: string): boolean {
  return RETIRED_BOTTOM_TABS.has(tab);
}

export function bottomTabLabel(tab: string): string {
  return BOTTOM_TAB_LABELS[tab] ?? tab;
}

export function defaultBottomTab(activity: ActivityId): string {
  return BOTTOM_TABS[activity][0] ?? "output";
}

export function emptySelection(): WorkbenchSelection {
  return { kind: "graph", name: "Graph" };
}

/** Resolve a tab list that includes a restored bottom tab from a newer build. */
export function bottomTabsFor(activity: ActivityId, current: string): string[] {
  const tabs = BOTTOM_TABS[activity];
  return tabs.includes(current) || isRetiredBottomTab(current)
    ? tabs
    : [current, ...tabs];
}
