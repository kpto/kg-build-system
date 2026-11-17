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
  bindings: [
    {
      index: 0,
      name: "alpha_binding",
      identity: ["alpha_id"],
      properties: 1,
      relations: ["alpha"],
      purpose: "Alpha binding.",
      meaning,
    },
    {
      index: 1,
      name: "beta_binding",
      identity: ["beta_id"],
      properties: 1,
      relations: ["beta"],
      purpose: "Beta binding.",
      meaning,
    },
  ],
};

const scene = buildConstitutionScene(sceneModel);

const byName = (name: string) =>
  scene.nodes.filter((entry) => entry.node.name === name);
const edge = (source: string, target: string) =>
  scene.edges.find((entry) => entry.id === `${source}->${target}`);

describe("constitution scene", () => {
  it("draws one fulfilment node per binding", () => {
    const fulfilments = scene.nodes.filter((entry) => entry.axis === "fulfilment");
    expect(fulfilments).toHaveLength(2);
    expect(byName("alpha_binding")).toHaveLength(1);
    expect(byName("beta_binding")).toHaveLength(1);
    expect(byName("alpha_binding")[0].text).toBe("Alpha binding.");
    expect(byName("beta_binding")[0].text).toBe("Beta binding.");
  });

  it("draws a shared source relation and asset once", () => {
    expect(byName("surveys")).toHaveLength(1);
    expect(byName("estate")).toHaveLength(1);
    expect(byName("alpha")).toHaveLength(1);
    expect(byName("beta")).toHaveLength(1);
  });

  it("gives a shared node one edge per consumer", () => {
    expect(edge("relation:surveys", "projection:alpha")).toBeTruthy();
    expect(edge("relation:surveys", "projection:beta")).toBeTruthy();
    expect(edge("asset:estate", "relation:surveys")).toBeTruthy();
    expect(
      scene.edges.filter((entry) => entry.source === "asset:estate"),
    ).toHaveLength(1);
  });

  it("supplies each binding from its own relation and answers the purpose", () => {
    expect(edge("projection:alpha", "binding:0")).toBeTruthy();
    expect(edge("projection:beta", "binding:1")).toBeTruthy();
    expect(edge("binding:0", "purpose")).toBeTruthy();
    expect(edge("binding:1", "purpose")).toBeTruthy();
    expect(edge("graph:fixture_graph", "purpose")).toBeTruthy();
  });

  it("layers a shared node below every consumer", () => {
    const binding = byName("alpha_binding")[0];
    const alpha = byName("alpha")[0];
    const surveys = byName("surveys")[0];
    const estate = byName("estate")[0];
    expect(alpha.y).toBeGreaterThan(binding.y);
    expect(surveys.y).toBeGreaterThan(alpha.y);
    expect(estate.y).toBeGreaterThan(surveys.y);
  });

  it("starts the seam below the fulfilment row and labels both subgraphs", () => {
    const binding = byName("alpha_binding")[0];
    expect(scene.seam?.y1).toBe(binding.y + binding.height);
    expect(scene.labels.map((label) => label.text)).toEqual([
      "GRAPH",
      "RELATION",
    ]);
  });
});
