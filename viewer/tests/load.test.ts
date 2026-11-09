import { describe, expect, it } from "vitest";
import { loadSnapshotFromObject, loadSnapshotFromText } from "../lib/load";
import { snapshot } from "./fixtures";

describe("snapshot loading", () => {
  it("loads the reference snapshot", () => {
    expect(snapshot.format).toBe("kg-viewer-snapshot");
    expect(snapshot.version).toBe(1);
    expect(snapshot.name).toBe("reference-estate");
    expect(snapshot.title).toBe("Monitored Estate Reference Build");
    expect(snapshot.blueprint.graph.nodes).toHaveLength(7);
    expect(snapshot.blueprint.graph.edges).toHaveLength(7);
    expect(snapshot.blueprint.bindings).toHaveLength(14);
    expect(snapshot.workflow.steps).toHaveLength(60);
    expect(snapshot.workflow.connections).toHaveLength(90);
    expect(snapshot.report.published_artifacts.length).toBeGreaterThan(0);
    expect(snapshot.metaGraph?.nodes).toHaveLength(7);
  });

  it("accepts a bare workflow plan", () => {
    const loaded = loadSnapshotFromObject({
      components: [{ id: "core", version: "1" }],
      steps: [],
      connections: [],
      provenance: null,
    });
    expect(loaded.title).toBe("Workflow plan");
    expect(loaded.workflow.components[0].id).toBe("core");
    expect(loaded.blueprint.assets).toEqual([]);
  });

  it("accepts a bare blueprint", () => {
    const loaded = loadSnapshotFromObject({
      graph: { nodes: [{ name: "site" }], edges: [] },
      data: { structures: [], relations: [], projections: [] },
      assets: [{ name: "estate" }],
      bindings: [],
    });
    expect(loaded.title).toBe("Blueprint");
    expect(loaded.blueprint.graph.nodes[0].name).toBe("site");
    expect(loaded.workflow.steps).toEqual([]);
  });

  it("rejects malformed JSON text", () => {
    expect(() => loadSnapshotFromText("{")).toThrow(/Invalid JSON/);
  });
});
