import { describe, expect, it } from "vitest";

import { contractIndex } from "./fixtures";
import { previewForConceptTarget } from "../workbench/conceptPreview";

const preview = (target: Parameters<typeof previewForConceptTarget>[1]) =>
  previewForConceptTarget(contractIndex, target);

describe("concept previews", () => {
  it("previews a node with identity, facts and meaning", () => {
    const model = preview({ concept: "node", name: "defect" });
    expect(model?.kind).toBe("Node");
    expect(model?.name).toBe("defect");
    expect(model?.facts).toContainEqual({ label: "Labels", value: "Defect" });
    expect(model?.facts).toContainEqual({ label: "Properties", value: "1" });
    expect(model?.facts).toContainEqual({ label: "Connections", value: "1" });
    expect(model?.meaning?.claims[0]?.text).toContain(
      "A defect is observed",
    );
  });

  it("previews an edge with its endpoints", () => {
    const model = preview({ concept: "edge", name: "has_observation" });
    expect(model?.kind).toBe("Edge");
    expect(model?.facts).toContainEqual({
      label: "Endpoints",
      value: "documented → defect",
    });
    expect(model?.meaning?.claims[0]?.text).toContain("when the defect");
  });

  it("previews a property on its owner", () => {
    const model = preview({
      concept: "property",
      name: "defect.title",
      component: "defect",
      property: "title",
    });
    expect(model?.kind).toBe("Property");
    expect(model?.name).toBe("defect.title");
    expect(model?.facts).toContainEqual({
      label: "Owner",
      value: "node defect",
    });
    expect(model?.facts).toContainEqual({ label: "Type", value: "str" });
    expect(model?.meaning?.claims[0]?.text).toContain("display name");
  });

  it("previews an asset, relation and derived relation", () => {
    const asset = preview({ concept: "asset", name: "estate" });
    expect(asset?.kind).toBe("Asset");
    expect(asset?.facts).toContainEqual({ label: "Layout", value: "json" });
    expect(asset?.facts).toContainEqual({
      label: "Location",
      value: "fixture://estate",
    });
    expect(asset?.facts).toContainEqual({
      label: "Source relations",
      value: "1",
    });
    expect(asset?.meaning?.purpose).toContain("fixture estate");

    const relation = preview({ concept: "table", name: "surveys" });
    expect(relation?.kind).toBe("Source relation");
    expect(relation?.facts).toContainEqual({ label: "Asset", value: "estate" });
    expect(relation?.facts).toContainEqual({ label: "Columns", value: "2" });
    expect(relation?.facts).toContainEqual({
      label: "Grain",
      value: "one survey row per defect",
    });

    const projection = preview({ concept: "projection", name: "defect" });
    expect(projection?.kind).toBe("Derived relation");
    expect(projection?.facts).toContainEqual({
      label: "Scans",
      value: "surveys",
    });
    expect(projection?.facts).toContainEqual({
      label: "Visibility",
      value: "public",
    });
  });

  it("previews a field, binding, step and workflow component", () => {
    const field = preview({
      concept: "field",
      name: "survey_id",
      component: "surveys",
      ownerConcept: "table",
    });
    expect(field?.kind).toBe("Field");
    expect(field?.facts).toContainEqual({
      label: "Owner",
      value: "relation surveys",
    });
    expect(field?.facts).toContainEqual({ label: "Type", value: "str" });

    const binding = preview({ concept: "binding", name: "defect.title", bindingIndex: 0 });
    expect(binding?.kind).toBe("Binding");
    expect(binding?.name).toBe("defect.title");
    expect(binding?.facts).toContainEqual({
      label: "Target",
      value: "node defect",
    });
    expect(binding?.facts).toContainEqual({
      label: "Rows read",
      value: "surveys",
    });
    expect(binding?.meaning?.claims[0]?.text).toContain("survey title");

    const step = preview({
      concept: "step",
      name: "binding.0",
      component: "core",
      stepId: ["core", "binding.0"],
    });
    expect(step?.kind).toBe("Step");
    expect(step?.facts).toContainEqual({ label: "Component", value: "core" });
    expect(step?.facts).toContainEqual({
      label: "Instruction",
      value: "sql · duckdb",
    });
    expect(step?.facts).toContainEqual({ label: "Inputs", value: "1" });
    expect(step?.facts).toContainEqual({ label: "Outputs", value: "1" });

    const component = preview({ concept: "workflow", name: "core" });
    expect(component?.kind).toBe("Workflow component");
    expect(component?.facts).toContainEqual({ label: "Steps", value: "1" });
  });

  it("previews a collection and the graph declaration", () => {
    const collection = preview({
      concept: "node",
      name: "Nodes",
      collection: "nodes",
    });
    expect(collection?.kind).toBe("Collection");
    expect(collection?.facts).toContainEqual({ label: "Items", value: "1" });

    const graph = preview({ concept: "graph", name: "fixture_graph" });
    expect(graph?.kind).toBe("Graph declaration");
    expect(graph?.facts).toContainEqual({ label: "Nodes", value: "2" });
    expect(graph?.meaning?.purpose).toContain("Exercise the viewer");
  });

  it("returns nothing for an unresolved target", () => {
    expect(preview({ concept: "node", name: "missing" })).toBeUndefined();
    expect(
      preview({ concept: "binding", name: "missing", bindingIndex: 999 }),
    ).toBeUndefined();
  });
});
