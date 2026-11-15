import { describe, expect, it } from "vitest";
import {
  artifactKey,
  buildViewerIndex,
  findComponentPropertyBindings,
  normalizeConnection,
  openingMatchesStep,
  propertyRefKey,
  semanticSubjectKey,
  stepInputConnections,
  stepKey,
} from "../lib/indexes";
import { contractIndex as index } from "./fixtures";

const binding0: [string, string] = ["core", "binding.0"];

describe("workflow indexes", () => {
  it("indexes steps by id, component and emitter", () => {
    const step = index.stepsById.get(stepKey(binding0));
    expect(step?.instruction.kind).toEqual(["sql", "duckdb"]);
    expect(index.stepsByComponent.get("core")?.map((entry) => entry.id)).toEqual([
      binding0,
    ]);
    expect(index.stepsByEmitter.get("sql:duckdb")).toHaveLength(2);
    expect(index.workflow.components.map((component) => component.id)).toEqual([
      "core",
      "duckdb",
    ]);
  });

  it("indexes the producer by output artifact type", () => {
    const artifact = ["core", "binding", "defect", "0"];
    expect(index.producerByArtifactKey.get(artifactKey(artifact))?.id).toEqual(
      binding0,
    );
    expect(index.producersByArtifactKey.get(artifactKey(artifact))).toHaveLength(1);
  });

  it("normalizes connection prefixes and matches step-local openings as prefixes", () => {
    const raw = {
      input: ["core", "binding.0", "input", "records"],
      output: ["duckdb", "source.surveys", "output", "output"],
    };
    const connection = normalizeConnection(raw, 0);
    expect(connection.input).toMatchObject({
      component: "core",
      step: "binding.0",
      direction: "input",
      opening: ["records"],
    });
    expect(connection.output.opening).toEqual(["output"]);
    expect(
      openingMatchesStep(connection.input, binding0, "input", ["records"]),
    ).toBe(true);
    expect(
      openingMatchesStep(
        connection.output,
        ["duckdb", "source.surveys"],
        "output",
        ["output"],
      ),
    ).toBe(true);
    expect(
      openingMatchesStep(connection.input, binding0, "output", ["records"]),
    ).toBe(false);
    expect(
      stepInputConnections(index, binding0, ["records"])[0].outputStepId,
    ).toEqual(["duckdb", "source.surveys"]);
  });
});

describe("blueprint indexes", () => {
  it("indexes graph components, relations, projections, structs and assets", () => {
    expect(index.topologyNodesByName.get("defect")).toBeDefined();
    expect(index.topologyEdgesByName.get("has_observation")).toBeDefined();
    expect(index.relationByName.get("surveys")?.asset).toEqual([
      "asset",
      "asset",
      "estate",
    ]);
    expect(index.projectionByName.get("defect")?.row_source.kind).toBe("scan");
    expect(index.structByName.get("reading")?.columns[0].name).toBe("value");
    expect(index.assetsByName.get("estate")?.layout?.kind).toBe("json");
  });

  it("indexes fields by relation.field", () => {
    expect(index.fieldsByKey.get("surveys.title")?.ownerName).toBe("surveys");
    expect(index.fieldsByKey.get("surveys.title")?.ownerKind).toBe("relation");
    expect(index.fieldsByKey.get("defect.title")?.ownerKind).toBe("projection");
    expect(index.fieldsByKey.get("reading.value")?.ownerKind).toBe("struct");
  });

  it("indexes bindings by component and global index", () => {
    expect(index.bindings).toHaveLength(1);
    expect(index.bindings[0].component).toBe("defect");
    expect(index.bindingByComponent.get("defect")?.map((binding) => binding.index)).toEqual([
      0,
    ]);
    expect(
      index.bindingByOutputArtifactKey.get(
        artifactKey(["core", "binding", "defect", "0"]),
      )?.index,
    ).toBe(0);
    expect(index.bindings[0].step?.id).toEqual(binding0);
  });

  it("indexes property lookup branches", () => {
    const title = findComponentPropertyBindings(index, "node", "defect", "title");
    expect(title).toHaveLength(1);
    expect(title[0].propertyRef).toEqual([
      "topology",
      "property",
      "defect.title",
    ]);
    expect(title[0].fieldRefs).toEqual([["data", "field", "surveys.title"]]);
    expect(propertyRefKey(title[0].propertyRef)).toBe(
      propertyRefKey(["topology", "property", "defect.title"]),
    );
  });

  it("reports status counts", () => {
    expect(index.stats).toMatchObject({
      assets: 1,
      tables: 1,
      projections: 1,
      structs: 1,
      topologyNodes: 2,
      topologyEdges: 1,
      topologyProperties: 3,
      bindings: 1,
      components: 2,
      steps: 2,
      connections: 1,
    });
  });
});

describe("semantics and profile indexes", () => {
  it("indexes the graph declaration and its purpose", () => {
    expect(index.graphDeclaration?.name).toBe("fixture_graph");
    expect(index.graphSemantics?.claims).toHaveLength(1);
    expect(index.graphDeclaration?.semantics.purpose?.limitations).toHaveLength(2);

    const graph = index.semanticsByKey.get(semanticSubjectKey("graph", "fixture_graph"));
    expect(graph?.kind).toBe("graph");
    expect(graph?.semantics?.purpose?.text).toBe(
      "Exercise the viewer data contract without loading a release.",
    );
    expect(graph?.semantics?.purpose?.limitations).toHaveLength(2);
  });

  it("indexes asset profiles", () => {
    expect(index.assetProfilesByName.get("estate")).toMatchObject({
      subject: "a monitored estate",
      authority: "primary",
      basis: "synthetic fixture data",
    });
  });

  it("indexes the semantics of every subject kind", () => {
    expect(index.semanticsByKey.get(semanticSubjectKey("asset", "estate"))?.semantics).toBeDefined();
    expect(index.semanticsByKey.get(semanticSubjectKey("relation", "surveys"))?.semantics).toBeDefined();
    expect(index.semanticsByKey.get(semanticSubjectKey("projection", "defect"))?.semantics).toBeDefined();
    expect(index.semanticsByKey.get(semanticSubjectKey("struct", "reading"))?.semantics).toBeDefined();
    expect(
      index.semanticsByKey.get(
        semanticSubjectKey("field", "relation", "surveys", "title"),
      )?.semantics,
    ).toBeDefined();
    expect(index.semanticsByKey.get(semanticSubjectKey("node", "defect"))?.semantics).toBeDefined();
    expect(
      index.semanticsByKey.get(semanticSubjectKey("edge", "has_observation"))?.semantics,
    ).toBeDefined();
    expect(
      index.semanticsByKey.get(
        semanticSubjectKey("property", "node", "defect", "title"),
      )?.semantics,
    ).toBeDefined();
    expect(
      index.semanticsByKey.get(
        semanticSubjectKey("property", "edge", "has_observation", "as_at"),
      )?.semantics,
    ).toBeDefined();
    expect(index.semanticsByKey.get(semanticSubjectKey("binding", 0))?.semantics).toBeDefined();
  });

  it("groups subjects by kind and keeps keys deterministic", () => {
    expect(index.semanticSubjects).toHaveLength(17);
    expect(index.semanticsByKind.get("graph")).toHaveLength(1);
    expect(index.semanticsByKind.get("asset")).toHaveLength(1);
    expect(index.semanticsByKind.get("relation")).toHaveLength(1);
    expect(index.semanticsByKind.get("projection")).toHaveLength(1);
    expect(index.semanticsByKind.get("struct")).toHaveLength(1);
    expect(index.semanticsByKind.get("field")).toHaveLength(5);
    expect(index.semanticsByKind.get("node")).toHaveLength(2);
    expect(index.semanticsByKind.get("edge")).toHaveLength(1);
    expect(index.semanticsByKind.get("property")).toHaveLength(3);
    expect(index.semanticsByKind.get("binding")).toHaveLength(1);

    expect(semanticSubjectKey("node", "defect")).toBe(
      semanticSubjectKey("node", "defect"),
    );
    expect(semanticSubjectKey("node", "defect")).not.toBe(
      semanticSubjectKey("edge", "defect"),
    );
  });
});

describe("viewer index rebuild", () => {
  it("accepts a snapshot without workflow, bindings or a graph declaration", () => {
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
    expect(empty.graphDeclaration).toBeUndefined();
    expect(empty.semanticSubjects).toEqual([]);
    expect(empty.semanticsByKind.size).toBe(0);
  });
});
