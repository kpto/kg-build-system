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
  it("reads the graph branch, relation branch and fulfilment box for a node", () => {
    const model = constitutionModel(hierarchyIndex, {
      level: "node",
      component: "defect",
    });
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
    expect(model.bindings[0].identity).toContain("surveys.survey_id");
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

  it("roots a relation in its own meaning and lists the records it fulfils", () => {
    const model = constitutionModel(contractIndex, {
      level: "relation",
      component: "surveys",
    });
    expect(model.purpose.name).toBe("surveys");
    expect(model.purpose.current).toBe(true);
    expect(model.purpose.meaning.claims[0]?.text).toContain(
      "estate survey table",
    );
    expect(model.graph.map((level) => level.name)).toEqual([
      "defect",
      "fixture_graph",
    ]);
    expect(model.relation.map((root) => root.node.kind)).toEqual([
      "relation",
    ]);
    expect(model.relation[0].node.current).toBe(true);
    expect(model.relation[0].node.meaning.claims[0]?.text).toContain(
      "estate survey table",
    );
    expect(model.relation[0].children[0].node.name).toBe("estate");
    expect(model.bindings).toHaveLength(1);
  });

  it("keeps the whole provenance chain of a derived relation", () => {
    const model = constitutionModel(contractIndex, {
      level: "projection",
      component: "defect",
    });
    expect(model.relation).toHaveLength(1);
    const derived = model.relation[0];
    expect(derived.node.kind).toBe("projection");
    expect(derived.node.name).toBe("defect");
    expect(derived.children.map((child) => child.node.name)).toEqual([
      "surveys",
    ]);
    const source = derived.children[0];
    expect(source.node.kind).toBe("relation");
    expect(source.children.map((child) => child.node.name)).toEqual(["estate"]);
    expect(source.children[0].node.kind).toBe("asset");
    expect(source.children[0].children).toEqual([]);
  });
});
