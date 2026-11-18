import { describe, expect, it } from "vitest";

import { contractIndex, contractSnapshot } from "./fixtures";
import { createWorkbenchState, workbenchReducer } from "../workbench/store";
import {
  documentTitle,
  subjectTitle,
  type WorkbenchState,
} from "../workbench/types";

function state(): WorkbenchState {
  return createWorkbenchState(contractSnapshot, contractIndex);
}

function activeTitle(current: WorkbenchState): string | undefined {
  const tab = current.tabs.find((candidate) => candidate.id === current.activeTabId);
  return tab ? documentTitle(tab.document) : undefined;
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
  it("starts with the canonical Graph and Workflow documents", () => {
    const initial = state();
    expect(initial.tabs).toHaveLength(2);
    expect(initial.tabs[0]).toMatchObject({
      id: "graph",
      document: { kind: "graph" },
      pinned: true,
    });
    expect(initial.tabs[1]).toMatchObject({
      id: "workflow",
      document: { kind: "workflow" },
      pinned: true,
    });
    expect(activeTitle(initial)).toBe("Graph");
    expect(initial.inspection).toBeUndefined();
    expect(initial.layout.sidebarWidth).toBe(300);
  });

  it("resizes one geometry for every document", () => {
    const current = workbenchReducer(state(), {
      type: "set-layout",
      patch: { sidebarWidth: 348 },
    });
    expect(current.layout.sidebarWidth).toBe(348);
  });

  it("clamps the side-bar width", () => {
    const current = workbenchReducer(state(), {
      type: "set-layout",
      patch: { sidebarWidth: 999 },
    });
    expect(current.layout.sidebarWidth).toBe(520);
  });

  it("reuses one preview tab for single-click navigation", () => {
    let current = workbenchReducer(state(), {
      type: "open-tab",
      input: { selection: defectNode, preview: true },
    });
    expect(current.tabs).toHaveLength(3);
    expect(current.tabs[2].preview).toBe(true);

    current = workbenchReducer(current, {
      type: "open-tab",
      input: { selection: defectProperty, preview: true },
    });
    expect(current.tabs).toHaveLength(3);
    expect(current.tabs.map((tab) => documentTitle(tab.document))).toEqual([
      "Graph",
      "Workflow",
      "defect.title",
    ]);
    expect(activeTitle(current)).toBe("defect.title");
    expect(current.tabs[2].preview).toBe(true);
  });

  it("keeps preview ids unique when the shown subject changes", () => {
    let current = workbenchReducer(state(), {
      type: "open-tab",
      input: { selection: defectNode, preview: true },
    });
    current = workbenchReducer(current, {
      type: "open-tab",
      input: { selection: defectProperty, preview: true },
    });
    current = workbenchReducer(current, {
      type: "open-tab",
      input: { selection: defectNode },
    });
    expect(current.tabs.map((tab) => documentTitle(tab.document))).toEqual([
      "Graph",
      "Workflow",
      "defect.title",
      "defect",
    ]);
    expect(new Set(current.tabs.map((tab) => tab.id)).size).toBe(4);
  });

  it("promotes a preview tab when the document is opened explicitly", () => {
    let current = workbenchReducer(state(), {
      type: "open-tab",
      input: { selection: defectNode, preview: true },
    });
    current = workbenchReducer(current, {
      type: "open-tab",
      input: { selection: defectNode },
    });
    expect(current.tabs).toHaveLength(3);
    expect(current.tabs[2].preview).toBeUndefined();
  });

  it("pins a preview tab into a permanent document", () => {
    let current = workbenchReducer(state(), {
      type: "open-tab",
      input: { selection: defectNode, preview: true },
    });
    const previewId = current.activeTabId;
    current = workbenchReducer(current, { type: "pin-tab", tabId: previewId });
    expect(current.tabs[2].preview).toBeUndefined();

    current = workbenchReducer(current, {
      type: "open-tab",
      input: { selection: defectProperty, preview: true },
    });
    // The former preview was pinned, so the new preview needs its own tab.
    expect(current.tabs).toHaveLength(4);
  });

  it("inspects without opening a document", () => {
    const inspected = workbenchReducer(state(), {
      type: "inspect",
      selection: defectNode,
    });
    expect(inspected.tabs).toHaveLength(2);
    expect(inspected.inspection).toMatchObject(defectNode);
    expect(inspected.activeTabId).toBe("graph");
  });

  it("opens and reuses subject documents", () => {
    const opened = workbenchReducer(state(), {
      type: "open-tab",
      input: { selection: defectNode },
    });
    expect(opened.tabs.map((tab) => documentTitle(tab.document))).toEqual([
      "Graph",
      "Workflow",
      "defect",
    ]);
    const again = workbenchReducer(opened, {
      type: "open-tab",
      input: { selection: defectNode },
    });
    expect(again.tabs).toHaveLength(3);
  });

  it("deduplicates equivalent explorer and pill selections", () => {
    // The Explorer supplies a display name and level; a pill supplies the
    // component alone. They are the same document and must reuse one tab.
    let current = workbenchReducer(state(), {
      type: "open-tab",
      input: { selection: defectNode },
    });
    current = workbenchReducer(current, {
      type: "open-tab",
      input: {
        selection: { kind: "node", level: "node", component: "defect" },
        preview: true,
      },
    });
    expect(current.tabs).toHaveLength(3);
    expect(
      current.tabs.filter((tab) => documentTitle(tab.document) === "defect"),
    ).toHaveLength(1);

    current = workbenchReducer(current, {
      type: "open-tab",
      input: {
        selection: {
          kind: "edge",
          level: "edge",
          component: "target_belongs_to_class",
          name: "target_belongs_to_class",
        },
      },
    });
    current = workbenchReducer(current, {
      type: "open-tab",
      input: {
        selection: {
          kind: "edge",
          level: "edge",
          component: "target_belongs_to_class",
        },
        preview: true,
      },
    });
    expect(
      current.tabs.filter(
        (tab) => documentTitle(tab.document) === "target_belongs_to_class",
      ),
    ).toHaveLength(1);
  });

  it("deduplicates a property with or without its qualified display name", () => {
    let current = workbenchReducer(state(), {
      type: "open-tab",
      input: { selection: defectProperty },
    });
    current = workbenchReducer(current, {
      type: "open-tab",
      input: {
        selection: {
          kind: "property",
          level: "property",
          component: "defect",
          property: "title",
          name: "title",
        },
      },
    });
    expect(current.tabs).toHaveLength(3);
    expect(activeTitle(current)).toBe("defect.title");
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
    expect(current.tabs.map((tab) => documentTitle(tab.document))).toEqual([
      "Graph",
      "Workflow",
      "defect",
      "defect.title",
    ]);

    current = workbenchReducer(current, { type: "back" });
    expect(activeTitle(current)).toBe("defect");

    current = workbenchReducer(current, { type: "forward" });
    expect(activeTitle(current)).toBe("defect.title");
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
    expect(activeTitle(current)).toBe("defect.title");
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
    expect(current.tabs.map((tab) => documentTitle(tab.document))).toEqual([
      "Graph",
      "Workflow",
      "defect",
    ]);
    expect(activeTitle(current)).toBe("defect");
  });

  it("opens a background tab without changing the active view", () => {
    let current = workbenchReducer(state(), {
      type: "open-tab",
      input: { selection: defectNode, background: true },
    });
    expect(current.tabs.map((tab) => documentTitle(tab.document))).toEqual([
      "Graph",
      "Workflow",
      "defect",
    ]);
    expect(activeTitle(current)).toBe("Graph");
    expect(current.history).toHaveLength(1);

    current = workbenchReducer(current, {
      type: "open-tab",
      input: { selection: defectProperty, background: true },
    });
    expect(current.tabs.map((tab) => documentTitle(tab.document))).toEqual([
      "Graph",
      "Workflow",
      "defect",
      "defect.title",
    ]);
    expect(activeTitle(current)).toBe("Graph");
    expect(current.history).toHaveLength(1);

    current = workbenchReducer(current, {
      type: "open-tab",
      input: { selection: defectNode },
    });
    expect(activeTitle(current)).toBe("defect");
    expect(current.tabs).toHaveLength(4);
  });

  it("reopens a closed view when history reaches it", () => {
    let current = workbenchReducer(state(), {
      type: "open-tab",
      input: { selection: defectNode },
    });
    current = workbenchReducer(current, {
      type: "open-tab",
      input: { selection: defectProperty },
    });
    const nodeTab = current.tabs.find(
      (tab) => documentTitle(tab.document) === "defect",
    );
    expect(nodeTab).toBeTruthy();
    current = workbenchReducer(current, {
      type: "close-tab",
      tabId: nodeTab!.id,
    });
    expect(current.tabs.map((tab) => documentTitle(tab.document))).toEqual([
      "Graph",
      "Workflow",
      "defect.title",
    ]);
    expect(current.history).toHaveLength(3);

    current = workbenchReducer(current, { type: "back" });
    expect(activeTitle(current)).toBe("defect");
    expect(current.tabs.map((tab) => documentTitle(tab.document))).toEqual([
      "Graph",
      "Workflow",
      "defect.title",
      "defect",
    ]);
    expect(
      current.tabs.find(
        (tab) => documentTitle(tab.document) === "defect",
      )?.preview,
    ).toBe(true);
    expect(current.historyIndex).toBe(1);

    current = workbenchReducer(current, { type: "forward" });
    expect(activeTitle(current)).toBe("defect.title");
  });

  it("reopens the closed active view from history", () => {
    let current = workbenchReducer(state(), {
      type: "open-tab",
      input: { selection: defectNode },
    });
    current = workbenchReducer(current, {
      type: "open-tab",
      input: { selection: defectProperty },
    });
    const propertyTab = current.tabs.find(
      (tab) => documentTitle(tab.document) === "defect.title",
    );
    expect(propertyTab).toBeTruthy();
    current = workbenchReducer(current, {
      type: "close-tab",
      tabId: propertyTab!.id,
    });
    expect(activeTitle(current)).toBe("defect");

    current = workbenchReducer(current, { type: "back" });
    expect(activeTitle(current)).toBe("defect.title");
    expect(current.tabs.map((tab) => documentTitle(tab.document))).toEqual([
      "Graph",
      "Workflow",
      "defect",
      "defect.title",
    ]);
    expect(
      current.tabs.find(
        (tab) => documentTitle(tab.document) === "defect.title",
      )?.preview,
    ).toBe(true);
  });

  it("titles a step document by its step name", () => {
    expect(
      subjectTitle({
        kind: "step",
        component: "core",
        name: "binding.0",
        stepId: ["core", "binding.0"],
      }),
    ).toBe("binding.0");
  });

  it("keeps two bindings of one record as distinct documents", () => {
    let current = state();
    current = workbenchReducer(current, {
      type: "open-tab",
      input: {
        selection: {
          kind: "binding",
          component: "defect",
          name: "binding #0",
          bindingIndex: 0,
        },
      },
    });
    current = workbenchReducer(current, {
      type: "open-tab",
      input: {
        selection: {
          kind: "binding",
          component: "defect",
          name: "binding #1",
          bindingIndex: 1,
        },
      },
    });
    expect(current.tabs.map((tab) => documentTitle(tab.document))).toEqual([
      "Graph",
      "Workflow",
      "binding #0",
      "binding #1",
    ]);
    expect(subjectTitle({
      kind: "binding",
      component: "defect",
      name: "#1",
      bindingIndex: 1,
    })).toBe("binding #1");
  });

  it("opens a virtual collection as its own document", () => {
    const current = workbenchReducer(state(), {
      type: "open-tab",
      input: {
        selection: {
          kind: "collection" as const,
          collection: "derivedRelations" as const,
          name: "Derived relations",
        },
        preview: true,
      },
    });
    expect(activeTitle(current)).toBe("Derived relations");
    expect(current.tabs.at(-1)?.document).toMatchObject({
      kind: "subject",
      selection: { kind: "collection", collection: "derivedRelations" },
    });
  });

  it("keys a collection document by its collection and component", () => {
    const derived = workbenchReducer(state(), {
      type: "open-tab",
      input: {
        selection: { kind: "collection", collection: "derivedRelations" },
      },
    });
    const component = workbenchReducer(derived, {
      type: "open-tab",
      input: {
        selection: {
          kind: "collection",
          collection: "workflow",
          component: "duckdb",
        },
      },
    });
    expect(component.tabs).toHaveLength(4);
    expect(activeTitle(component)).toBe("duckdb");
  });

  it("does not close the pinned Graph or Workflow document", () => {
    const initial = state();
    const afterGraph = workbenchReducer(initial, {
      type: "close-tab",
      tabId: "graph",
    });
    expect(afterGraph.tabs).toHaveLength(2);
    const afterWorkflow = workbenchReducer(afterGraph, {
      type: "close-tab",
      tabId: "workflow",
    });
    expect(afterWorkflow.tabs).toHaveLength(2);
  });
});
