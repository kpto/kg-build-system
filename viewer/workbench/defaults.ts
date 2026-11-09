/**
 * Workbench defaults.
 *
 * The shell owns the default arrangement of each function and the tab names an
 * empty function opens with. A function may open more tabs later; the shell
 * persists whatever is open without knowing what the tab means.
 */

import type {
  ActivityId,
  FunctionLayout,
  FunctionState,
  WorkbenchSelection,
} from "./types";
import { DEFAULT_LAYOUT } from "./types";

export const ACTIVITY_ORDER: ActivityId[] = [
  "topology",
  "proof",
  "meaning",
];

export const ACTIVITY_LABELS: Record<ActivityId, string> = {
  topology: "Topology",
  proof: "Proof",
  meaning: "Meaning",
};

export const ACTIVITY_DESCRIPTIONS: Record<ActivityId, string> = {
  topology: "Force-directed view of the graph and its relations.",
  proof: "Multi-level value provenance with attached semantics.",
  meaning: "Read the graph purpose, frames, claims and limits.",
};

export interface ActivityTabs {
  bottomTabs: string[];
  openTabs: string[];
  activeTab: string;
}

export const DEFAULT_TABS: Record<ActivityId, ActivityTabs> = {
  topology: {
    bottomTabs: ["selection"],
    openTabs: ["Graph"],
    activeTab: "Graph",
  },
  proof: {
    bottomTabs: ["trace", "evidence"],
    openTabs: ["Provenance"],
    activeTab: "Provenance",
  },
  meaning: {
    bottomTabs: ["details"],
    openTabs: ["Meaning"],
    activeTab: "Meaning",
  },
};

export const BOTTOM_TAB_LABELS: Record<string, string> = {
  output: "Output",
  trace: "Trace",
  evidence: "Evidence",
  details: "Details",
  selection: "Selection",
};

const RETIRED_BOTTOM_TABS = new Set([
  "data",
  "json",
  "problems",
  "decisions",
  "coverage",
]);

/** A tab from an earlier workbench that is no longer a valid surface. */
export function isRetiredBottomTab(tab: string): boolean {
  return RETIRED_BOTTOM_TABS.has(tab);
}

export function bottomTabLabel(tab: string): string {
  return BOTTOM_TAB_LABELS[tab] ?? tab;
}

/** Display a tab identity without leaking the internal subject prefix. */
export function editorTabLabel(tab: string): string {
  if (tab.startsWith("subject:")) {
    const rest = tab.slice("subject:".length);
    const separator = rest.indexOf(":");
    return separator >= 0 ? rest.slice(separator + 1) : rest;
  }
  return tab;
}

export function selectionTab(kind: string, name: string): string {
  return `subject:${kind}:${name}`;
}

export function defaultFunctionState(activity: ActivityId): FunctionState {
  const tabs = DEFAULT_TABS[activity];
  return {
    layout: {
      ...DEFAULT_LAYOUT,
      bottomTab: tabs.bottomTabs[0] ?? DEFAULT_LAYOUT.bottomTab,
      openTabs: [...tabs.openTabs],
      activeTab: tabs.activeTab,
    },
    selection: { activity },
  };
}

export function defaultFunctions(): Record<ActivityId, FunctionState> {
  return {
    topology: defaultFunctionState("topology"),
    proof: defaultFunctionState("proof"),
    meaning: defaultFunctionState("meaning"),
  };
}

export function emptySelection(activity: ActivityId): WorkbenchSelection {
  return { activity };
}

/** Resolve a tab list that includes a restored bottom tab from a newer build. */
export function bottomTabsFor(
  activity: ActivityId,
  current: string,
): string[] {
  const tabs = DEFAULT_TABS[activity].bottomTabs;
  return tabs.includes(current) || isRetiredBottomTab(current)
    ? [...tabs]
    : [current, ...tabs];
}
