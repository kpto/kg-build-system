import { describe, expect, it } from "vitest";
import {
  buildLineage,
  lineageStepNodeId,
  propertySelection,
} from "../lib/lineage";
import type { LineageBranch, LineageGraph, StepId } from "../lib/types";
import { index } from "./fixtures";

function hasStep(branch: LineageBranch, id: StepId): boolean {
  return (
    branch.sourceSteps.some((step) => step.id[0] === id[0] && step.id[1] === id[1]) ||
    branch.transformationSteps.some((step) => step.id[0] === id[0] && step.id[1] === id[1]) ||
    branch.postSteps.some((step) => step.id[0] === id[0] && step.id[1] === id[1]) ||
    branch.targetSteps.some((step) => step.id[0] === id[0] && step.id[1] === id[1]) ||
    (branch.bindingStep?.id[0] === id[0] && branch.bindingStep?.id[1] === id[1])
  );
}

function hasChain(graph: LineageGraph, chain: StepId[]): boolean {
  const ids = chain.map((id) => lineageStepNodeId(index.stepsById.get(`${id[0]}\u0000${id[1]}`)!));
  return chain.slice(1).every((_, position) => {
    const source = ids[position];
    const target = ids[position + 1];
    return graph.edges.some((edge) => edge.source === source && edge.target === target);
  });
}

function lineageFor(kind: "node" | "edge", component: string, property: string) {
  return buildLineage(index, propertySelection(kind, component, property));
}

describe("property lineage", () => {
  it("builds the defect.title source and target chain", () => {
    const lineage = lineageFor("node", "defect", "title");
    expect(lineage.branches).toHaveLength(1);
    const branch = lineage.branches[0];

    expect(branch.binding.index).toBe(0);
    expect(branch.fieldKeys).toEqual(["defect.title"]);
    expect(branch.relationNames).toEqual(["defect"]);
    expect(branch.sourceRelations).toEqual(["surveys"]);
    expect(branch.assetNames).toEqual(["estate"]);

    // Upstream: source -> projection -> binding.
    expect(hasStep(branch, ["duckdb", "source.surveys"])).toBe(true);
    expect(hasStep(branch, ["core", "projection.defect"])).toBe(true);
    expect(hasStep(branch, ["core", "binding.0"])).toBe(true);
    expect(
      hasChain(lineage, [
        ["duckdb", "source.surveys"],
        ["core", "projection.defect"],
        ["core", "binding.0"],
      ]),
    ).toBe(true);

    // The semantic projection node is wired to its workflow step. The
    // artifact tuple is ("core","data","projection",name): reading the wrong
    // segment silently drops this edge.
    const projectionStep = index.stepsById.get("core\u0000projection.defect")!;
    expect(
      lineage.edges.some(
        (edge) =>
          edge.source === "semantic:projection:defect" &&
          edge.target === lineageStepNodeId(projectionStep),
      ),
    ).toBe(true);
    expect(
      lineage.edges.some(
        (edge) =>
          edge.source === "semantic:field:defect.title" &&
          edge.target === "semantic:projection:defect",
      ),
    ).toBe(true);

    // Downstream: aggregate -> dedup -> publication targets.
    expect(hasStep(branch, ["core", "aggregate.defect"])).toBe(true);
    expect(hasStep(branch, ["deduplication", "defect"])).toBe(true);
    expect(branch.targetSteps.map((step) => step.id[0])).toEqual(
      expect.arrayContaining(["file", "meta_graph", "neo4j"]),
    );
    expect(
      branch.targetSteps.some(
        (step) =>
          step.id[0] === "neo4j" && step.id[1].startsWith("export.node.defect"),
      ),
    ).toBe(true);
    expect(
      hasChain(lineage, [
        ["core", "binding.0"],
        ["core", "aggregate.defect"],
        ["deduplication", "defect"],
        ["file", "write"],
      ]),
    ).toBe(true);

    const lanes = new Set(lineage.nodes.map((node) => node.lane));
    expect(lanes).toEqual(
      new Set(["asset", "source", "transformation", "binding", "post", "target"]),
    );
    const terminal = lineage.nodes.find((node) => node.id === lineage.terminalNodeId);
    expect(terminal?.kind).toBe("property");
    expect(lineage.edges.some((edge) => edge.source === terminal?.id)).toBe(false);
    expect(terminal?.metadata.annotationViews[0]?.examples).toContain("Bearing wear");
    expect(terminal?.metadata.counts?.records).toBe(3);

    const bindingStep = lineage.nodes.find(
      (node) => node.id === lineageStepNodeId(index.stepsById.get("core\u0000binding.0")!),
    );
    expect(bindingStep?.metadata.sqlPreview).toContain("SELECT");
    expect(bindingStep?.metadata.artifacts).toContainEqual([
      "core",
      "binding",
      "defect",
      "0",
    ]);
  });

  it("shows every branch for reading.value", () => {
    const lineage = lineageFor("node", "reading", "value");
    expect(lineage.branches).toHaveLength(2);
    expect(lineage.branches.map((branch) => branch.binding.index)).toEqual([4, 5]);
    expect(
      lineage.branches.flatMap((branch) => branch.fieldKeys).sort(),
    ).toEqual(["temperature.deg_c", "vibration.mm_s"]);

    const temperature = lineage.branches.find((branch) => branch.binding.index === 4)!;
    expect(temperature.sourceRelations).toEqual(["temperature"]);
    expect(hasStep(temperature, ["duckdb", "source.temperature"])).toBe(true);
    expect(hasStep(temperature, ["core", "aggregate.reading"])).toBe(true);
    expect(hasStep(temperature, ["deduplication", "reading"])).toBe(true);

    const vibration = lineage.branches.find((branch) => branch.binding.index === 5)!;
    expect(vibration.sourceRelations).toEqual(["vibration"]);
    expect(hasStep(vibration, ["duckdb", "source.vibration"])).toBe(true);
  });

  it("traces binding.12 through the measures target", () => {
    const lineage = lineageFor("edge", "measures", "as_at");
    const temperatureBranch = lineage.branches.find(
      (branch) => branch.binding.index === 12,
    )!;
    expect(temperatureBranch.sourceRelations).toEqual(["temperature"]);
    expect(hasStep(temperatureBranch, ["duckdb", "source.temperature"])).toBe(true);
    expect(hasStep(temperatureBranch, ["core", "binding.12"])).toBe(true);
    expect(hasStep(temperatureBranch, ["core", "aggregate.measures"])).toBe(true);
    expect(hasStep(temperatureBranch, ["deduplication", "measures"])).toBe(true);
    expect(
      hasChain(lineage, [
        ["duckdb", "source.temperature"],
        ["core", "binding.12"],
        ["core", "aggregate.measures"],
        ["deduplication", "measures"],
      ]),
    ).toBe(true);
    expect(
      temperatureBranch.targetSteps.some((step) => step.id[0] === "file"),
    ).toBe(true);
  });

  it("keeps a literal-only property to binding and targets", () => {
    const lineage = lineageFor("node", "defect", "source_version");
    const branch = lineage.branches[0];
    expect(branch.binding.index).toBe(0);
    expect(branch.fieldRefs).toEqual([]);
    expect(branch.relationNames).toEqual([]);
    expect(branch.sourceRelations).toEqual([]);
    expect(branch.assetNames).toEqual([]);
    expect(lineage.nodes.some((node) => node.lane === "source")).toBe(false);
    expect(lineage.nodes.some((node) => node.lane === "transformation")).toBe(false);
    expect(hasStep(branch, ["core", "aggregate.defect"])).toBe(true);
  });

  it("enriches edge property lineage from a projection", () => {
    const lineage = lineageFor("edge", "has_observation", "as_at");
    const branch = lineage.branches[0];
    expect(branch.fieldKeys).toEqual(["observation.observed_on"]);
    expect(branch.sourceRelations).toEqual(["defect"]);
    expect(branch.transformationSteps.map((step) => step.id)).toEqual(
      expect.arrayContaining([
        ["core", "projection.observation"],
        ["core", "projection.defect"],
      ]),
    );
    expect(branch.downstreamSteps.map((step) => step.id)).toContainEqual([
      "deduplication",
      "has_observation",
    ]);
  });

  it("returns an empty-state graph for an unknown property", () => {
    const lineage = buildLineage(index, propertySelection("node", "defect", "missing"));
    expect(lineage.branches).toEqual([]);
    expect(lineage.nodes).toHaveLength(1);
    expect(lineage.nodes[0].id).toBe(lineage.terminalNodeId);
  });
});
