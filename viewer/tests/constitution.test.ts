import { describe, expect, it } from "vitest";

import { constitutionModel } from "../detail/model/constitution";
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
    expect(model.purpose.kind).toBe("node");
    expect(model.purpose.name).toBe("defect");
    expect(model.purpose.current).toBe(true);
    expect(model.purpose.meaning.claims[0]?.text).toContain(
      "A defect is observed",
    );
    expect(model.graph.map((level) => level.label)).toEqual([
      "Category",
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
    expect(model.purpose.kind).toBe("property");
    expect(model.purpose.name).toBe("defect.title");
    expect(model.graph.map((level) => level.kind)).toEqual([
      "node",
      "abstract",
      "graph",
    ]);
    expect(model.purpose.meaning.claims[0]?.text).toContain("display name");
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
    expect(model.purpose.kind).toBe("relation");
    expect(model.purpose.name).toBe("surveys");
    expect(model.purpose.current).toBe(true);
    expect(model.purpose.meaning.claims[0]?.text).toContain(
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
    expect(model.purpose.kind).toBe("projection");
    expect(model.purpose.name).toBe("defect");
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
    expect(model.purpose.kind).toBe("asset");
    expect(model.purpose.name).toBe("estate");
    expect(model.graph).toEqual([]);
    expect(model.relation).toEqual([]);
    expect(model.bindings).toEqual([]);
  });

  it("gives a binding its purpose, the target record's purpose and identity, and the relations it reads", () => {
    const model = constitutionModel(contractIndex, {
      level: "binding",
      component: "defect",
      bindingIndex: 0,
    });
    expect(model.purpose.kind).toBe("binding");
    expect(model.purpose.name).toBe("defect.title");
    expect(model.purpose.current).toBe(true);
    expect(model.purpose.meaning.claims[0]?.text).toContain(
      "projects the survey title",
    );
    expect(model.graph).toHaveLength(1);
    expect(model.graph[0].kind).toBe("node");
    expect(model.graph[0].name).toBe("defect");
    expect(model.graph[0].detail).toBe("identity surveys.survey_id");
    expect(model.graph[0].meaning.claims[0]?.text).toContain(
      "A defect is observed",
    );
    expect(model.relation).toHaveLength(1);
    expect(model.relation[0].node.name).toBe("surveys");
    expect(model.relation[0].children.map((child) => child.node.name)).toEqual([
      "estate",
    ]);
    expect(model.bindings).toEqual([]);
  });
});
