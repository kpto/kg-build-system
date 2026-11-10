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

describe("workbench documents and geometry", () => {
  it("starts with the canonical graph document", () => {
    const initial = state();
    expect(initial.tabs).toHaveLength(1);
    expect(initial.tabs[0]).toMatchObject({
      id: "graph",
      title: "Graph",
      selection: { kind: "graph" },
      pinned: true,
    });
    expect(initial.layout.sidebarWidth).toBe(300);
    expect(initial.layout.bottomHeight).toBe(240);
    expect(initial.layout.bottomTabs).toEqual({
      graph: "selection",
      subject: "trace",
    });
  });

  it("resizes one geometry for every document", () => {
    const current = workbenchReducer(state(), {
      type: "set-layout",
      patch: { sidebarWidth: 348, bottomHeight: 276 },
    });
    expect(current.layout.sidebarWidth).toBe(348);
    expect(current.layout.bottomHeight).toBe(276);
  });

  it("inspects without opening a document", () => {
    const inspected = workbenchReducer(state(), {
      type: "inspect",
      selection: defectNode,
    });
    expect(inspected.tabs).toHaveLength(1);
    expect(inspected.inspection).toMatchObject(defectNode);
    expect(inspected.activeTabId).toBe("graph");
  });

  it("opens and reuses subject documents", () => {
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

  it("walks back and forward across documents", () => {
    let current = workbenchReducer(state(), {
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
    expect(current.tabs.find((tab) => tab.id === current.activeTabId)?.title).toBe(
      "defect",
    );

    current = workbenchReducer(current, { type: "forward" });
    expect(current.tabs.find((tab) => tab.id === current.activeTabId)?.title).toBe(
      "defect.title",
    );
  });

  it("updates the active document without a history step", () => {
    let current = workbenchReducer(state(), {
      type: "open-tab",
      input: { selection: defectNode },
    });
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

  it("closes a subject document and falls back to the previous document", () => {
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
