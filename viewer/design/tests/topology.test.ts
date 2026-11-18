import { describe, expect, it } from "vitest";

import {
  applyTopologyFilters,
  createTopologyDetail,
  createTopologyFilters,
  findTopologyEntity,
} from "@/topology/model/TopologyGraphModel";
import {
  buildTopologyGraphModel,
  buildTopologyModel,
} from "@/topology/model/buildTopologyModel";
import {
  contractIndex,
  contractSnapshot,
  index,
  snapshot,
} from "./fixtures";

function model() {
  return buildTopologyModel(snapshot, index);
}

describe("topology design model", () => {
  it("builds one node per topology node and one relation link per topology edge", () => {
    const built = model();
    expect(built.nodes).toHaveLength(index.stats.topologyNodes);
    expect(built.links.filter((link) => link.kind === "edge")).toHaveLength(
      index.stats.topologyEdges,
    );

    const nodeIds = new Set(built.nodes.map((node) => node.id));
    for (const link of built.links) {
      expect(nodeIds.has(link.source)).toBe(true);
      expect(nodeIds.has(link.target)).toBe(true);
      expect(link.directed).toBe(true);
    }
    expect(built.stats.links).toBe(built.links.length);
  });

  it("adds containment child -> parent links only when requested", () => {
    const built = model();
    const withParent = built.nodes.filter((node) => node.parent);
    const containment = built.links.filter(
      (link) => link.kind === "containment",
    );
    expect(containment).toHaveLength(withParent.length);

    for (const node of withParent) {
      const link = containment.find(
        (candidate) => candidate.sourceName === node.name,
      );
      expect(link?.source).toBe(node.id);
      expect(link?.target).toBe(`topology:node:${node.parent}`);
      expect(link?.targetName).toBe(node.parent);
    }

    const without = buildTopologyModel(snapshot, index, {
      containment: false,
    });
    expect(
      without.links.filter((link) => link.kind === "containment"),
    ).toHaveLength(0);

    const defaultDetail = createTopologyDetail();
    expect(defaultDetail.containment).toBe(false);
    const lowDetail = applyTopologyFilters(built, createTopologyFilters());
    expect(lowDetail.links.every((link) => link.kind === "edge")).toBe(true);

    const revealed = applyTopologyFilters(built, createTopologyFilters(), {
      ...defaultDetail,
      containment: true,
    });
    expect(
      revealed.links.filter((link) => link.kind === "containment"),
    ).toHaveLength(withParent.length);
  });

  it("exposes low-detail defaults and independent detail switches", () => {
    expect(createTopologyDetail()).toEqual({
      labels: "hubs",
      edgeLabels: false,
      containment: false,
      semantics: false,
      properties: false,
      clusters: true,
      edges: "relations",
    });

    const built = model();
    expect(built.detail).toEqual(createTopologyDetail());

    const detail = createTopologyDetail();
    const noEdges = applyTopologyFilters(built, createTopologyFilters(), {
      ...detail,
      edges: "off",
    });
    expect(noEdges.links.filter((link) => link.kind === "edge")).toHaveLength(0);
    expect(noEdges.nodes).toHaveLength(built.nodes.length);

    const all = applyTopologyFilters(built, createTopologyFilters(), {
      ...detail,
      edges: "relations",
      containment: true,
    });
    expect(all.links).toHaveLength(built.links.length);
  });

  it("uses deterministic ids, labels and ordering", () => {
    const first = model();
    const second = buildTopologyGraphModel(snapshot, index);

    expect(second.nodes.map((node) => node.id)).toEqual(
      first.nodes.map((node) => node.id),
    );
    expect(second.links.map((link) => link.id)).toEqual(
      first.links.map((link) => link.id),
    );
    expect(
      second.nodes.map((node) => [node.id, node.label, node.category]),
    ).toEqual(first.nodes.map((node) => [node.id, node.label, node.category]));

    expect(first.nodes.find((node) => node.name === "defect")).toMatchObject({
      id: "topology:node:defect",
      name: "defect",
      label: "Defect",
      kind: "node",
      abstract: false,
      category: "uncategorized",
    });
    expect(
      first.links.find((link) => link.edgeName === "has_observation"),
    ).toMatchObject({
      id: "topology:edge:has_observation",
      kind: "edge",
      sourceName: "documented",
      targetName: "defect",
    });
  });

  it("reports labels, property count and semantics presence", () => {
    const built = model();
    const defect = built.nodes.find((node) => node.name === "defect");
    expect(defect?.labels).toContain("Defect");
    expect(defect?.properties).toBeGreaterThan(0);
    expect(typeof defect?.hasSemantics).toBe("boolean");

    const withSemantics = buildTopologyModel(contractSnapshot, contractIndex);
    expect(withSemantics.stats.semantics).toBe(3);
    expect(withSemantics.nodes.every((node) => node.hasSemantics)).toBe(true);
    expect(
      withSemantics.links
        .filter((link) => link.kind === "edge")
        .every((link) => link.hasSemantics),
    ).toBe(true);

    const documented = withSemantics.nodes.find(
      (node) => node.name === "documented",
    );
    expect(documented?.properties).toBe(1);
    expect(documented?.semantics).toMatchObject({
      present: true,
      claimCount: 1,
      purposePresent: true,
      limitationCount: 1,
    });
  });

  it("filters by kind, abstract and semantics", () => {
    const built = model();
    const base = createTopologyFilters();

    const all = applyTopologyFilters(built, base);
    expect(all.nodes).toHaveLength(built.nodes.length);
    expect(all.links.every((link) => link.kind === "edge")).toBe(true);

    const nodesOnly = applyTopologyFilters(built, {
      ...base,
      kinds: { node: true, edge: false },
    });
    expect(nodesOnly.nodes).toHaveLength(built.nodes.length);
    expect(nodesOnly.links).toHaveLength(0);

    const edgesOnly = applyTopologyFilters(built, {
      ...base,
      kinds: { node: false, edge: true },
    });
    expect(edgesOnly.links.every((link) => link.kind === "edge")).toBe(true);
    expect(edgesOnly.nodes.length).toBeGreaterThan(0);

    const abstractOnly = applyTopologyFilters(built, {
      ...base,
      abstract: "abstract",
    });
    expect(abstractOnly.nodes.length).toBeGreaterThan(0);
    expect(abstractOnly.nodes.every((node) => node.abstract)).toBe(true);

    const concreteOnly = applyTopologyFilters(built, {
      ...base,
      abstract: "concrete",
    });
    expect(concreteOnly.nodes.every((node) => !node.abstract)).toBe(true);
    expect(concreteOnly.nodes).toHaveLength(
      built.nodes.filter((node) => !node.abstract).length,
    );

    const present = applyTopologyFilters(built, {
      ...base,
      semantics: "present",
    });
    expect(present.nodes).toHaveLength(2);

    const missing = applyTopologyFilters(built, {
      ...base,
      semantics: "missing",
    });
    expect(missing.nodes).toHaveLength(0);

    const contract = buildTopologyModel(contractSnapshot, contractIndex);
    const contractPresent = applyTopologyFilters(contract, {
      ...base,
      semantics: "present",
    });
    expect(contractPresent.nodes).toHaveLength(contract.nodes.length);
    const contractMissing = applyTopologyFilters(contract, {
      ...base,
      semantics: "missing",
    });
    expect(contractMissing.nodes).toHaveLength(0);
  });

  it("resolves a workbench selection to a node or edge entity", () => {
    const built = model();
    expect(
      findTopologyEntity(built, { kind: "node", name: "defect" })?.label,
    ).toBe("Defect");
    expect(
      findTopologyEntity(built, { kind: "edge", name: "has_observation" })?.name,
    ).toBe("has_observation");
    expect(findTopologyEntity(built, { kind: "node", name: "missing" })).toBe(
      undefined,
    );
  });
});
