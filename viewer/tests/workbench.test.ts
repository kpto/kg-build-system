import { describe, expect, it } from "vitest";

import { contractIndex, contractSnapshot } from "./fixtures";
import { createWorkbenchState, workbenchReducer } from "../workbench/store";
import type { WorkbenchState } from "../workbench/types";

function state(): WorkbenchState {
  return createWorkbenchState(contractSnapshot, contractIndex);
}

const defectNode = {
  kind: "node" as const,
  level: "node" as const,
  component: "defect",
  name: "defect",
};

const defectProperty = {
  kind: "property" as const,
  level: "property" as const,
  component: "defect",
  property: "title",
  name: "defect.title",
};

describe("workbench tabs and geometry", () => {
  it("starts with one pinned canonical graph tab", () => {
    const initial = state();
    expect(initial.tabs).toHaveLength(1);
    expect(initial.tabs[0]).toMatchObject({
      id: "graph",
      title: "Graph",
      selection: { kind: "graph" },
      pinned: true,
    });
    expect(initial.activity).toBe("topology");
    expect(initial.layout.sidebarWidth).toBe(300);
    expect(initial.layout.bottomHeight).toBe(240);
  });

  it("keeps one geometry when the mode changes", () => {
    const resized = workbenchReducer(state(), {
      type: "set-layout",
      patch: { sidebarWidth: 348, bottomHeight: 276 },
    });
    const detail = workbenchReducer(resized, {
      type: "set-activity",
      activity: "detail",
    });
    expect(detail.layout.sidebarWidth).toBe(348);
    expect(detail.layout.bottomHeight).toBe(276);
    expect(detail.activity).toBe("detail");
  });

  it("does not change the active tab when the mode changes", () => {
    let current = workbenchReducer(state(), {
      type: "open-tab",
      input: { selection: defectProperty },
    });
    const tabId = current.activeTabId;
    current = workbenchReducer(current, {
      type: "set-activity",
      activity: "detail",
    });
    expect(current.activity).toBe("detail");
    expect(current.activeTabId).toBe(tabId);
    expect(
      current.tabs.find((tab) => tab.id === current.activeTabId)?.selection,
    ).toEqual(defectProperty);

    current = workbenchReducer(current, {
      type: "set-activity",
      activity: "topology",
    });
    expect(current.activity).toBe("topology");
    expect(current.activeTabId).toBe(tabId);
  });

  it("does not change the mode when a tab is activated", () => {
    let current = workbenchReducer(state(), { type: "set-activity", activity: "detail" });
    current = workbenchReducer(current, {
      type: "open-tab",
      input: { selection: defectNode },
    });
    expect(current.activity).toBe("detail");
    current = workbenchReducer(current, {
      type: "activate-tab",
      tabId: "graph",
    });
    expect(current.activity).toBe("detail");
    expect(current.tabs.find((tab) => tab.id === current.activeTabId)?.title).toBe(
      "Graph",
    );
  });

  it("inspects a node without opening a document tab", () => {
    const inspected = workbenchReducer(state(), {
      type: "inspect",
      selection: { kind: "node", name: "defect" },
    });
    expect(inspected.tabs).toHaveLength(1);
    expect(inspected.tabs[0].selection).toMatchObject({ kind: "graph" });
    expect(inspected.inspection).toMatchObject({ kind: "node", name: "defect" });
    expect(inspected.activeTabId).toBe("graph");
  });

  it("keeps the graph tab as a graph document when a subject opens", () => {
    const opened = workbenchReducer(state(), {
      type: "open-tab",
      input: { selection: defectNode },
    });
    expect(opened.tabs).toHaveLength(2);
    expect(opened.tabs[0].selection).toMatchObject({ kind: "graph" });
    expect(opened.tabs[1].selection).toMatchObject({
      kind: "node",
      name: "defect",
    });
  });

  it("opens a subject tab, then reuses it for the same subject", () => {
    const opened = workbenchReducer(state(), {
      type: "open-tab",
      input: { selection: defectNode },
    });
    expect(opened.tabs.map((tab) => tab.title)).toEqual(["Graph", "defect"]);
    const again = workbenchReducer(opened, {
      type: "open-tab",
      input: { selection: defectNode },
    });
    expect(again.tabs).toHaveLength(2);
  });

  it("adds a property tab and walks back and forward without changing mode", () => {
    let current = workbenchReducer(state(), { type: "set-activity", activity: "detail" });
    current = workbenchReducer(current, {
      type: "open-tab",
      input: { selection: defectNode },
    });
    current = workbenchReducer(current, {
      type: "open-tab",
      input: { selection: defectProperty },
    });
    expect(current.tabs.map((tab) => tab.title)).toEqual([
      "Graph",
      "defect",
      "defect.title",
    ]);

    current = workbenchReducer(current, { type: "back" });
    expect(current.activity).toBe("detail");
    expect(current.tabs.find((tab) => tab.id === current.activeTabId)?.title).toBe(
      "defect",
    );

    current = workbenchReducer(current, { type: "forward" });
    expect(current.activity).toBe("detail");
    expect(current.tabs.find((tab) => tab.id === current.activeTabId)?.title).toBe(
      "defect.title",
    );
  });

  it("updates the active tab selection without a history step", () => {
    let current = workbenchReducer(state(), { type: "set-activity", activity: "detail" });
    const historyLength = current.history.length;
    current = workbenchReducer(current, {
      type: "set-selection",
      selection: defectProperty,
    });
    expect(current.history).toHaveLength(historyLength);
    expect(current.tabs.find((tab) => tab.id === current.activeTabId)?.title).toBe(
      "defect.title",
    );
  });

  it("closes a subject tab and falls back to the previous document", () => {
    let current = workbenchReducer(state(), {
      type: "open-tab",
      input: { selection: defectNode },
    });
    current = workbenchReducer(current, {
      type: "open-tab",
      input: { selection: defectProperty },
    });
    const propertyId = current.activeTabId;
    current = workbenchReducer(current, { type: "close-tab", tabId: propertyId });
    expect(current.tabs.map((tab) => tab.title)).toEqual(["Graph", "defect"]);
    expect(current.tabs.find((tab) => tab.id === current.activeTabId)?.title).toBe(
      "defect",
    );
  });
});
