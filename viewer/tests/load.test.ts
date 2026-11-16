import { describe, expect, it } from "vitest";
import { loadSnapshotFromObject, loadSnapshotFromText } from "../lib/load";
import { contractSnapshot as snapshot } from "./fixtures";

describe("snapshot loading", () => {
  it("loads the contract fixture with its graph declaration", () => {
    expect(snapshot.format).toBe("kg-viewer-snapshot");
    expect(snapshot.version).toBe(1);
    expect(snapshot.name).toBe("fixture-estate");
    expect(snapshot.title).toBe("Fixture Estate Build");
    expect(snapshot.blueprint.graph.nodes).toHaveLength(2);
    expect(snapshot.blueprint.graph.edges).toHaveLength(1);
    expect(snapshot.blueprint.bindings).toHaveLength(1);
    expect(snapshot.workflow.steps).toHaveLength(2);
    expect(snapshot.workflow.connections).toHaveLength(1);

    const declaration = snapshot.blueprint.graph_declaration;
    expect(declaration?.name).toBe("fixture_graph");
    expect(declaration?.meaning?.claims).toHaveLength(1);
    expect(declaration?.meaning?.purpose?.text).toBe(
      "Exercise the viewer data contract without loading a release.",
    );
    expect(declaration?.meaning?.purpose?.limitations).toHaveLength(2);
  });

  it("loads asset profiles and attached semantics on every subject", () => {
    const asset = snapshot.blueprint.assets[0];
    expect(asset.profile).toMatchObject({
      subject: "a monitored estate",
      coverage: "the estate survey table",
      authority: "primary",
      basis: "synthetic fixture data",
    });
    expect(asset.semantics?.claims?.[0].text).toBe(
      "The fixture estate is a JSON asset.",
    );

    const relation = snapshot.blueprint.data.source_relations[0];
    expect(relation.semantics?.claims).toHaveLength(1);
    expect(relation.columns[1].semantics?.claims).toHaveLength(1);

    const projection = snapshot.blueprint.data.derived_relations[0];
    expect(projection.semantics?.claims).toHaveLength(1);
    expect(projection.columns[1].semantics?.claims).toHaveLength(1);

    const struct = snapshot.blueprint.data.structs[0];
    expect(struct.semantics?.claims).toHaveLength(1);
    expect(struct.columns[0].semantics?.claims).toHaveLength(1);

    const node = snapshot.blueprint.graph.nodes.find((entry) => entry.name === "defect");
    expect(node?.semantics?.claims).toHaveLength(1);
    expect(node?.properties?.[0].semantics?.claims).toHaveLength(1);

    const edge = snapshot.blueprint.graph.edges[0];
    expect(edge.semantics?.claims).toHaveLength(1);
    expect(edge.properties?.[0].semantics?.claims).toHaveLength(1);

    const binding = snapshot.blueprint.bindings[0];
    expect(binding.semantics?.claims?.[0].text).toBe(
      "The binding projects the survey title.",
    );
    expect(binding.name).toBe("defect.title");
    expect(binding.mode).toBe("merge");
    expect(binding.python_ref?.qualname).toBe("DefectTitle");
  });

  it("preserves unknown fields on the blueprint and on entities", () => {
    expect(
      (snapshot.blueprint as unknown as Record<string, unknown>).contract_extension,
    ).toEqual({ generatedBy: "tests/fixtures.ts" });
    const node = snapshot.blueprint.graph.nodes.find((entry) => entry.name === "defect");
    expect((node as Record<string, unknown>).x_node_field).toBe("survives");
    expect(
      (snapshot.blueprint.assets[0] as Record<string, unknown>).x_asset_field,
    ).toBe("survives");
    expect(
      (snapshot.blueprint.assets[0].semantics as unknown as Record<string, unknown>)
        .x_semantics_field,
    ).toBe("survives");
  });

  it("allows a snapshot without a graph declaration", () => {
    const loaded = loadSnapshotFromObject({
      format: "kg-viewer-snapshot",
      version: 1,
      name: "legacy",
      title: "Legacy snapshot",
      blueprint: {
        graph: { nodes: [], edges: [] },
        data: {
        structs: [],
        source_relations: [],
        derived_relations: [],
      },
        assets: [],
        bindings: [],
      },
      workflow: { components: [], steps: [], connections: [], provenance: null },
      report: {
        published_artifacts: [],
        recovered_failures: [],
        unresolved_failures: [],
        provenance: null,
      },
    });
    expect(loaded.blueprint.graph_declaration).toBeUndefined();
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

  it("reads the source blueprint from workflow provenance", () => {
    const loaded = loadSnapshotFromObject({
      name: "embedded",
      title: "Embedded blueprint",
      components: [{ id: "core", version: "1" }],
      steps: [],
      connections: [],
      provenance: {
        blueprint: {
          graph: { nodes: [{ name: "site" }], edges: [] },
          data: {
        structs: [],
        source_relations: [],
        derived_relations: [],
      },
          assets: [{ name: "estate" }],
          bindings: [],
        },
      },
    });
    expect(loaded.blueprint.graph.nodes[0].name).toBe("site");
    expect(loaded.blueprint.assets[0].name).toBe("estate");
    expect(loaded.workflow.provenance?.blueprint).toBeDefined();
  });

  it("accepts a bare blueprint and keeps unknown fields", () => {
    const loaded = loadSnapshotFromObject({
      graph: { nodes: [{ name: "site" }], edges: [] },
      data: {
        structs: [],
        source_relations: [],
        derived_relations: [],
      },
      assets: [{ name: "estate" }],
      bindings: [],
      local_extension: { kept: true },
    });
    expect(loaded.title).toBe("Blueprint");
    expect(loaded.blueprint.graph.nodes[0].name).toBe("site");
    expect(loaded.workflow.steps).toEqual([]);
    expect(
      (loaded.blueprint as unknown as Record<string, unknown>).local_extension,
    ).toEqual({ kept: true });
  });

  it("rejects malformed JSON text", () => {
    expect(() => loadSnapshotFromText("{")).toThrow(/Invalid JSON/);
  });
});
