// @vitest-environment jsdom

import { describe, expect, it } from "vitest";

import {
  createReadyMessage,
  createSelectMessage,
  embedQuery,
  parentOrigin,
  parseOpenMessage,
  snapshotFromOpen,
} from "../workbench/embed";

const rawSnapshot = {
  format: "kg-viewer-snapshot",
  version: 1,
  name: "embedded",
  title: "Embedded snapshot",
  blueprint: {
    graph: { nodes: [], edges: [] },
    data: { structs: [], relations: [], projections: [] },
    assets: [],
    bindings: [],
  },
  workflow: {
    components: [],
    steps: [],
    connections: [],
    provenance: null,
  },
};

describe("embed bridge contract", () => {
  it("enables the bridge only for embed=1", () => {
    expect(embedQuery("?embed=1")).toEqual({ enabled: true, snapshot: undefined });
    expect(embedQuery("?embed=0")).toEqual({ enabled: false, snapshot: undefined });
    expect(embedQuery("?snapshot=https%3A%2F%2Fexample.test%2Fs.json")).toEqual({
      enabled: false,
      snapshot: "https://example.test/s.json",
    });
  });

  it("builds ready and select envelopes", () => {
    expect(createReadyMessage()).toEqual({ type: "ready" });
    expect(createReadyMessage("embedded")).toEqual({
      type: "ready",
      snapshot: "embedded",
    });
    expect(
      createSelectMessage({
        kind: "property",
        component: "defect",
        property: "title",
        name: "defect.title",
      }),
    ).toEqual({
      type: "select",
      subject: {
        kind: "property",
        component: "defect",
        property: "title",
        name: "defect.title",
      },
    });
  });

  it("accepts an open message with a parsed snapshot", () => {
    const open = parseOpenMessage({
      type: "open",
      snapshot: rawSnapshot,
      requestId: "req-1",
    });
    expect(open?.type).toBe("open");
    expect(open?.snapshot).toEqual(rawSnapshot);
    expect(open?.requestId).toBe("req-1");
  });

  it("accepts an open message with raw JSON text", () => {
    const open = parseOpenMessage({
      type: "open",
      snapshot: JSON.stringify(rawSnapshot),
    });
    expect(open).not.toBeNull();
    const snapshot = snapshotFromOpen(open?.snapshot);
    expect(snapshot.name).toBe("embedded");
    expect(snapshot.title).toBe("Embedded snapshot");
  });

  it("normalises a parsed snapshot", () => {
    const snapshot = snapshotFromOpen(rawSnapshot);
    expect(snapshot.format).toBe("kg-viewer-snapshot");
    expect(snapshot.workflow.steps).toEqual([]);
  });

  it("ignores messages that are not open", () => {
    expect(parseOpenMessage({ type: "select", subject: {} })).toBeNull();
    expect(parseOpenMessage({ type: "open" })).toBeNull();
    expect(parseOpenMessage("open")).toBeNull();
    expect(parseOpenMessage(null)).toBeNull();
  });

  it("falls back to * when the referrer is absent", () => {
    expect(parentOrigin()).toBe("*");
  });
});
