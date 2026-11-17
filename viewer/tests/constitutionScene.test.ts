import { describe, expect, it } from "vitest";

import type {
  ConstitutionModel,
  ConstitutionNode,
  ConstitutionRelation,
} from "../detail/model/constitution";
import { buildConstitutionScene } from "../detail/view/constitutionScene";

const meaning = { claims: [], limitations: [], frames: [] };

function node(
  kind: ConstitutionNode["kind"],
  name: string,
  label = name,
): ConstitutionNode {
  return { kind, name, label, meaning };
}

function sourceTree(name: string): ConstitutionRelation {
  return {
    node: node("relation", name, "Source relation"),
    children: [{ node: node("asset", "estate", "Asset"), children: [] }],
  };
}

function derivedTree(
  name: string,
  scan: ConstitutionRelation,
): ConstitutionRelation {
  return {
    node: node("projection", name, "Derived relation"),
    children: [scan],
  };
}

const sceneModel: ConstitutionModel = {
  purpose: node("graph", "defect", "Purpose"),
  graph: [node("graph", "fixture_graph", "Graph")],
  relation: [
    derivedTree("alpha", sourceTree("surveys")),
    derivedTree("beta", sourceTree("surveys")),
  ],
  binding: { count: 2, identity: [], properties: 0, meaning },
};

const scene = buildConstitutionScene(sceneModel, {
  node: node("binding", "2 bindings", "Fulfilment"),
  text: "2 bindings",
  hoverable: false,
});

const byName = (name: string) =>
  scene.nodes.filter((entry) => entry.node.name === name);
const edge = (source: string, target: string) =>
  scene.edges.find(
    (entry) =>
      entry.id ===
      `${source}->${target}`,
  );

describe("constitution scene", () => {
  it("draws a shared source relation and asset once", () => {
    expect(byName("surveys")).toHaveLength(1);
    expect(byName("estate")).toHaveLength(1);
    expect(byName("alpha")).toHaveLength(1);
    expect(byName("beta")).toHaveLength(1);
    expect(byName("2 bindings")).toHaveLength(1);
  });

  it("gives a shared node one edge per consumer", () => {
    // Both derived relations consume the same source relation.
    expect(edge("relation:surveys", "projection:alpha")).toBeTruthy();
    expect(edge("relation:surveys", "projection:beta")).toBeTruthy();
    // The asset is a single child of the source relation.
    expect(edge("asset:estate", "relation:surveys")).toBeTruthy();
    expect(scene.edges.filter((entry) => entry.source === "asset:estate"))
      .toHaveLength(1);
  });

  it("points every edge from the supply to the consumer", () => {
    expect(edge("projection:alpha", "fulfilment")).toBeTruthy();
    expect(edge("projection:beta", "fulfilment")).toBeTruthy();
    expect(edge("fulfilment", "purpose")).toBeTruthy();
    expect(edge("graph:fixture_graph", "purpose")).toBeTruthy();
  });

  it("layers a shared node below every consumer", () => {
    const alpha = byName("alpha")[0];
    const surveys = byName("surveys")[0];
    const estate = byName("estate")[0];
    expect(surveys.y).toBeGreaterThan(alpha.y);
    expect(estate.y).toBeGreaterThan(surveys.y);
  });

  it("starts the seam below fulfilment and labels both subgraphs", () => {
    const fulfilment = scene.nodes.find((entry) => entry.id === "fulfilment");
    expect(fulfilment).toBeTruthy();
    expect(scene.seam?.y1).toBe(
      (fulfilment?.y ?? 0) + (fulfilment?.height ?? 0),
    );
    expect(scene.labels.map((label) => label.text)).toEqual([
      "GRAPH",
      "RELATION",
    ]);
  });
});
