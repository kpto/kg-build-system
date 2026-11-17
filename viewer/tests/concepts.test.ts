import { describe, expect, it } from "vitest";

import type { ConceptKind } from "../lib/concepts";
import * as pills from "../detail/view/ConceptPill";
import { concepts } from "../shared/ui/concepts";

const kinds: ConceptKind[] = [
  "graph",
  "abstract",
  "node",
  "edge",
  "property",
  "asset",
  "table",
  "projection",
  "field",
  "binding",
  "workflow",
  "step",
  "semantics",
];

describe("concept catalogue", () => {
  it("defines a mark, label and colour for every layer", () => {
    expect(Object.keys(concepts).sort()).toEqual([...kinds].sort());
    for (const kind of kinds) {
      const definition = concepts[kind];
      expect(definition.label.length).toBeGreaterThan(0);
      expect(definition.color).toMatch(/^var\(--color-concept-/);
      expect(definition.mark).toBeTruthy();
    }
  });

  it("normalises every layer logo to one visual size", () => {
    const ratios = kinds.map((kind) => {
      const [, , width = 24, height = 24] = concepts[kind].box
        .split(" ")
        .map(Number);
      const boxMax = Math.max(width, height);
      const stroke = (1.6 * boxMax) / 24;
      return (boxMax - 2.4 + stroke) / boxMax;
    });
    expect(Math.max(...ratios) - Math.min(...ratios)).toBeLessThan(0.05);
  });

  it("gives every layer a distinct colour", () => {
    const colours = kinds.map((kind) => concepts[kind].color);
    expect(new Set(colours).size).toBe(kinds.length);
  });

  it("names the layers by their role", () => {
    expect(concepts.graph.label).toBe("Graph");
    expect(concepts.table.label).toBe("Source relation");
    expect(concepts.projection.label).toBe("Derived relation");
    expect(concepts.semantics.label).toBe("Meaning");
    expect(concepts.binding.label).toBe("Binding");
  });

  it("exports one inline pill for every layer", () => {
    const names = [
      "GraphPill",
      "AbstractPill",
      "NodePill",
      "EdgePill",
      "PropertyPill",
      "AssetPill",
      "SourceRelationPill",
      "DerivedRelationPill",
      "FieldPill",
      "BindingPill",
      "WorkflowPill",
      "StepPill",
      "MeaningPill",
    ];
    for (const name of names) {
      expect(name in pills, name).toBe(true);
    }
  });
});
