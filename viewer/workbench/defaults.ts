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
  "semantics",
  "audit",
  "proof",
  "topology",
];

export const ACTIVITY_LABELS: Record<ActivityId, string> = {
  semantics: "Orient",
  audit: "Audit",
  proof: "Proof",
  topology: "Topology",
};

export const ACTIVITY_DESCRIPTIONS: Record<ActivityId, string> = {
  semantics: "Understand the graph purpose, frames, claims and limits before auditing.",
  audit: "Identity, grounding, type/presence and semantics findings.",
  proof: "Multi-level value provenance with attached semantics.",
  topology: "Force-directed orientation view of the graph.",
};

export interface ActivityTabs {
  bottomTabs: string[];
  openTabs: string[];
  activeTab: string;
}

export const DEFAULT_TABS: Record<ActivityId, ActivityTabs> = {
  proof: {
    bottomTabs: ["trace", "evidence", "data"],
    openTabs: ["Provenance"],
    activeTab: "Provenance",
  },
  audit: {
    bottomTabs: ["problems", "evidence", "data"],
    openTabs: ["Findings"],
    activeTab: "Findings",
  },
  semantics: {
    bottomTabs: ["decisions", "coverage", "data"],
    openTabs: ["Ledger"],
    activeTab: "Ledger",
  },
  topology: {
    bottomTabs: ["selection", "data"],
    openTabs: ["Graph"],
    activeTab: "Graph",
  },
};

export const BOTTOM_TAB_LABELS: Record<string, string> = {
  problems: "Problems",
  output: "Output",
  trace: "Trace",
  evidence: "Evidence",
  data: "Data",
  decisions: "Decisions",
  coverage: "Coverage",
  selection: "Selection",
};

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
    proof: defaultFunctionState("proof"),
    audit: defaultFunctionState("audit"),
    semantics: defaultFunctionState("semantics"),
    topology: defaultFunctionState("topology"),
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
  return tabs.includes(current) ? [...tabs] : [current, ...tabs];
}
