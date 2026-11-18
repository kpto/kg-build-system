import { describe, expect, it } from "vitest";

import {
  componentMeaning,
  graphMeaning,
  meaningCount,
  meaningLimitations,
  propertyMeaning,
  purposeLevels,
} from "../shared/design/meaning";
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

describe("design meaning", () => {
  it("reads the graph purpose, limitations and claims", () => {
    const meaning = graphMeaning(contractIndex);
    expect(meaning.purpose).toBe(
      "Exercise the viewer data contract without loading a release.",
    );
    expect(meaning.claims.map((claim) => claim.text)).toContain(
      "The fixture graph contains one observed estate.",
    );
    expect(meaning.limitations).toHaveLength(2);
    expect(meaningCount(meaning)).toBe(4);
    expect(meaningLimitations(meaning)).toHaveLength(2);
  });

  it("reads the meaning attached to a component", () => {
    const meaning = componentMeaning(contractIndex, "node", "defect");
    expect(meaning.claims.map((claim) => claim.text)).toEqual([
      "A defect is observed on an estate survey.",
    ]);
    expect(meaning.limitations).toHaveLength(0);
  });

  it("reads the meaning attached to one property", () => {
    const meaning = propertyMeaning(contractIndex, "node", "defect", "title");
    expect(meaning.claims.map((claim) => claim.text)).toEqual([
      "The title is the defect's display name.",
    ]);
  });

  it("returns empty meaning for a subject without meaning", () => {
    expect(componentMeaning(contractIndex, "node", "missing").claims).toEqual([]);
    expect(componentMeaning(contractIndex, "node", "missing").limitations).toEqual(
      [],
    );
  });
});


describe("purpose hierarchy", () => {
  it("reads the graph, the category and the component downward", () => {
    const levels = purposeLevels(hierarchyIndex, {
      level: "node",
      component: "defect",
    });
    expect(levels.map((entry) => entry.label)).toEqual([
      "Graph",
      "Abstract node",
      "Node",
    ]);
    expect(levels[0].meaning.purpose).toContain(
      "Exercise the viewer data contract",
    );
    expect(levels[1].meaning.purpose).toContain("abstract category");
    expect(levels[1].meaning.claims[0]?.text).toContain("Every documented");
    expect(levels[2].current).toBe(true);
    expect(levels[2].meaning.purpose).toBeUndefined();
  });

  it("closes the chain with a property", () => {
    const levels = purposeLevels(hierarchyIndex, {
      level: "property",
      kind: "node",
      component: "defect",
      property: "title",
    });
    expect(levels.map((entry) => entry.kind)).toEqual([
      "graph",
      "abstract",
      "node",
      "property",
    ]);
    expect(levels.at(-1)?.current).toBe(true);
  });

  it("keeps a relation purpose off the record hierarchy", () => {
    expect(
      purposeLevels(contractIndex, {
        level: "relation",
        component: "surveys",
      }),
    ).toEqual([]);
  });
});
