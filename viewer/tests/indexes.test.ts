import { describe, expect, it } from "vitest";
import {
  artifactKey,
  buildViewerIndex,
  findComponentPropertyBindings,
  normalizeConnection,
  openingMatchesStep,
  propertyRefKey,
  stepInputConnections,
  stepKey,
  stepOutputConnections,
} from "../lib/indexes";
import { index } from "./fixtures";

const binding0: [string, string] = ["core", "binding.0"];
const binding4: [string, string] = ["core", "binding.4"];
const binding12: [string, string] = ["core", "binding.12"];

describe("workflow indexes", () => {
  it("indexes steps by id, component and emitter", () => {
    const step = index.stepsById.get(stepKey(binding0));
    expect(step?.instruction.kind).toEqual(["sql", "duckdb"]);
    expect(index.stepsByComponent.get("core")?.length).toBeGreaterThan(0);
    expect(index.stepsByEmitter.get("sql:duckdb")?.length).toBeGreaterThan(0);
    expect(index.workflow.components.map((component) => component.id)).toContain("core");
  });

  it("indexes the producer by output artifact type", () => {
    const artifact = ["core", "binding", "defect", "0"];
    expect(index.producerByArtifactKey.get(artifactKey(artifact))?.id).toEqual(binding0);
    expect(index.producersByArtifactKey.get(artifactKey(artifact))).toHaveLength(1);
  });

  it("normalizes connection prefixes and matches step-local openings as prefixes", () => {
    const raw = {
      input: ["core", "binding.0", "input", "projection.defect"],
      output: ["core", "projection.defect", "output", "output"],
    };
    const connection = normalizeConnection(raw, 0);
    expect(connection.input).toMatchObject({
      component: "core",
      step: "binding.0",
      direction: "input",
      opening: ["projection.defect"],
    });
    expect(connection.output.opening).toEqual(["output"]);
    expect(openingMatchesStep(connection.input, binding0, "input", ["projection.defect"])).toBe(
      true,
    );
    expect(openingMatchesStep(connection.output, ["core", "projection.defect"], "output", ["output"])).toBe(
      true,
    );
    expect(openingMatchesStep(connection.input, binding0, "output", ["projection.defect"])).toBe(
      false,
    );
  });

  it("matches upstream bindings by local opening", () => {
    const input = stepInputConnections(index, binding0, ["projection.defect"]);
    expect(input).toHaveLength(1);
    expect(input[0].outputStepId).toEqual(["core", "projection.defect"]);

    expect(stepInputConnections(index, binding4, ["table.temperature"])[0].outputStepId).toEqual([
      "duckdb",
      "source.temperature",
    ]);
    expect(stepInputConnections(index, binding12, ["table.temperature"])[0].outputStepId).toEqual([
      "duckdb",
      "source.temperature",
    ]);
  });

  it("matches one output opening feeding several consumers", () => {
    const connections = stepOutputConnections(index, ["deduplication", "defect"], ["distinct"]);
    expect(connections).toHaveLength(3);
    const inputSteps = connections.map((connection) => connection.inputStepId);
    expect(inputSteps).toEqual(
      expect.arrayContaining([
        ["file", "write"],
        ["meta_graph", "document"],
      ]),
    );
    expect(inputSteps.some((step) => step[0] === "neo4j")).toBe(true);
    const neo4j = connections.find((connection) => connection.input.component === "neo4j");
    expect(neo4j?.input.step.startsWith("export.node.defect")).toBe(true);
  });

  it("matches a multi-part input opening with a type suffix", () => {
    const input = stepInputConnections(
      index,
      ["file", "write"],
      ["records", "core", "graph", "node", "defect"],
    );
    expect(input).toHaveLength(1);
    expect(input[0].outputStepId).toEqual(["deduplication", "defect"]);
  });
});

describe("blueprint indexes", () => {
  it("indexes graph components, relations, projections and assets", () => {
    expect(index.topologyNodesByName.get("defect")).toBeDefined();
    expect(index.topologyEdgesByName.get("has_observation")).toBeDefined();
    expect(index.relationByName.get("surveys")?.asset).toEqual(["asset", "asset", "estate"]);
    expect(index.projectionByName.get("defect")?.row_source.kind).toBe("scan");
    expect(index.assetsByName.get("estate")?.layout?.kind).toBe("json");
  });

  it("indexes fields by relation.field", () => {
    expect(index.fieldsByKey.get("defect.title")?.ownerName).toBe("defect");
    expect(index.fieldsByKey.get("surveys.survey_id")?.ownerKind).toBe("relation");
  });

  it("indexes bindings by component and global index", () => {
    expect(index.bindings).toHaveLength(14);
    expect(index.bindings[0].component).toBe("defect");
    expect(index.bindingByComponent.get("reading")?.map((binding) => binding.index)).toEqual([
      4, 5,
    ]);
    expect(index.bindingByOutputArtifactKey.get(artifactKey(["core", "binding", "defect", "0"]))?.index).toBe(
      0,
    );
    expect(index.bindings[0].step?.id).toEqual(binding0);
  });

  it("indexes property lookup branches, including duplicate source bindings", () => {
    expect(findComponentPropertyBindings(index, "node", "defect", "title")).toHaveLength(1);
    const readingValue = findComponentPropertyBindings(index, "node", "reading", "value");
    expect(readingValue).toHaveLength(2);
    expect(readingValue.map((entry) => entry.binding.index)).toEqual([4, 5]);
    const sourceVersion = findComponentPropertyBindings(
      index,
      "node",
      "defect",
      "source_version",
    );
    expect(sourceVersion).toHaveLength(1);
    expect(sourceVersion[0].fieldRefs).toEqual([]);
    expect(propertyRefKey(sourceVersion[0].propertyRef)).toBe(
      propertyRefKey(["topology", "property", "defect.source_version"]),
    );
  });

  it("reports status counts", () => {
    expect(index.stats).toMatchObject({
      assets: 1,
      tables: 5,
      projections: 2,
      topologyNodes: 7,
      topologyEdges: 7,
      bindings: 14,
      steps: 60,
      connections: 90,
    });
  });
});

describe("viewer index rebuild", () => {
  it("accepts a snapshot with missing workflow/bindings", () => {
    const empty = buildViewerIndex({
      format: "kg-viewer-snapshot",
      version: 1,
      name: "empty",
      title: "Empty",
      blueprint: {
        graph: { nodes: [], edges: [] },
        data: { structs: [], relations: [], projections: [] },
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
    expect(empty.stats.steps).toBe(0);
    expect(empty.propertyIndex.size).toBe(0);
    expect(empty.searchRecords).toEqual([]);
  });
});
