/**
 * Workbench defaults.
 *
 * The side bar exposes Topology and Detail as collapsible sections. The tab
 * strip is the document axis; the bottom tabs belong to the document view.
 */

import type { TabView } from "./types";

export const BOTTOM_TABS: Record<TabView, string[]> = {
  graph: ["selection"],
  subject: ["trace", "evidence"],
};

export const BOTTOM_TAB_LABELS: Record<string, string> = {
  output: "Output",
  trace: "Trace",
  evidence: "Evidence",
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

export function isRetiredBottomTab(tab: string): boolean {
  return RETIRED_BOTTOM_TABS.has(tab);
}

export function bottomTabLabel(tab: string): string {
  return BOTTOM_TAB_LABELS[tab] ?? tab;
}

export function defaultBottomTab(view: TabView): string {
  return BOTTOM_TABS[view][0] ?? "output";
}

export function bottomTabsFor(view: TabView, current: string): string[] {
  const tabs = BOTTOM_TABS[view];
  return tabs.includes(current) || isRetiredBottomTab(current)
    ? tabs
    : [current, ...tabs];
}
