import { describe, expect, it } from "vitest";

import { constitutionModel } from "../shared/design/constitution";
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
    expect(model.relation.map((level) => level.label)).toEqual([
      "Source relation",
      "Asset",
    ]);
    expect(model.relation.map((level) => level.name)).toEqual([
      "surveys",
      "estate",
    ]);
    expect(model.binding?.count).toBe(1);
    expect(model.binding?.identity).toContain("surveys.survey_id");
    expect(model.binding?.meaning.claims[0]?.text).toContain(
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
    expect(model.relation.map((level) => level.name)).toEqual([
      "surveys",
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
    expect(model.relation.map((level) => level.kind)).toEqual([
      "relation",
      "asset",
    ]);
    expect(model.relation[0].current).toBe(true);
    expect(model.relation[0].meaning.claims[0]?.text).toContain(
      "estate survey table",
    );
    expect(model.relation[1].name).toBe("estate");
    expect(model.binding?.count).toBe(1);
  });
});
