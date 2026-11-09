import { describe, expect, it } from "vitest";
import {
  annotationKey,
  buildMetaGraphIndex,
  dedupeAnnotations,
  enrichAnnotations,
  flattenAnnotations,
} from "../lib/annotations";
import { snapshot } from "./fixtures";

const node = snapshot.blueprint.graph.nodes.find((candidate) => candidate.name === "defect");
const edge = snapshot.blueprint.graph.edges.find(
  (candidate) => candidate.name === "has_observation",
);
const metaGraph = buildMetaGraphIndex(snapshot.metaGraph);

describe("annotation flattening", () => {
  it("flattens namespace:id keys and arguments", () => {
    const annotations = flattenAnnotations(node?.annotations);
    expect(annotations).toHaveLength(1);
    expect(annotations[0]).toMatchObject({
      key: "reference_project:provenance",
      namespace: "reference_project",
      id: "provenance",
      arguments: { stage: "built" },
      text: "reference_project/provenance(stage=built)",
    });
    expect(annotations[0].argumentList).toEqual([{ key: "stage", value: "built" }]);
    expect(annotationKey(annotations[0].source)).toBe("reference_project:provenance");
  });

  it("handles missing annotations", () => {
    expect(flattenAnnotations(undefined)).toEqual([]);
    expect(flattenAnnotations([])).toEqual([]);
  });

  it("deduplicates by key and arguments", () => {
    const annotations = flattenAnnotations(node?.annotations);
    expect(dedupeAnnotations([...annotations, ...annotations])).toHaveLength(1);
  });
});

describe("metaGraph enrichment", () => {
  it("uses property examples and component counts for a node property", () => {
    const enriched = enrichAnnotations(
      node?.annotations,
      { kind: "node", component: "defect", property: "title" },
      metaGraph,
    );
    expect(enriched[0].description).toBe("What the defect is, as the surveyor described it.");
    expect(enriched[0].examples).toContain("Bearing wear");
    expect(enriched[0].counts?.records).toBe(3);
    expect(enriched[0].metaProperty?.name).toBe("title");
  });

  it("uses edge property examples", () => {
    const enriched = enrichAnnotations(
      edge?.annotations,
      { kind: "edge", component: "has_observation", property: "as_at" },
      metaGraph,
    );
    expect(enriched[0].examples).toContain("2026-07-14T10:12");
    expect(enriched[0].metaComponent?.kind).toBe("edge");
  });

  it("returns the annotation unenriched when no context exists", () => {
    const enriched = enrichAnnotations(node?.annotations, {});
    expect(enriched[0].examples).toEqual([]);
    expect(enriched[0].metaComponent).toBeUndefined();
  });
});
