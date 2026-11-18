import { describe, expect, it } from "vitest";

import type {
  ConstitutionModel,
  ConstitutionNode,
  ConstitutionRelation,
} from "../detail/model/constitution";
import { buildConstitutionScene } from "../detail/view/constitutionScene";
import type { ConstitutionScene } from "../detail/view/constitutionScene";

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
  purpose: node("node", "defect", "Purpose"),
  graph: [node("graph", "fixture_graph", "Graph")],
  relation: [
    derivedTree("alpha", sourceTree("surveys")),
    derivedTree("beta", sourceTree("surveys")),
    sourceTree("surveys"),
  ],
  bindings: [
    {
      index: 0,
      name: "alpha_binding",
      component: "defect",
      relations: ["alpha"],
      purpose: "Alpha binding.",
      meaning,
    },
    {
      index: 1,
      name: "beta_binding",
      component: "defect",
      relations: ["beta"],
      purpose: "Beta binding.",
      meaning,
    },
    {
      index: 2,
      name: "gamma_binding",
      component: "defect",
      relations: ["surveys"],
      purpose: "Gamma binding.",
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
  it("draws one binding node per binding", () => {
    const bindings = scene.nodes.filter((entry) => entry.axis === "binding");
    expect(bindings).toHaveLength(3);
    expect(byName("alpha_binding")).toHaveLength(1);
    expect(byName("beta_binding")).toHaveLength(1);
    expect(byName("gamma_binding")).toHaveLength(1);
    expect(byName("alpha_binding")[0].text).toBe("Alpha binding.");
    expect(byName("alpha_binding")[0].component).toBe("defect");
    expect(byName("alpha_binding")[0].bindingIndex).toBe(0);
    expect(byName("beta_binding")[0].text).toBe("Beta binding.");
    expect(byName("gamma_binding")[0].text).toBe("Gamma binding.");
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
    expect(edge("relation:surveys", "binding:2")).toBeTruthy();
    expect(edge("asset:estate", "relation:surveys")).toBeTruthy();
    expect(
      scene.edges.filter((entry) => entry.source === "asset:estate"),
    ).toHaveLength(1);
  });

  it("routes each binding to the purpose as an angled line", () => {
    for (const binding of scene.edges.filter(
      (entry) => entry.source.startsWith("binding:") && entry.target === "purpose",
    )) {
      expect(binding.path).toContain("L");
      expect(binding.path).not.toContain("C");
      expect(binding.head).toBeDefined();
    }
  });

  it("centres the binding heads and spaces them evenly on the purpose edge", () => {
    const purpose = byName("defect")[0];
    const heads = scene.edges
      .filter(
        (entry) =>
          entry.source.startsWith("binding:") &&
          entry.target === "purpose",
      )
      .map((entry) => entry.head!)
      .sort((left, right) => left.y - right.y);
    expect(heads).toHaveLength(3);
    const centre = purpose.y + purpose.height / 2;
    expect(heads[1].y).toBeCloseTo(centre);
    expect(heads[0].y + heads[2].y).toBeCloseTo(centre * 2);
    expect(heads[1].y - heads[0].y).toBeCloseTo(
      heads[2].y - heads[1].y,
    );
    for (const head of heads) {
      expect(head.x).toBeCloseTo(purpose.x + purpose.width);
    }
  });

  it("supplies each binding from its own relation and answers the purpose", () => {
    expect(edge("projection:alpha", "binding:0")).toBeTruthy();
    expect(edge("projection:beta", "binding:1")).toBeTruthy();
    expect(edge("relation:surveys", "binding:2")).toBeTruthy();
    expect(edge("binding:0", "purpose")).toBeTruthy();
    expect(edge("binding:1", "purpose")).toBeTruthy();
    expect(edge("binding:2", "purpose")).toBeTruthy();
    expect(edge("graph:fixture_graph", "purpose")).toBeTruthy();
  });

  it("puts every binding on one rank and layers provenance below it", () => {
    const alphaBinding = byName("alpha_binding")[0];
    const betaBinding = byName("beta_binding")[0];
    const gammaBinding = byName("gamma_binding")[0];
    const alpha = byName("alpha")[0];
    const surveys = byName("surveys")[0];
    const estate = byName("estate")[0];
    expect(gammaBinding.y).toBe(alphaBinding.y);
    expect(betaBinding.y).toBe(alphaBinding.y);
    expect(alpha.y).toBeGreaterThan(alphaBinding.y);
    expect(surveys.y).toBeGreaterThan(alpha.y);
    expect(estate.y).toBeGreaterThan(surveys.y);
  });

  it("frames the graph ancestry, the bindings and the relation provenance", () => {
    expect(scene.frames.map((frame) => frame.id)).toEqual([
      "graph",
      "fulfilment",
      "relation",
    ]);
    const contains = (
      entry: (typeof scene.frames)[number],
      item: (typeof scene.nodes)[number],
    ) =>
      item.x >= entry.x &&
      item.y >= entry.y &&
      item.x + item.width <= entry.x + entry.width &&
      item.y + item.height <= entry.y + entry.height;
    const frameFor = (id: (typeof scene.frames)[number]["id"]) =>
      scene.frames.find((frame) => frame.id === id)!;
    const graphFrame = frameFor("graph");
    const fulfilmentFrame = frameFor("fulfilment");
    const relationFrame = frameFor("relation");

    expect(contains(graphFrame, byName("fixture_graph")[0])).toBe(true);
    expect(contains(graphFrame, byName("defect")[0])).toBe(true);
    expect(contains(graphFrame, byName("alpha_binding")[0])).toBe(false);

    for (const binding of scene.nodes.filter(
      (entry) => entry.axis === "binding",
    )) {
      expect(contains(fulfilmentFrame, binding)).toBe(true);
    }
    expect(contains(fulfilmentFrame, byName("surveys")[0])).toBe(false);

    expect(contains(relationFrame, byName("alpha")[0])).toBe(true);
    expect(contains(relationFrame, byName("estate")[0])).toBe(true);
    expect(contains(relationFrame, byName("alpha_binding")[0])).toBe(false);
    expect(contains(relationFrame, byName("fixture_graph")[0])).toBe(false);

    expect(scene.offset.x).toBeGreaterThanOrEqual(0);
    expect(scene.offset.y).toBeGreaterThanOrEqual(0);
    expect(scene.labels.map((label) => label.text)).toEqual([
      "GRAPH",
      "FULFILMENT",
      "RELATION",
    ]);
    for (const label of scene.labels) {
      const frame =
        label.text === "GRAPH"
          ? graphFrame
          : label.text === "FULFILMENT"
            ? fulfilmentFrame
            : relationFrame;
      expect(label.x).toBeGreaterThan(frame.x);
      expect(label.y).toBeGreaterThan(frame.y);
      expect(label.y).toBeLessThan(frame.y + frame.height);
    }
  });

  it("keeps the frames disjoint", () => {
    const [graphFrame, fulfilmentFrame, relationFrame] = scene.frames;
    expect(graphFrame.x + graphFrame.width).toBeLessThanOrEqual(
      fulfilmentFrame.x,
    );
    expect(fulfilmentFrame.y + fulfilmentFrame.height).toBeLessThanOrEqual(
      relationFrame.y,
    );
  });
});

describe("constitution scene for a produced subject", () => {
  const findBySceneId = (scenes: ConstitutionScene, id: string) =>
    scenes.nodes.find((entry) => entry.id === id);
  const findEdge = (scenes: ConstitutionScene, source: string, target: string) =>
    scenes.edges.find((entry) => entry.id === `${source}->${target}`);
  const frameFor = (
    scenes: ConstitutionScene,
    id: (typeof scenes.frames)[number]["id"],
  ) => scenes.frames.find((frame) => frame.id === id);
  const contains = (
    scenes: ConstitutionScene,
    id: (typeof scenes.frames)[number]["id"],
    nodeId: string,
  ) => {
    const frame = frameFor(scenes, id);
    const node = findBySceneId(scenes, nodeId);
    if (!frame || !node) return false;
    return (
      node.x >= frame.x &&
      node.y >= frame.y &&
      node.x + node.width <= frame.x + frame.width &&
      node.y + node.height <= frame.y + frame.height
    );
  };

  it("shows a source relation as its purpose over its asset alone", () => {
    const model: ConstitutionModel = {
      purpose: node("relation", "surveys", "Purpose"),
      graph: [],
      relation: [{ node: node("asset", "estate", "Asset"), children: [] }],
      bindings: [],
    };
    const sourceScene = buildConstitutionScene(model);
    expect(sourceScene.nodes.map((entry) => entry.id)).toEqual([
      "purpose",
      "asset:estate",
    ]);
    expect(findEdge(sourceScene, "asset:estate", "purpose")).toBeTruthy();
    expect(sourceScene.labels.map((label) => label.text)).toEqual([
      "RELATION",
    ]);
    expect(sourceScene.frames.map((frame) => frame.id)).toEqual([
      "relation",
    ]);
    expect(sourceScene.offset.x).toBeGreaterThanOrEqual(0);
    expect(sourceScene.offset.y).toBeGreaterThanOrEqual(0);
    expect(contains(sourceScene, "relation", "asset:estate")).toBe(true);
    const purpose = findBySceneId(sourceScene, "purpose")!;
    const asset = findBySceneId(sourceScene, "asset:estate")!;
    const head = sourceScene.edges.find(
      (entry) => entry.target === "purpose",
    )?.head;
    expect(head).toBeDefined();
    expect(head!.x).toBeCloseTo(purpose.x + purpose.width / 2);
    expect(head!.y).toBeCloseTo(purpose.y + purpose.height);
    expect(asset.y).toBeGreaterThan(purpose.y);
  });

  it("shows a derived relation as its purpose over its scanned sources and their assets", () => {
    const model: ConstitutionModel = {
      purpose: node("projection", "defect", "Purpose"),
      graph: [],
      relation: [sourceTree("surveys")],
      bindings: [],
    };
    const derivedScene = buildConstitutionScene(model);
    expect(findEdge(derivedScene, "relation:surveys", "purpose")).toBeTruthy();
    expect(findEdge(derivedScene, "asset:estate", "relation:surveys")).toBeTruthy();
    expect(derivedScene.labels.map((label) => label.text)).toEqual([
      "RELATION",
    ]);
    expect(derivedScene.frames.map((frame) => frame.id)).toEqual([
      "relation",
    ]);
    expect(contains(derivedScene, "relation", "relation:surveys")).toBe(true);
    expect(contains(derivedScene, "relation", "asset:estate")).toBe(true);
    const surveys = findBySceneId(derivedScene, "relation:surveys");
    const estate = findBySceneId(derivedScene, "asset:estate");
    const purpose = findBySceneId(derivedScene, "purpose");
    expect(surveys!.y).toBeGreaterThan(purpose!.y);
    expect(estate!.y).toBeGreaterThan(surveys!.y);
  });

  it("shows a binding with the purpose, the target record and the relations it reads", () => {
    const model: ConstitutionModel = {
      purpose: node("binding", "defect.title", "Purpose"),
      graph: [
        {
          ...node("node", "defect", "Node"),
          detail: "identity surveys.survey_id",
        },
      ],
      relation: [sourceTree("surveys")],
      bindings: [],
    };
    const bindingScene = buildConstitutionScene(model);
    expect(findEdge(bindingScene, "node:defect", "purpose")).toBeTruthy();
    expect(findEdge(bindingScene, "relation:surveys", "purpose")).toBeTruthy();
    expect(findEdge(bindingScene, "asset:estate", "relation:surveys")).toBeTruthy();
    expect(bindingScene.labels.map((label) => label.text)).toEqual([
      "GRAPH",
      "RELATION",
    ]);
    expect(bindingScene.frames.map((frame) => frame.id)).toEqual([
      "graph",
      "relation",
    ]);
    expect(contains(bindingScene, "graph", "node:defect")).toBe(true);
    expect(contains(bindingScene, "relation", "relation:surveys")).toBe(true);
    expect(contains(bindingScene, "relation", "asset:estate")).toBe(true);
    const target = findBySceneId(bindingScene, "node:defect")!;
    const surveys = findBySceneId(bindingScene, "relation:surveys")!;
    const purpose = findBySceneId(bindingScene, "purpose")!;
    const heads = bindingScene.edges
      .filter((entry) => entry.target === "purpose")
      .map((entry) => entry.head!)
      .sort((left, right) => left.x - right.x);
    expect(heads).toHaveLength(2);
    const centre = purpose.x + purpose.width / 2;
    expect((heads[0].x + heads[1].x) / 2).toBeCloseTo(centre);
    expect(heads[1].x - heads[0].x).toBeCloseTo(24);
    for (const head of heads) {
      expect(head.y).toBeCloseTo(purpose.y + purpose.height);
    }
    expect(target.y).toBe(surveys.y);
    expect(target.y).toBeGreaterThan(purpose.y);
    expect(target.node.detail).toBe("identity surveys.survey_id");
  });

  it("shows an asset as its purpose with no component", () => {
    const model: ConstitutionModel = {
      purpose: node("asset", "estate", "Purpose"),
      graph: [],
      relation: [],
      bindings: [],
    };
    const assetScene = buildConstitutionScene(model);
    expect(assetScene.nodes.map((entry) => entry.id)).toEqual(["purpose"]);
    expect(assetScene.edges).toEqual([]);
    expect(assetScene.labels).toEqual([]);
    expect(assetScene.frames).toEqual([]);
    expect(assetScene.notes.map((note) => note.text)).toEqual([
      "No component is declared.",
    ]);
  });
});
