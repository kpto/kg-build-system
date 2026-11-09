import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { buildViewerIndex } from "@/lib/indexes";
import { loadSnapshotFromObject, normalizeReviewSidecar } from "@/lib/load";
import {
  applyTopologyFilters,
  createTopologyFilters,
  findTopologyEntity,
} from "@/topology/model/TopologyGraphModel";
import {
  buildTopologyGraphModel,
  buildTopologyModel,
} from "@/topology/model/buildTopologyModel";
import { index, snapshot } from "./fixtures";

const reviewText = readFileSync(
  new URL("../public/data/reference.review.json", import.meta.url),
  "utf8",
);
const review = normalizeReviewSidecar(JSON.parse(reviewText));

function model() {
  return buildTopologyModel(snapshot, index, { review });
}

describe("topology force model", () => {
  it("builds one node per topology node and one edge link per topology edge", () => {
    const built = model();
    expect(built.nodes).toHaveLength(index.stats.topologyNodes);
    expect(
      built.links.filter((link) => link.kind === "edge"),
    ).toHaveLength(index.stats.topologyEdges);

    const nodeIds = new Set(built.nodes.map((node) => node.id));
    for (const link of built.links) {
      expect(nodeIds.has(link.source)).toBe(true);
      expect(nodeIds.has(link.target)).toBe(true);
      expect(link.directed).toBe(true);
    }
    expect(built.stats.links).toBe(built.links.length);
  });

  it("links every child to its category parent with containment", () => {
    const built = model();
    const withParent = built.nodes.filter((node) => node.parent);
    const containment = built.links.filter(
      (link) => link.kind === "containment",
    );
    expect(containment).toHaveLength(withParent.length);

    for (const node of withParent) {
      const link = containment.find((candidate) => candidate.sourceName === node.name);
      expect(link).toBeDefined();
      expect(link?.source).toBe(node.id);
      expect(link?.target).toBe(`topology:node:${node.parent}`);
      expect(link?.targetName).toBe(node.parent);
    }
  });

  it("uses deterministic ids, labels and ordering", () => {
    const first = model();
    const second = buildTopologyGraphModel(snapshot, index, { review });

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
      category: "documented",
    });
    expect(
      first.links.find((link) => link.edgeName === "has_observation"),
    ).toMatchObject({
      id: "topology:edge:has_observation",
      kind: "edge",
      sourceName: "defect",
      targetName: "observation",
    });
  });

  it("exposes labels, semantics, finding and decision state", () => {
    const built = model();
    const defect = built.nodes.find((node) => node.name === "defect");
    expect(defect?.labels).toContain("Defect");
    expect(defect?.findings.severities).toBeDefined();
    expect(defect?.decisionStatuses).toBeDefined();
    expect(typeof defect?.hasSemantics).toBe("boolean");
    expect(defect?.semantics.claims).toEqual(expect.any(Array));

    const edge = built.links.find((link) => link.kind === "edge");
    expect(edge?.edgeName).toBeTruthy();
    expect(edge?.semantics.claims).toEqual(expect.any(Array));
    expect(edge?.decisionIds).toEqual(expect.any(Array));
  });

  it("filters by kind, abstract, semantics, findings and decision", () => {
    const built = model();
    const base = createTopologyFilters();

    const all = applyTopologyFilters(built, base);
    expect(all.nodes).toHaveLength(built.nodes.length);
    expect(all.links).toHaveLength(built.links.length);

    const nodesOnly = applyTopologyFilters(built, {
      ...base,
      kinds: { node: true, edge: false },
    });
    expect(nodesOnly.nodes).toHaveLength(built.nodes.length);
    expect(
      nodesOnly.links.every((link) => link.kind === "containment"),
    ).toBe(true);

    const edgesOnly = applyTopologyFilters(built, {
      ...base,
      kinds: { node: false, edge: true },
    });
    expect(
      edgesOnly.links.every((link) => link.kind === "edge"),
    ).toBe(true);
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

    const withFindings = applyTopologyFilters(built, {
      ...base,
      findings: "with",
    });
    expect(withFindings.nodes.length).toBeGreaterThan(0);
    expect(
      withFindings.nodes.every((node) => node.findings.total > 0),
    ).toBe(true);

    const clean = applyTopologyFilters(built, {
      ...base,
      findings: "without",
    });
    expect(clean.nodes.every((node) => node.findings.total === 0)).toBe(true);

    // The reference components carry no semantics; the Open Targets test below
    // covers the present side.
    const present = applyTopologyFilters(built, {
      ...base,
      semantics: "present",
    });
    expect(present.nodes.every((node) => node.hasSemantics)).toBe(true);
    const missing = applyTopologyFilters(built, {
      ...base,
      semantics: "missing",
    });
    expect(missing.nodes.every((node) => !node.hasSemantics)).toBe(true);

    const noDecision = applyTopologyFilters(built, {
      ...base,
      decision: "none",
    });
    expect(noDecision.nodes.every((node) => !node.decisionStatus)).toBe(true);
    expect(noDecision.nodes.length).toBeGreaterThan(0);
  });

  it("resolves a workbench selection to a node or edge entity", () => {
    const built = model();
    expect(
      findTopologyEntity(built, { kind: "node", name: "defect" })?.label,
    ).toBe("Defect");
    expect(
      findTopologyEntity(built, { kind: "edge", name: "has_observation" })
        ?.name,
    ).toBe("has_observation");
    expect(findTopologyEntity(built, { kind: "node", name: "missing" })).toBe(
      undefined,
    );
  });

  it("handles the current 63-node / 163-edge Open Targets snapshot", () => {
    const text = readFileSync(
      new URL("../public/data/opentargets.snapshot.json", import.meta.url),
      "utf8",
    );
    const bigSnapshot = loadSnapshotFromObject(JSON.parse(text));
    const bigIndex = buildViewerIndex(bigSnapshot);
    const built = buildTopologyGraphModel(bigSnapshot, bigIndex);

    expect(built.nodes).toHaveLength(63);
    expect(built.stats.edgeLinks).toBe(163);
    expect(built.nodes).toHaveLength(bigIndex.stats.topologyNodes);
    expect(built.stats.edgeLinks).toBe(bigIndex.stats.topologyEdges);
    expect(built.stats.abstractNodes).toBe(3);
    expect(built.stats.semantics).toBe(226);
    expect(
      built.nodes.filter((node) => node.hasSemantics),
    ).toHaveLength(63);
    expect(
      built.links.filter((link) => link.kind === "edge" && link.hasSemantics),
    ).toHaveLength(163);

    const present = applyTopologyFilters(built, {
      ...createTopologyFilters(),
      semantics: "present",
    });
    expect(present.nodes).toHaveLength(63);
  });
});
