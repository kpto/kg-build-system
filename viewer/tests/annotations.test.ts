import { describe, expect, it } from "vitest";
import {
  annotationKey,
  buildMetaGraphIndex,
  dedupeAnnotations,
  enrichAnnotations,
  flattenAnnotations,
} from "../lib/annotations";

const annotation = {
  namespace: "example",
  id: "provenance",
  arguments: { stage: "built" },
};
const annotations = [annotation];
const metaGraph = buildMetaGraphIndex({
  nodes: [
    {
      kind: "node",
      name: "defect",
      properties: [
        {
          name: "title",
          description: "The defect label.",
          examples: ["Bearing wear"],
        },
      ],
      counts: { records: 3 },
    },
  ],
  edges: [
    {
      kind: "edge",
      name: "has_observation",
      properties: [
        {
          name: "as_at",
          examples: ["2026-07-14T10:12"],
        },
      ],
    },
  ],
});

describe("annotation flattening", () => {
  it("flattens namespace:id keys and arguments", () => {
    const flattened = flattenAnnotations(annotations);
    expect(flattened).toHaveLength(1);
    expect(flattened[0]).toMatchObject({
      key: "example:provenance",
      namespace: "example",
      id: "provenance",
      arguments: { stage: "built" },
      text: "example/provenance(stage=built)",
    });
    expect(flattened[0].argumentList).toEqual([{ key: "stage", value: "built" }]);
    expect(annotationKey(flattened[0].source)).toBe("example:provenance");
  });

  it("handles missing annotations", () => {
    expect(flattenAnnotations(undefined)).toEqual([]);
    expect(flattenAnnotations([])).toEqual([]);
  });

  it("deduplicates by key and arguments", () => {
    const flattened = flattenAnnotations(annotations);
    expect(dedupeAnnotations([...flattened, ...flattened])).toHaveLength(1);
  });
});

describe("metaGraph enrichment", () => {
  it("uses property examples and component counts for a node property", () => {
    const enriched = enrichAnnotations(
      annotations,
      { kind: "node", component: "defect", property: "title" },
      metaGraph,
    );
    expect(enriched[0].description).toBe("The defect label.");
    expect(enriched[0].examples).toContain("Bearing wear");
    expect(enriched[0].counts?.records).toBe(3);
    expect(enriched[0].metaProperty?.name).toBe("title");
  });

  it("uses edge property examples", () => {
    const enriched = enrichAnnotations(
      annotations,
      { kind: "edge", component: "has_observation", property: "as_at" },
      metaGraph,
    );
    expect(enriched[0].examples).toContain("2026-07-14T10:12");
    expect(enriched[0].metaComponent?.kind).toBe("edge");
  });

  it("returns the annotation unenriched when no context exists", () => {
    const enriched = enrichAnnotations(annotations, {});
    expect(enriched[0].examples).toEqual([]);
    expect(enriched[0].metaComponent).toBeUndefined();
  });
});
