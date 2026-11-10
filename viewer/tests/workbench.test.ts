import { describe, expect, it } from "vitest";

import { contractIndex, contractSnapshot } from "./fixtures";
import { createWorkbenchState, workbenchReducer } from "../workbench/store";
import type { WorkbenchState } from "../workbench/types";

function state(): WorkbenchState {
  return createWorkbenchState(contractSnapshot, contractIndex);
}

const targetNode = {
  activity: "detail" as const,
  kind: "node" as const,
  level: "node" as const,
  component: "defect",
  name: "defect",
};

const targetProperty = {
  activity: "detail" as const,
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
      activity: "topology",
      pinned: true,
    });
    expect(initial.activity).toBe("topology");
    expect(initial.layout.sidebarWidth).toBe(300);
    expect(initial.layout.bottomHeight).toBe(240);
  });

  it("keeps one geometry when the activity changes", () => {
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

  it("updates the graph selection when a topology subject is opened", () => {
    const opened = workbenchReducer(state(), {
      type: "open-tab",
      input: {
        activity: "topology",
        selection: {
          activity: "topology",
          kind: "node",
          name: "defect",
        },
      },
    });
    expect(opened.tabs).toHaveLength(1);
    expect(opened.tabs[0].selection).toMatchObject({
      kind: "node",
      name: "defect",
    });
  });

  it("opens a detail tab, then reuses it for the same subject", () => {
    const opened = workbenchReducer(state(), {
      type: "open-tab",
      input: { activity: "detail", selection: targetNode },
    });
    expect(opened.tabs.map((tab) => tab.title)).toEqual(["Graph", "defect"]);
    const again = workbenchReducer(opened, {
      type: "open-tab",
      input: { activity: "detail", selection: targetNode },
    });
    expect(again.tabs).toHaveLength(2);
  });

  it("adds a property tab and walks back and forward", () => {
    let current = workbenchReducer(state(), {
      type: "open-tab",
      input: { activity: "detail", selection: targetNode },
    });
    current = workbenchReducer(current, {
      type: "open-tab",
      input: { activity: "detail", selection: targetProperty },
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
    expect(current.tabs.find((tab) => tab.id === current.activeTabId)?.title).toBe(
      "defect.title",
    );
  });

  it("updates the active tab title on selection without a history step", () => {
    let current = workbenchReducer(state(), {
      type: "set-activity",
      activity: "detail",
    });
    const historyLength = current.history.length;
    current = workbenchReducer(current, {
      type: "set-selection",
      activity: "detail",
      selection: targetProperty,
    });
    expect(current.history).toHaveLength(historyLength);
    expect(current.tabs.find((tab) => tab.id === current.activeTabId)?.title).toBe(
      "defect.title",
    );
  });

  it("closes a detail tab and falls back to the previous editor", () => {
    let current = workbenchReducer(state(), {
      type: "open-tab",
      input: { activity: "detail", selection: targetNode },
    });
    current = workbenchReducer(current, {
      type: "open-tab",
      input: { activity: "detail", selection: targetProperty },
    });
    const propertyId = current.activeTabId;
    current = workbenchReducer(current, { type: "close-tab", tabId: propertyId });
    expect(current.tabs.map((tab) => tab.title)).toEqual(["Graph", "defect"]);
    expect(current.tabs.find((tab) => tab.id === current.activeTabId)?.title).toBe(
      "defect",
    );
  });
});
