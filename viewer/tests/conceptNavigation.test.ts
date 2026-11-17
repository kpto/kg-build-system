import { describe, expect, it } from "vitest";

import {
  destinationForConceptTarget,
  selectionForConceptTarget,
} from "../workbench/conceptTarget";
import { contractIndex as index } from "./fixtures";

describe("concept pill navigation", () => {
  it("opens a record, relation and working surface", () => {
    expect(
      destinationForConceptTarget(index, { concept: "node", name: "defect" }),
    ).toEqual({
      kind: "subject",
      selection: { kind: "node", level: "node", component: "defect" },
    });
    expect(
      destinationForConceptTarget(index, { concept: "table", name: "surveys" }),
    ).toMatchObject({
      kind: "subject",
      selection: { kind: "relation", component: "surveys" },
    });
    expect(
      destinationForConceptTarget(index, {
        concept: "graph",
        name: "fixture_graph",
      }),
    ).toEqual({ kind: "graph" });
  });

  it("resolves a property through its owner", () => {
    expect(
      selectionForConceptTarget(
        {
          concept: "property",
          name: "title",
          component: "defect",
          property: "title",
        },
        index,
      ),
    ).toMatchObject({
      kind: "node",
      level: "property",
      component: "defect",
      property: "title",
    });
  });

  it("opens the owner document for a field", () => {
    expect(
      selectionForConceptTarget(
        {
          concept: "field",
          name: "some_column",
          component: "surveys",
          ownerConcept: "table",
        },
        index,
      ),
    ).toMatchObject({ kind: "relation", component: "surveys" });
  });

  it("does not invent a destination when the layer has no document", () => {
    expect(
      destinationForConceptTarget(index, {
        concept: "semantics",
        name: "anything",
      }),
    ).toBeUndefined();
  });
});
