import { describe, expect, it } from "vitest";

import {
  constitutionModel,
  contributionModel,
  stepBoundaryModel,
} from "../detail/model/constitution";
import { buildViewerIndex } from "../lib/indexes";
import { loadSnapshotFromObject } from "../lib/load";
import { contractIndex, contractSnapshot } from "./fixtures";

const hierarchyIndex = buildViewerIndex(
  loadSnapshotFromObject({
    ...contractSnapshot,
    blueprint: {
      ...contractSnapshot.blueprint,
      graph: {
        ...contractSnapshot.blueprint.graph,
        nodes: contractSnapshot.blueprint.graph.nodes.map((node) =>
          node.name === "defect"
            ? { ...node, parent: ["topology", "node", "documented"] }
            : node,
        ),
      },
    },
  }),
);

describe("constitution", () => {
  it("gives a record its purpose, bindings, graph ancestry and relation provenance", () => {
    const model = constitutionModel(hierarchyIndex, {
      level: "node",
      component: "defect",
    });
    expect(model.subject.kind).toBe("node");
    expect(model.subject.name).toBe("defect");
    expect(model.subject.current).toBe(true);
    expect(model.subject.meaning.claims[0]?.text).toContain(
      "A defect is observed",
    );
    expect(model.graph.map((level) => level.label)).toEqual([
      "Abstract node",
      "Graph",
    ]);
    expect(model.graph.map((level) => level.name)).toEqual([
      "documented",
      "fixture_graph",
    ]);
    expect(model.relation).toHaveLength(1);
    expect(model.relation[0].node.label).toBe("Source relation");
    expect(model.relation[0].node.name).toBe("surveys");
    expect(model.relation[0].children.map((child) => child.node.label)).toEqual([
      "Asset",
    ]);
    expect(model.relation[0].children.map((child) => child.node.name)).toEqual([
      "estate",
    ]);
    expect(model.bindings).toHaveLength(1);
    expect(model.bindings[0].component).toBe("defect");
    expect(model.bindings[0].meaning.claims[0]?.text).toContain(
      "projects the survey title",
    );
  });

  it("closes the graph branch with a property", () => {
    const model = constitutionModel(hierarchyIndex, {
      level: "property",
      kind: "node",
      component: "defect",
      property: "title",
    });
    expect(model.subject.kind).toBe("property");
    expect(model.subject.name).toBe("defect.title");
    expect(model.graph.map((level) => level.kind)).toEqual([
      "node",
      "abstract",
      "graph",
    ]);
    expect(model.subject.meaning.claims[0]?.text).toContain("display name");
    expect(model.relation.map((root) => root.node.name)).toEqual(["surveys"]);
    expect(model.relation[0].children.map((child) => child.node.name)).toEqual([
      "estate",
    ]);
  });

  it("gives a source relation its own purpose and only its asset", () => {
    const model = constitutionModel(contractIndex, {
      level: "relation",
      component: "surveys",
    });
    expect(model.subject.kind).toBe("relation");
    expect(model.subject.name).toBe("surveys");
    expect(model.subject.current).toBe(true);
    expect(model.subject.meaning.claims[0]?.text).toContain(
      "estate survey table",
    );
    expect(model.graph).toEqual([]);
    expect(model.bindings).toEqual([]);
    expect(model.relation).toHaveLength(1);
    expect(model.relation[0].node.kind).toBe("asset");
    expect(model.relation[0].node.name).toBe("estate");
    expect(model.relation[0].node.current).toBe(false);
    expect(model.relation[0].children).toEqual([]);
  });

  it("gives a derived relation its own purpose and only its scanned sources", () => {
    const model = constitutionModel(contractIndex, {
      level: "projection",
      component: "defect",
    });
    expect(model.subject.kind).toBe("projection");
    expect(model.subject.name).toBe("defect");
    expect(model.graph).toEqual([]);
    expect(model.bindings).toEqual([]);
    expect(model.relation).toHaveLength(1);
    const source = model.relation[0];
    expect(source.node.kind).toBe("relation");
    expect(source.node.name).toBe("surveys");
    expect(source.children.map((child) => child.node.name)).toEqual(["estate"]);
    expect(source.children[0].node.kind).toBe("asset");
    expect(source.children[0].children).toEqual([]);
  });

  it("gives an asset no components: it is the origin", () => {
    const model = constitutionModel(contractIndex, {
      level: "asset",
      component: "estate",
    });
    expect(model.subject.kind).toBe("asset");
    expect(model.subject.name).toBe("estate");
    expect(model.graph).toEqual([]);
    expect(model.relation).toEqual([]);
    expect(model.bindings).toEqual([]);
  });

  it("gives a binding its relations as constitution and its record as contribution", () => {
    const model = constitutionModel(contractIndex, {
      level: "binding",
      component: "defect",
      bindingIndex: 0,
    });
    expect(model.subject.kind).toBe("binding");
    expect(model.subject.name).toBe("defect.title");
    expect(model.subject.current).toBe(true);
    expect(model.subject.meaning.claims[0]?.text).toContain(
      "projects the survey title",
    );
    expect(model.graph).toEqual([]);
    expect(model.relation).toHaveLength(1);
    expect(model.relation[0].node.name).toBe("surveys");
    expect(model.relation[0].children.map((child) => child.node.name)).toEqual([
      "estate",
    ]);
    expect(model.bindings).toEqual([]);

    const contribution = contributionModel(contractIndex, {
      level: "binding",
      component: "defect",
      bindingIndex: 0,
    });
    expect(contribution.direction).toBe("contribution");
    expect(contribution.graph).toHaveLength(1);
    expect(contribution.graph[0].kind).toBe("node");
    expect(contribution.graph[0].name).toBe("defect");
    expect(contribution.graph[0].detail).toBe("identity surveys.survey_id");
    expect(contribution.graph[0].meaning.claims[0]?.text).toContain(
      "A defect is observed",
    );
  });

  it("contributes an asset's source relations one level up", () => {
    const model = contributionModel(contractIndex, {
      level: "asset",
      component: "estate",
    });
    expect(model.direction).toBe("contribution");
    expect(model.subject.kind).toBe("asset");
    expect(model.relation.map((root) => root.node.name)).toEqual(["surveys"]);
    expect(model.graph).toEqual([]);
  });

  it("contributes a source relation's derived relations and direct bindings", () => {
    const model = contributionModel(contractIndex, {
      level: "relation",
      component: "surveys",
    });
    expect(model.relation.map((root) => root.node.name)).toEqual(["defect"]);
    expect(model.bindings.map((binding) => binding.index)).toEqual([0]);
  });

  it("contributes an abstract category's immediate children only", () => {
    const model = contributionModel(hierarchyIndex, {
      level: "abstract",
      component: "documented",
    });
    expect(model.graph.map((node) => node.name)).toEqual(["defect"]);
    expect(model.graph[0].kind).toBe("node");
  });

  it("contributes a node's incident edges and no data dependant for an edge", () => {
    const node = contributionModel(contractIndex, {
      level: "node",
      component: "defect",
    });
    expect(node.graph.map((edge) => edge.name)).toEqual(["has_observation"]);
    expect(node.graph[0].kind).toBe("edge");

    const edge = contributionModel(contractIndex, {
      level: "edge",
      component: "has_observation",
    });
    expect(edge.graph).toEqual([]);
    expect(edge.note).toContain("no dependant");
  });

  it("contributes a property's owning record", () => {
    const model = contributionModel(contractIndex, {
      level: "property",
      kind: "node",
      component: "defect",
      property: "title",
    });
    expect(model.graph.map((node) => node.name)).toEqual(["defect"]);
    expect(model.graph[0].kind).toBe("node");
  });

  it("contributes a step's downstream steps and receives upstream as constitution", () => {
    const downstream = contributionModel(contractIndex, {
      level: "step",
      component: "duckdb",
      name: "source.surveys",
      stepId: ["duckdb", "source.surveys"],
    });
    expect(downstream.workflow?.map((node) => node.name)).toEqual([
      "binding.0",
    ]);

    const upstream = stepBoundaryModel(
      contractIndex,
      {
        level: "step",
        component: "core",
        name: "binding.0",
        stepId: ["core", "binding.0"],
      },
      "dependency",
    );
    expect(upstream.workflow?.map((node) => node.name)).toEqual([
      "source.surveys",
    ]);
  });
});
