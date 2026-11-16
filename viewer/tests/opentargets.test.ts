import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { buildViewerIndex, openingMatchesStep } from "../lib/indexes";
import { buildLineage, propertySelection } from "../lib/lineage";
import { loadSnapshotFromObject } from "../lib/load";
import { buildProof } from "../proof/model";
import { provenanceReferences } from "../proof/references";

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
    expect(index.stats.sourceRelations).toBe(61);
    expect(index.stats.derivedRelations).toBe(9);
    expect(index.stats.bindings).toBe(239);
    expect(index.stats.steps).toBe(1000);
    expect(index.stats.connections).toBe(1423);
    expect(index.blueprint.assets?.[0]?.name).toBe("open_target");
    expect(index.assetsByName.get("open_target")?.governance?.license).toMatchObject({
      identifier: "CC0-1.0",
      attribution: "Open Targets",
    });
    expect(snapshot.report.published_artifacts).toEqual([]);
    expect(snapshot.report.provenance).toBeNull();
    expect(snapshot.metaGraph).toBeUndefined();
    expect(
      snapshot.workflow.provenance?.blueprint,
    ).toBeDefined();
  });

  it("carries the graph declaration, purpose and attached semantics", () => {
    const declaration = snapshot.blueprint.graph_declaration;
    expect(declaration?.name).toBe("open_targets");
    expect(declaration?.meaning.claims).toHaveLength(9);
    expect(declaration?.meaning.purpose?.text).toContain(
      "Target-disease evidence review",
    );
    expect(index.graphDeclaration?.name).toBe("open_targets");

    const node = snapshot.blueprint.graph.nodes.find(
      (candidate) => candidate.semantics,
    );
    expect(node?.semantics?.claims?.length).toBeGreaterThan(0);

    const edge = snapshot.blueprint.graph.edges.find(
      (candidate) => candidate.semantics,
    );
    expect(edge?.semantics?.claims?.length).toBeGreaterThan(0);

    const property = [...snapshot.blueprint.graph.nodes, ...snapshot.blueprint.graph.edges]
      .flatMap((candidate) => candidate.properties ?? [])
      .find((candidate) => candidate.semantics);
    expect(property?.semantics?.claims?.length).toBeGreaterThan(0);

    const binding = snapshot.blueprint.bindings.find(
      (candidate) => candidate.semantics,
    );
    expect(binding?.semantics?.claims?.length).toBeGreaterThan(0);

    expect(snapshot.blueprint.assets[0]?.profile?.subject).toBe(
      "target-disease associations and supporting evidence",
    );
    expect(index.semanticsByKind.get("node")).toHaveLength(63);
    expect(index.semanticsByKind.get("edge")).toHaveLength(163);
    expect(index.semanticsByKind.get("binding")).toHaveLength(239);
    expect(index.assetProfilesByName.get("open_target")?.authority).toBe("primary");
  });

  it("derives provenance for an edge without declared properties", () => {
    const proof = buildProof(index, {
      level: "edge",
      kind: "edge",
      component: "clinical_trial_studies_molecule",
    });
    expect(proof.properties).toEqual([]);

    const provenance = provenanceReferences(index, proof);
    expect(provenance.assets.map((reference) => reference.name)).toEqual([
      "open_target",
    ]);
    expect(provenance.tables.map((reference) => reference.name)).toEqual([
      "clinical_report",
    ]);
    expect(provenance.tables[0].target).toMatchObject({ concept: "table", name: "clinical_report" });
    expect(provenance.projections).toEqual([]);
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
});
