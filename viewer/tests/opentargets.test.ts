import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { buildAudit } from "../lib/audit";
import { computeImpact } from "../lib/impact";
import { buildViewerIndex, openingMatchesStep } from "../lib/indexes";
import { buildLineage, propertySelection } from "../lib/lineage";
import { loadSnapshotFromObject } from "../lib/load";

const text = readFileSync(
  new URL("../public/data/opentargets.snapshot.json", import.meta.url),
  "utf8",
);
const snapshot = loadSnapshotFromObject(JSON.parse(text));
const index = buildViewerIndex(snapshot);

describe("Open Targets snapshot", () => {
  it("preserves the release shape", () => {
    expect(snapshot.name).toBe("open-targets-26.09");
    expect(index.stats.topologyNodes).toBe(63);
    expect(index.stats.topologyEdges).toBe(163);
    expect(index.stats.tables).toBe(61);
    expect(index.stats.projections).toBe(9);
    expect(index.stats.bindings).toBe(239);
    expect(index.stats.steps).toBe(998);
    expect(index.stats.connections).toBe(1419);
    expect(index.blueprint.assets?.[0]?.name).toBe("open_target");
    expect(snapshot.report.provenance).toMatchObject({ mode: "compile-only" });
    expect(snapshot.metaGraph).toBeUndefined();
  });

  it("resolves every binding to its workflow step", () => {
    const unresolved = index.bindings.filter((binding) => !binding.step);
    expect(unresolved.map((binding) => binding.component)).toEqual([]);
  });

  it("matches every connection to a declared opening", () => {
    const unmatched = index.connections.filter((connection) => {
      const consumer = index.stepsById.get(
        `${connection.inputStepId[0]}\u0000${connection.inputStepId[1]}`,
      );
      const producer = index.stepsById.get(
        `${connection.outputStepId[0]}\u0000${connection.outputStepId[1]}`,
      );
      if (!consumer || !producer) return true;
      const consumerOpening = consumer.inputs?.some((opening) =>
        openingMatchesStep(
          connection.input,
          consumer.id,
          "input",
          opening.opening_name,
        ),
      );
      const producerOpening = producer.outputs?.some((opening) =>
        openingMatchesStep(
          connection.output,
          producer.id,
          "output",
          opening.opening_name,
        ),
      );
      return !consumerOpening || !producerOpening;
    });
    expect(unmatched.slice(0, 3)).toEqual([]);
  });

  it("builds target property lineage from a real table", () => {
    const lineage = buildLineage(
      index,
      propertySelection("node", "target", "approvedSymbol"),
    );
    expect(lineage.branches.length).toBeGreaterThan(0);
    const branch = lineage.branches[0];
    expect(branch.sourceRelations).toContain("target");
    expect(branch.bindingStep?.id[0]).toBe("core");
    expect(branch.sourceSteps.map((step) => step.id)).toContainEqual([
      "duckdb",
      "source.target",
    ]);
  });

  it("audits the release without stalling", () => {
    const started = performance.now();
    const audit = buildAudit(index, snapshot.review);
    const elapsed = performance.now() - started;
    expect(audit.findings.length).toBeGreaterThan(0);
    expect(audit.score.value).toBeGreaterThanOrEqual(0);
    expect(audit.score.value).toBeLessThanOrEqual(100);
    expect(elapsed).toBeLessThan(30_000);
  });

  it("computes impact for every topology property within the UI budget", () => {
    const started = performance.now();
    let count = 0;
    for (const node of index.topologyNodes) {
      for (const property of node.properties ?? []) {
        computeImpact(index, {
          kind: "property",
          name: node.name,
          component: node.name,
          property: property.name,
          entityKind: "node",
        });
        count += 1;
      }
    }
    for (const edge of index.topologyEdges) {
      for (const property of edge.properties ?? []) {
        computeImpact(index, {
          kind: "property",
          name: edge.name,
          component: edge.name,
          property: property.name,
          entityKind: "edge",
        });
        count += 1;
      }
    }
    const elapsed = performance.now() - started;
    expect(count).toBeGreaterThan(1000);
    expect(elapsed).toBeLessThan(20_000);
  });
});
